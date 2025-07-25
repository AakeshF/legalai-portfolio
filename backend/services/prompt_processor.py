import asyncio
from typing import Dict, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy.orm import Session
import json
import logging

from models import (
    User,
    Organization,
    PromptLog,
    PromptStatus,
    PromptReviewQueue,
    PromptAdminAction,
    ConsentRecord,
    ConsentType,
)

# from services.anonymization_service import AnonymizationService  # Temporarily disabled - requires spacy
# from services.sensitive_data_detector import SensitiveDataDetector  # Temporarily disabled - may require spacy
from config import settings

logger = logging.getLogger(__name__)


class PromptProcessor:
    """
    Middleware for processing all prompts through anonymization,
    logging, and consent management
    """

    def __init__(self):
        # self.anonymization_service = AnonymizationService()  # Temporarily disabled
        # self.sensitive_data_detector = SensitiveDataDetector()  # Temporarily disabled
        pass

    async def process_prompt(
        self,
        prompt: str,
        db: Session,
        user_id: str,
        org_id: str,
        model_requested: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process prompt through the complete pipeline
        Returns structured response with processing details
        """
        # Create prompt log entry
        prompt_log = PromptLog(
            organization_id=org_id,
            user_id=user_id,
            original_prompt=prompt,
            model_requested=model_requested,
            status=PromptStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db.add(prompt_log)
        db.commit()

        try:
            # Step 1: Detect sensitive data
            sensitivity_result = await self._detect_sensitive_data(
                prompt, db, user_id, org_id
            )

            # Step 2: Check consent requirements
            consent_required, consent_details = await self._check_consent_requirements(
                sensitivity_result, db, user_id, org_id
            )

            # Step 3: Anonymize if needed
            anonymization_result = self.anonymization_service.anonymize_text(
                prompt, db, user_id, org_id
            )

            # Update prompt log
            prompt_log.redacted_prompt = anonymization_result.redacted
            prompt_log.sensitive_patterns_detected = [
                {
                    "type": p.type,
                    "confidence": p.confidence,
                    "needs_consent": p.needs_consent,
                }
                for p in anonymization_result.sensitive_patterns
            ]
            prompt_log.confidence_scores = {
                p.type: p.confidence for p in anonymization_result.sensitive_patterns
            }

            # Step 4: Determine if review is required
            requires_review = await self._determine_review_requirement(
                sensitivity_result, anonymization_result, db, org_id
            )

            prompt_log.requires_review = requires_review

            # Step 5: Handle based on review requirement
            if requires_review:
                # Add to review queue
                review_queue_entry = PromptReviewQueue(
                    prompt_log_id=prompt_log.id,
                    organization_id=org_id,
                    priority=self._calculate_priority(sensitivity_result),
                    reason=self._generate_review_reason(
                        sensitivity_result, anonymization_result
                    ),
                    added_at=datetime.utcnow(),
                )
                db.add(review_queue_entry)
                prompt_log.status = PromptStatus.PENDING

                result = {
                    "status": "pending_review",
                    "prompt_id": prompt_log.id,
                    "requires_review": True,
                    "review_reason": review_queue_entry.reason,
                    "estimated_wait_time": await self._estimate_wait_time(db, org_id),
                }
            else:
                # Auto-approve if no review needed
                prompt_log.status = PromptStatus.AUTO_APPROVED
                prompt_log.auto_approved = True
                prompt_log.final_prompt = anonymization_result.redacted

                result = {
                    "status": "approved",
                    "prompt_id": prompt_log.id,
                    "processed_prompt": anonymization_result.redacted,
                    "requires_consent": consent_required,
                    "consent_details": consent_details,
                    "anonymization_applied": len(
                        anonymization_result.sensitive_patterns
                    )
                    > 0,
                    "sensitive_patterns": len(anonymization_result.sensitive_patterns),
                }

            db.commit()
            return result

        except Exception as e:
            logger.error(f"Error processing prompt: {e}")
            prompt_log.status = PromptStatus.FAILED
            prompt_log.error_message = str(e)
            db.commit()
            raise

    async def _detect_sensitive_data(
        self, prompt: str, db: Session, user_id: str, org_id: str
    ) -> Dict[str, Any]:
        """Detect sensitive data in prompt"""
        return await self.sensitive_data_detector.analyze(prompt, db, user_id, org_id)

    async def _check_consent_requirements(
        self, sensitivity_result: Dict[str, Any], db: Session, user_id: str, org_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if consent is required based on sensitivity"""
        # Check for highly sensitive data types
        sensitive_types = {
            "ssn",
            "credit_card",
            "bank_account",
            "medical_record",
            "privileged_communication",
        }

        detected_sensitive = [
            item
            for item in sensitivity_result.get("detected_items", [])
            if item["type"] in sensitive_types
        ]

        if not detected_sensitive:
            return False, None

        # Check existing consent
        consent = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.user_id == user_id,
                ConsentRecord.organization_id == org_id,
                ConsentRecord.consent_type == ConsentType.CLOUD_AI,
                ConsentRecord.granted == True,
                ConsentRecord.revoked_at.is_(None),
            )
            .first()
        )

        if consent and (
            not consent.expires_at or consent.expires_at > datetime.utcnow()
        ):
            return False, None

        # Consent required
        return True, {
            "sensitive_data_types": list(
                set(item["type"] for item in detected_sensitive)
            ),
            "consent_type": "cloud_ai_processing",
            "message": "This prompt contains sensitive data that requires your consent for AI processing.",
        }

    async def _determine_review_requirement(
        self,
        sensitivity_result: Dict[str, Any],
        anonymization_result: Any,
        db: Session,
        org_id: str,
    ) -> bool:
        """Determine if manual review is required"""
        # Get organization settings
        org = db.query(Organization).filter(Organization.id == org_id).first()

        # Check review triggers
        triggers = []

        # High sensitivity score
        if sensitivity_result.get("overall_sensitivity", 0) > 0.8:
            triggers.append("high_sensitivity")

        # Low confidence anonymization
        if anonymization_result.confidence_score < 0.6:
            triggers.append("low_confidence_anonymization")

        # Specific sensitive types always require review
        always_review_types = {"ssn", "credit_card", "privileged_communication"}
        detected_types = {p.type for p in anonymization_result.sensitive_patterns}
        if detected_types & always_review_types:
            triggers.append("sensitive_type_detected")

        # Organization policy
        if hasattr(org, "require_prompt_review") and org.require_prompt_review:
            triggers.append("org_policy")

        return len(triggers) > 0

    def _calculate_priority(self, sensitivity_result: Dict[str, Any]) -> str:
        """Calculate review priority based on sensitivity"""
        score = sensitivity_result.get("overall_sensitivity", 0)

        if score > 0.9:
            return "critical"
        elif score > 0.7:
            return "high"
        elif score > 0.4:
            return "medium"
        else:
            return "low"

    def _generate_review_reason(
        self, sensitivity_result: Dict[str, Any], anonymization_result: Any
    ) -> str:
        """Generate human-readable review reason"""
        reasons = []

        if sensitivity_result.get("overall_sensitivity", 0) > 0.8:
            reasons.append("High sensitivity score")

        sensitive_types = {p.type for p in anonymization_result.sensitive_patterns}
        if sensitive_types:
            reasons.append(f"Contains: {', '.join(sensitive_types)}")

        if anonymization_result.confidence_score < 0.6:
            reasons.append("Low confidence in anonymization")

        return "; ".join(reasons) if reasons else "Manual review required"

    async def _estimate_wait_time(self, db: Session, org_id: str) -> int:
        """Estimate wait time in minutes for review"""
        # Count pending reviews
        pending_count = (
            db.query(PromptReviewQueue)
            .filter(
                PromptReviewQueue.organization_id == org_id,
                PromptReviewQueue.assigned_to.is_(None),
            )
            .count()
        )

        # Estimate based on average review time (5 minutes per prompt)
        return pending_count * 5

    async def get_prompt_status(
        self, prompt_id: int, db: Session, user_id: str
    ) -> Dict[str, Any]:
        """Get current status of a prompt"""
        prompt_log = (
            db.query(PromptLog)
            .filter(PromptLog.id == prompt_id, PromptLog.user_id == user_id)
            .first()
        )

        if not prompt_log:
            return {"error": "Prompt not found"}

        result = {
            "prompt_id": prompt_id,
            "status": prompt_log.status.value,
            "created_at": prompt_log.created_at.isoformat(),
            "requires_review": prompt_log.requires_review,
        }

        if prompt_log.status == PromptStatus.APPROVED:
            result["processed_prompt"] = prompt_log.final_prompt
        elif prompt_log.status == PromptStatus.REJECTED:
            result["rejection_reason"] = prompt_log.rejection_reason
        elif prompt_log.status == PromptStatus.PENDING:
            queue_entry = (
                db.query(PromptReviewQueue)
                .filter(PromptReviewQueue.prompt_log_id == prompt_id)
                .first()
            )
            if queue_entry:
                result["queue_position"] = self._get_queue_position(
                    db, queue_entry.id, queue_entry.organization_id
                )

        return result

    def _get_queue_position(self, db: Session, queue_id: int, org_id: str) -> int:
        """Get position in review queue"""
        earlier_entries = (
            db.query(PromptReviewQueue)
            .filter(
                PromptReviewQueue.organization_id == org_id,
                PromptReviewQueue.id < queue_id,
                PromptReviewQueue.assigned_to.is_(None),
            )
            .count()
        )

        return earlier_entries + 1
