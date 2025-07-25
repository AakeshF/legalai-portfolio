import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from models import (
    User,
    Organization,
    PromptLog,
    PromptStatus,
    PromptReviewQueue,
    PromptAdminAction,
)
from utils.notifications import NotificationService

logger = logging.getLogger(__name__)


class AdminReviewService:
    """
    Service for managing admin review workflow for prompts
    """

    def __init__(self):
        self.notification_service = NotificationService()

    async def get_pending_prompts(
        self,
        db: Session,
        org_id: str,
        admin_id: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get prompts awaiting review"""
        query = (
            db.query(PromptReviewQueue, PromptLog, User)
            .join(PromptLog, PromptReviewQueue.prompt_log_id == PromptLog.id)
            .join(User, PromptLog.user_id == User.id)
            .filter(PromptReviewQueue.organization_id == org_id)
        )

        # Apply filters
        if filters:
            if filters.get("priority"):
                query = query.filter(PromptReviewQueue.priority == filters["priority"])
            if filters.get("assigned_to_me"):
                query = query.filter(PromptReviewQueue.assigned_to == admin_id)
            elif filters.get("unassigned"):
                query = query.filter(PromptReviewQueue.assigned_to.is_(None))
            if filters.get("date_from"):
                query = query.filter(PromptReviewQueue.added_at >= filters["date_from"])
            if filters.get("date_to"):
                query = query.filter(PromptReviewQueue.added_at <= filters["date_to"])

        # Order by priority and date
        priority_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}

        results = query.all()

        # Format results
        pending_prompts = []
        for queue_entry, prompt_log, user in results:
            pending_prompts.append(
                {
                    "queue_id": queue_entry.id,
                    "prompt_id": prompt_log.id,
                    "user": {
                        "id": user.id,
                        "name": user.full_name,
                        "email": user.email,
                    },
                    "original_prompt": prompt_log.original_prompt,
                    "redacted_prompt": prompt_log.redacted_prompt,
                    "sensitive_patterns": prompt_log.sensitive_patterns_detected,
                    "priority": queue_entry.priority,
                    "reason": queue_entry.reason,
                    "added_at": queue_entry.added_at.isoformat(),
                    "assigned_to": queue_entry.assigned_to,
                    "assigned_at": (
                        queue_entry.assigned_at.isoformat()
                        if queue_entry.assigned_at
                        else None
                    ),
                    "due_by": (
                        queue_entry.due_by.isoformat() if queue_entry.due_by else None
                    ),
                }
            )

        # Sort by priority
        pending_prompts.sort(
            key=lambda x: (priority_order.get(x["priority"], 5), x["added_at"])
        )

        return pending_prompts

    async def assign_prompt(
        self,
        db: Session,
        queue_id: int,
        admin_id: str,
        assign_to_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Assign a prompt to an admin for review"""
        queue_entry = (
            db.query(PromptReviewQueue).filter(PromptReviewQueue.id == queue_id).first()
        )

        if not queue_entry:
            raise ValueError("Queue entry not found")

        # Assign to self if no assignee specified
        assignee_id = assign_to_id or admin_id

        # Verify assignee is an admin
        assignee = (
            db.query(User)
            .filter(
                User.id == assignee_id,
                User.organization_id == queue_entry.organization_id,
                User.role.in_(["admin", "manager", "reviewer"]),
            )
            .first()
        )

        if not assignee:
            raise ValueError("Invalid assignee")

        # Update assignment
        queue_entry.assigned_to = assignee_id
        queue_entry.assigned_at = datetime.utcnow()

        # Set due date if not set
        if not queue_entry.due_by:
            if queue_entry.priority == "critical":
                queue_entry.due_by = datetime.utcnow() + timedelta(hours=1)
            elif queue_entry.priority == "high":
                queue_entry.due_by = datetime.utcnow() + timedelta(hours=4)
            else:
                queue_entry.due_by = datetime.utcnow() + timedelta(days=1)

        db.commit()

        # Send notification
        await self.notification_service.send_assignment_notification(
            assignee, queue_entry
        )

        return {
            "status": "assigned",
            "assigned_to": assignee.full_name,
            "due_by": queue_entry.due_by.isoformat(),
        }

    async def approve_prompt(
        self,
        db: Session,
        prompt_id: int,
        admin_id: str,
        edited_prompt: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve a prompt with optional edits"""
        # Get prompt log
        prompt_log = db.query(PromptLog).filter(PromptLog.id == prompt_id).first()

        if not prompt_log:
            raise ValueError("Prompt not found")

        # Verify admin has permission
        admin = (
            db.query(User)
            .filter(
                User.id == admin_id,
                User.organization_id == prompt_log.organization_id,
                User.role.in_(["admin", "manager", "reviewer"]),
            )
            .first()
        )

        if not admin:
            raise ValueError("Unauthorized")

        # Update prompt log
        prompt_log.status = PromptStatus.APPROVED
        prompt_log.reviewed_by = admin_id
        prompt_log.reviewed_at = datetime.utcnow()
        prompt_log.review_notes = notes

        # If edited, store the edit
        if edited_prompt and edited_prompt != prompt_log.redacted_prompt:
            prompt_log.final_prompt = edited_prompt

            # Create admin action record
            admin_action = PromptAdminAction(
                prompt_log_id=prompt_id,
                admin_id=admin_id,
                action="edit",
                original_content=prompt_log.redacted_prompt,
                modified_content=edited_prompt,
                action_details={"reason": "Admin edited prompt during approval"},
                timestamp=datetime.utcnow(),
            )
            db.add(admin_action)
        else:
            prompt_log.final_prompt = prompt_log.redacted_prompt

        # Create approval action
        approval_action = PromptAdminAction(
            prompt_log_id=prompt_id,
            admin_id=admin_id,
            action="approve",
            action_details={"notes": notes, "edited": edited_prompt is not None},
            timestamp=datetime.utcnow(),
        )
        db.add(approval_action)

        # Remove from review queue
        db.query(PromptReviewQueue).filter(
            PromptReviewQueue.prompt_log_id == prompt_id
        ).delete()

        db.commit()

        # Notify user
        user = db.query(User).filter(User.id == prompt_log.user_id).first()
        await self.notification_service.send_approval_notification(user, prompt_log)

        return {
            "status": "approved",
            "final_prompt": prompt_log.final_prompt,
            "reviewed_by": admin.full_name,
            "reviewed_at": prompt_log.reviewed_at.isoformat(),
        }

    async def reject_prompt(
        self,
        db: Session,
        prompt_id: int,
        admin_id: str,
        reason: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reject a prompt with reason"""
        # Get prompt log
        prompt_log = db.query(PromptLog).filter(PromptLog.id == prompt_id).first()

        if not prompt_log:
            raise ValueError("Prompt not found")

        # Verify admin has permission
        admin = (
            db.query(User)
            .filter(
                User.id == admin_id,
                User.organization_id == prompt_log.organization_id,
                User.role.in_(["admin", "manager", "reviewer"]),
            )
            .first()
        )

        if not admin:
            raise ValueError("Unauthorized")

        # Update prompt log
        prompt_log.status = PromptStatus.REJECTED
        prompt_log.reviewed_by = admin_id
        prompt_log.reviewed_at = datetime.utcnow()
        prompt_log.rejection_reason = reason
        prompt_log.review_notes = notes

        # Create rejection action
        rejection_action = PromptAdminAction(
            prompt_log_id=prompt_id,
            admin_id=admin_id,
            action="reject",
            action_details={"reason": reason, "notes": notes},
            timestamp=datetime.utcnow(),
        )
        db.add(rejection_action)

        # Remove from review queue
        db.query(PromptReviewQueue).filter(
            PromptReviewQueue.prompt_log_id == prompt_id
        ).delete()

        db.commit()

        # Notify user
        user = db.query(User).filter(User.id == prompt_log.user_id).first()
        await self.notification_service.send_rejection_notification(
            user, prompt_log, reason
        )

        return {
            "status": "rejected",
            "reason": reason,
            "reviewed_by": admin.full_name,
            "reviewed_at": prompt_log.reviewed_at.isoformat(),
        }

    async def flag_prompt(
        self,
        db: Session,
        prompt_id: int,
        admin_id: str,
        flag_type: str,
        details: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Flag a prompt for special attention"""
        # Get prompt log
        prompt_log = db.query(PromptLog).filter(PromptLog.id == prompt_id).first()

        if not prompt_log:
            raise ValueError("Prompt not found")

        # Create flag action
        flag_action = PromptAdminAction(
            prompt_log_id=prompt_id,
            admin_id=admin_id,
            action="flag",
            action_details={"flag_type": flag_type, "details": details},
            timestamp=datetime.utcnow(),
        )
        db.add(flag_action)

        # Update queue priority if needed
        if flag_type == "security_concern":
            queue_entry = (
                db.query(PromptReviewQueue)
                .filter(PromptReviewQueue.prompt_log_id == prompt_id)
                .first()
            )
            if queue_entry:
                queue_entry.priority = "critical"

        db.commit()

        return {"status": "flagged", "flag_type": flag_type, "details": details}

    async def get_analytics(
        self,
        db: Session,
        org_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get review analytics and statistics"""
        # Default to last 30 days
        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=30)
        if not date_to:
            date_to = datetime.utcnow()

        # Total prompts
        total_prompts = (
            db.query(PromptLog)
            .filter(
                PromptLog.organization_id == org_id,
                PromptLog.created_at.between(date_from, date_to),
            )
            .count()
        )

        # Prompts by status
        status_counts = {}
        for status in PromptStatus:
            count = (
                db.query(PromptLog)
                .filter(
                    PromptLog.organization_id == org_id,
                    PromptLog.status == status,
                    PromptLog.created_at.between(date_from, date_to),
                )
                .count()
            )
            status_counts[status.value] = count

        # Average review time
        reviewed_prompts = (
            db.query(PromptLog)
            .filter(
                PromptLog.organization_id == org_id,
                PromptLog.reviewed_at.isnot(None),
                PromptLog.created_at.between(date_from, date_to),
            )
            .all()
        )

        if reviewed_prompts:
            total_review_time = sum(
                (p.reviewed_at - p.created_at).total_seconds() for p in reviewed_prompts
            )
            avg_review_time = total_review_time / len(reviewed_prompts) / 60  # minutes
        else:
            avg_review_time = 0

        # Queue statistics
        current_queue_size = (
            db.query(PromptReviewQueue)
            .filter(PromptReviewQueue.organization_id == org_id)
            .count()
        )

        queue_by_priority = {}
        for priority in ["critical", "high", "medium", "low"]:
            count = (
                db.query(PromptReviewQueue)
                .filter(
                    PromptReviewQueue.organization_id == org_id,
                    PromptReviewQueue.priority == priority,
                )
                .count()
            )
            queue_by_priority[priority] = count

        # Admin activity
        admin_actions = (
            db.query(
                PromptAdminAction.admin_id,
                User.first_name,
                User.last_name,
                PromptAdminAction.action,
            )
            .join(User, PromptAdminAction.admin_id == User.id)
            .join(PromptLog, PromptAdminAction.prompt_log_id == PromptLog.id)
            .filter(
                PromptLog.organization_id == org_id,
                PromptAdminAction.timestamp.between(date_from, date_to),
            )
            .all()
        )

        admin_stats = {}
        for admin_id, first_name, last_name, action in admin_actions:
            if admin_id not in admin_stats:
                admin_stats[admin_id] = {
                    "name": f"{first_name} {last_name}",
                    "actions": {"approve": 0, "reject": 0, "edit": 0, "flag": 0},
                }
            admin_stats[admin_id]["actions"][action] += 1

        return {
            "date_range": {"from": date_from.isoformat(), "to": date_to.isoformat()},
            "total_prompts": total_prompts,
            "status_breakdown": status_counts,
            "average_review_time_minutes": round(avg_review_time, 2),
            "current_queue": {
                "total": current_queue_size,
                "by_priority": queue_by_priority,
            },
            "admin_activity": list(admin_stats.values()),
            "auto_approval_rate": (
                status_counts.get("auto_approved", 0) / total_prompts * 100
                if total_prompts > 0
                else 0
            ),
        }

    async def escalate_overdue_prompts(self, db: Session):
        """Escalate prompts that are overdue for review"""
        overdue_prompts = (
            db.query(PromptReviewQueue)
            .filter(
                PromptReviewQueue.due_by < datetime.utcnow(),
                PromptReviewQueue.assigned_to.isnot(None),
            )
            .all()
        )

        for prompt in overdue_prompts:
            # Increase priority
            if prompt.priority == "low":
                prompt.priority = "medium"
            elif prompt.priority == "medium":
                prompt.priority = "high"
            elif prompt.priority == "high":
                prompt.priority = "critical"

            # Notify supervisor
            org = (
                db.query(Organization)
                .filter(Organization.id == prompt.organization_id)
                .first()
            )

            if org:
                supervisors = (
                    db.query(User)
                    .filter(User.organization_id == org.id, User.role == "admin")
                    .all()
                )

                for supervisor in supervisors:
                    await self.notification_service.send_escalation_notification(
                        supervisor, prompt
                    )

        db.commit()
