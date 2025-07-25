# communication_routes.py - API endpoints for client communication management

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging
import json

from database import get_db
from models import (
    ClientCommunication,
    CommunicationFollowUp,
    CommunicationTemplate,
    Matter,
    User,
    Organization,
)
from services.mcp_servers.client_communication_mcp import ClientCommunicationMCPServer
from auth_middleware import get_current_user, get_current_organization
from schemas import (
    CommunicationLogRequest,
    CommunicationLogResponse,
    CommunicationSearchRequest,
    CommunicationSearchResponse,
    PrivilegeLogRequest,
    PrivilegeLogResponse,
    FollowUpRequest,
    FollowUpResponse,
    BulkImportRequest,
    BulkImportResponse,
    CommunicationStatsResponse,
    CommunicationTemplateRequest,
    CommunicationTemplateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mcp/communications", tags=["communications"])
security = HTTPBearer()

# Initialize MCP server
communication_mcp = ClientCommunicationMCPServer()


@router.post("/log", response_model=CommunicationLogResponse)
async def log_communication(
    request: CommunicationLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Log a client communication"""
    organization_id = current_org.id
    try:
        # Verify matter belongs to organization
        matter = (
            db.query(Matter)
            .filter(
                Matter.id == request.matter_id,
                Matter.organization_id == organization_id,
            )
            .first()
        )

        if not matter:
            raise HTTPException(status_code=404, detail="Matter not found")

        # Use MCP server to log communication
        result = await communication_mcp.query(
            "log_communication",
            {
                "matter_id": request.matter_id,
                "client_id": request.client_id or matter.client_id,
                "type": request.communication_type,
                "direction": request.direction,
                "date": (
                    request.date.isoformat()
                    if request.date
                    else datetime.utcnow().isoformat()
                ),
                "participants": request.participants,
                "subject": request.subject,
                "content": request.content,
                "attachments": request.attachments or [],
                "tags": request.tags or [],
                "follow_up_required": request.follow_up_required,
                "metadata": request.metadata or {},
            },
        )

        if result["success"]:
            # Also save to database
            communication = ClientCommunication(
                organization_id=organization_id,
                matter_id=request.matter_id,
                client_id=request.client_id or matter.client_id,
                communication_type=request.communication_type,
                direction=request.direction,
                date=request.date or datetime.utcnow(),
                subject=request.subject,
                content=request.content,
                participants=request.participants,
                attachments=request.attachments or [],
                tags=request.tags or [],
                metadata=request.metadata or {},
                follow_up_required=request.follow_up_required,
                created_by_id=current_user.id,
                is_privileged=result.get("privileged", False),
                privilege_type=request.privilege_type or "not_privileged",
            )

            db.add(communication)
            db.commit()

            return CommunicationLogResponse(
                communication_id=communication.id,
                success=True,
                privileged=communication.is_privileged,
                follow_ups_created=result.get("follow_ups_created", 0),
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))

    except Exception as e:
        logger.error(f"Error logging communication: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=CommunicationSearchResponse)
async def search_communications(
    request: CommunicationSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Search communications with filters"""
    organization_id = current_org.id
    try:
        # Build database query
        query = db.query(ClientCommunication).filter(
            ClientCommunication.organization_id == organization_id
        )

        # Apply filters
        if request.matter_id:
            query = query.filter(ClientCommunication.matter_id == request.matter_id)

        if request.client_id:
            query = query.filter(ClientCommunication.client_id == request.client_id)

        if request.communication_type:
            query = query.filter(
                ClientCommunication.communication_type == request.communication_type
            )

        if request.date_from:
            query = query.filter(ClientCommunication.date >= request.date_from)

        if request.date_to:
            query = query.filter(ClientCommunication.date <= request.date_to)

        if request.privileged_only:
            query = query.filter(ClientCommunication.is_privileged == True)

        # Text search
        if request.search_query:
            search_term = f"%{request.search_query}%"
            query = query.filter(
                or_(
                    ClientCommunication.subject.ilike(search_term),
                    ClientCommunication.content.ilike(search_term),
                    ClientCommunication.tags.cast(String).ilike(search_term),
                )
            )

        # Pagination
        total = query.count()
        communications = query.offset(request.offset).limit(request.limit).all()

        # Format results
        results = []
        for comm in communications:
            result = {
                "id": comm.id,
                "matter_id": comm.matter_id,
                "client_id": comm.client_id,
                "type": comm.communication_type,
                "direction": comm.direction,
                "date": comm.date.isoformat(),
                "subject": comm.subject,
                "participants": comm.participants,
                "is_privileged": comm.is_privileged,
                "tags": comm.tags,
                "follow_up_required": comm.follow_up_required,
            }

            # Only include content if not privileged or user has access
            if not comm.is_privileged or current_user.role in ["attorney", "admin"]:
                result["content"] = comm.content
            else:
                result["content"] = "[PRIVILEGED]"

            results.append(result)

        return CommunicationSearchResponse(
            results=results, total=total, offset=request.offset, limit=request.limit
        )

    except Exception as e:
        logger.error(f"Error searching communications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/privilege-log", response_model=PrivilegeLogResponse)
async def generate_privilege_log(
    request: PrivilegeLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Generate privilege log for court requirements"""
    organization_id = current_org.id
    try:
        # Verify matter access
        matter = (
            db.query(Matter)
            .filter(
                Matter.id == request.matter_id,
                Matter.organization_id == organization_id,
            )
            .first()
        )

        if not matter:
            raise HTTPException(status_code=404, detail="Matter not found")

        # Generate via MCP
        result = await communication_mcp.query(
            "generate_privilege_log",
            {
                "matter_id": request.matter_id,
                "date_range": (
                    {
                        "start": request.start_date.isoformat(),
                        "end": request.end_date.isoformat(),
                    }
                    if request.start_date and request.end_date
                    else None
                ),
            },
        )

        if result["success"]:
            privilege_log = result["privilege_log"]

            return PrivilegeLogResponse(
                matter_id=privilege_log["matter_id"],
                generated_date=privilege_log["generated_date"],
                date_range={
                    "start": privilege_log["date_range"]["start"],
                    "end": privilege_log["date_range"]["end"],
                },
                total_entries=privilege_log["total_entries"],
                privileged_count=privilege_log["privileged_count"],
                entries=privilege_log["entries"],
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))

    except Exception as e:
        logger.error(f"Error generating privilege log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow-up", response_model=FollowUpResponse)
async def create_follow_up(
    request: FollowUpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Create a follow-up for a communication"""
    organization_id = current_org.id
    try:
        # Verify communication exists and belongs to organization
        communication = (
            db.query(ClientCommunication)
            .filter(
                ClientCommunication.id == request.communication_id,
                ClientCommunication.organization_id == organization_id,
            )
            .first()
        )

        if not communication:
            raise HTTPException(status_code=404, detail="Communication not found")

        # Create follow-up via MCP
        result = await communication_mcp.query(
            "set_follow_up",
            {
                "communication_id": request.communication_id,
                "due_date": request.due_date.isoformat(),
                "description": request.description,
                "priority": request.priority,
                "assigned_to": request.assigned_to_id,
                "auto_escalate": request.auto_escalate,
            },
        )

        if result["success"]:
            # Also save to database
            follow_up = CommunicationFollowUp(
                organization_id=organization_id,
                communication_id=request.communication_id,
                matter_id=communication.matter_id,
                due_date=request.due_date,
                description=request.description,
                priority=request.priority or "medium",
                assigned_to_id=request.assigned_to_id,
                auto_escalate=request.auto_escalate,
            )

            db.add(follow_up)
            db.commit()

            return FollowUpResponse(
                follow_up_id=follow_up.id,
                success=True,
                due_date=follow_up.due_date.isoformat(),
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))

    except Exception as e:
        logger.error(f"Error creating follow-up: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-import", response_model=BulkImportResponse)
async def bulk_import_communications(
    request: BulkImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Bulk import communications from external sources"""
    organization_id = current_org.id
    try:
        # Validate import source
        if request.source not in ["email", "phone", "calendar"]:
            raise HTTPException(status_code=400, detail="Invalid import source")

        # Queue background import task
        background_tasks.add_task(
            _process_bulk_import, request.dict(), organization_id, current_user.id
        )

        return BulkImportResponse(
            success=True,
            message=f"Bulk import from {request.source} queued",
            job_id=f"import_{datetime.utcnow().timestamp()}",
        )

    except Exception as e:
        logger.error(f"Error initiating bulk import: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=CommunicationStatsResponse)
async def get_communication_stats(
    matter_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get communication statistics"""
    try:
        # Use MCP to get stats
        result = await communication_mcp.query(
            "get_communication_stats",
            {
                "matter_id": matter_id,
                "date_range": (
                    {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None,
                    }
                    if start_date or end_date
                    else None
                ),
            },
        )

        if result["success"]:
            return CommunicationStatsResponse(**result["stats"])
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))

    except Exception as e:
        logger.error(f"Error getting communication stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/follow-ups")
async def get_follow_ups(
    matter_id: Optional[str] = Query(None),
    assigned_to_me: bool = Query(False),
    include_completed: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get follow-ups"""
    organization_id = current_org.id
    try:
        query = db.query(CommunicationFollowUp).filter(
            CommunicationFollowUp.organization_id == organization_id
        )

        if matter_id:
            query = query.filter(CommunicationFollowUp.matter_id == matter_id)

        if assigned_to_me:
            query = query.filter(
                CommunicationFollowUp.assigned_to_id == current_user.id
            )

        if not include_completed:
            query = query.filter(CommunicationFollowUp.completed == False)

        follow_ups = query.order_by(CommunicationFollowUp.due_date).all()

        return [
            {
                "id": f.id,
                "communication_id": f.communication_id,
                "matter_id": f.matter_id,
                "due_date": f.due_date.isoformat(),
                "description": f.description,
                "priority": f.priority,
                "assigned_to_id": f.assigned_to_id,
                "completed": f.completed,
                "completed_date": (
                    f.completed_date.isoformat() if f.completed_date else None
                ),
            }
            for f in follow_ups
        ]

    except Exception as e:
        logger.error(f"Error getting follow-ups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/follow-ups/{follow_up_id}/complete")
async def mark_follow_up_complete(
    follow_up_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Mark a follow-up as complete"""
    organization_id = current_org.id
    try:
        follow_up = (
            db.query(CommunicationFollowUp)
            .filter(
                CommunicationFollowUp.id == follow_up_id,
                CommunicationFollowUp.organization_id == organization_id,
            )
            .first()
        )

        if not follow_up:
            raise HTTPException(status_code=404, detail="Follow-up not found")

        follow_up.completed = True
        follow_up.completed_date = datetime.utcnow()
        follow_up.completed_by_id = current_user.id

        db.commit()

        return {
            "success": True,
            "follow_up_id": follow_up_id,
            "completed_date": follow_up.completed_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error completing follow-up: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates", response_model=CommunicationTemplateResponse)
async def create_communication_template(
    request: CommunicationTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Create a communication template"""
    organization_id = current_org.id
    try:
        template = CommunicationTemplate(
            organization_id=organization_id,
            name=request.name,
            description=request.description,
            communication_type=request.communication_type,
            subject_template=request.subject_template,
            content_template=request.content_template,
            available_variables=request.available_variables or [],
            tags=request.tags or [],
        )

        db.add(template)
        db.commit()

        return CommunicationTemplateResponse(
            id=template.id,
            name=template.name,
            communication_type=template.communication_type,
            created_at=template.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_communication_templates(
    communication_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get communication templates"""
    organization_id = current_org.id
    try:
        query = db.query(CommunicationTemplate).filter(
            CommunicationTemplate.organization_id == organization_id,
            CommunicationTemplate.is_active == True,
        )

        if communication_type:
            query = query.filter(
                CommunicationTemplate.communication_type == communication_type
            )

        templates = query.all()

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "communication_type": t.communication_type,
                "available_variables": t.available_variables,
                "tags": t.tags,
                "usage_count": t.usage_count,
            }
            for t in templates
        ]

    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task for bulk import
async def _process_bulk_import(
    import_data: Dict[str, Any], organization_id: str, user_id: str
):
    """Process bulk import in background"""
    logger.info(f"Processing bulk import from {import_data['source']}")

    try:
        if import_data["source"] == "email":
            result = await communication_mcp.query(
                "sync_emails",
                {
                    "mailbox_config": import_data["config"],
                    "matter_id": import_data.get("matter_id"),
                },
            )

        logger.info(f"Bulk import completed: {result}")

    except Exception as e:
        logger.error(f"Bulk import failed: {str(e)}")


# Add string type import for query
from sqlalchemy import String
