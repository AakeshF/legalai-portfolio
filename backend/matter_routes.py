# matter_routes.py - API endpoints for matter management with MCP integration

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database import get_db
from models import Matter, MatterType, MatterStatus, User
from services.matter_service import MatterService, ConflictException
from services.mcp_manager import MCPManager
from auth_middleware import get_current_user, get_current_organization
from models import Organization
from schemas import (
    MatterCreateRequest,
    MatterUpdateRequest,
    MatterResponse,
    MatterListResponse,
    MCPContextResponse,
    ConflictCheckRequest,
    ConflictCheckResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/matters", tags=["matters"])
security = HTTPBearer()


@router.post("/create", response_model=MatterResponse)
async def create_matter(
    request: MatterCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Create a new matter with integrated conflict checking"""
    organization_id = current_org.id
    try:
        # Initialize services
        mcp_manager = MCPManager()
        matter_service = MatterService(db, mcp_manager)

        # Prepare matter data
        matter_data = {
            "client_id": request.client_id,
            "matter_name": request.matter_name,
            "matter_type": request.matter_type,
            "status": request.status or "active",
            "opposing_parties": request.opposing_parties or [],
            "jurisdiction": request.jurisdiction,
            "case_number": request.case_number,
            "judge_assigned": request.judge_assigned,
            "description": request.description,
            "billing_type": request.billing_type or "hourly",
            "estimated_value": request.estimated_value,
            "client_name": request.client_name,  # For conflict checking
        }

        # Create matter with conflict check
        matter = await matter_service.create_matter_with_conflict_check(
            matter_data, organization_id
        )

        # Schedule background MCP sync tasks
        background_tasks.add_task(matter_service._sync_matter_with_mcp_sources, matter)

        return MatterResponse.from_orm(matter)

    except ConflictException as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Conflict of interest detected",
                "conflicts": e.conflicts,
            },
        )
    except Exception as e:
        logger.error(f"Error creating matter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conflict-check", response_model=ConflictCheckResponse)
async def check_conflicts(
    request: ConflictCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Check for conflicts of interest before creating a matter"""
    organization_id = current_org.id
    try:
        mcp_manager = MCPManager()
        matter_service = MatterService(db, mcp_manager)

        result = await matter_service._check_conflicts_via_mcp(
            client_name=request.client_name,
            opposing_parties=request.opposing_parties,
            organization_id=organization_id,
        )

        return ConflictCheckResponse(**result)

    except Exception as e:
        logger.error(f"Error checking conflicts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{matter_id}", response_model=MatterResponse)
async def get_matter(
    matter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get a specific matter by ID"""
    organization_id = current_org.id
    matter = (
        db.query(Matter)
        .filter(Matter.id == matter_id, Matter.organization_id == organization_id)
        .first()
    )

    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    return MatterResponse.from_orm(matter)


@router.get("/", response_model=MatterListResponse)
async def list_matters(
    status: Optional[MatterStatus] = Query(None),
    matter_type: Optional[MatterType] = Query(None),
    client_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """List matters with filtering and pagination"""
    query = db.query(Matter).filter(Matter.organization_id == organization_id)

    # Apply filters
    if status:
        query = query.filter(Matter.status == status)
    if matter_type:
        query = query.filter(Matter.matter_type == matter_type)
    if client_id:
        query = query.filter(Matter.client_id == client_id)
    if search:
        query = query.filter(
            Matter.matter_name.ilike(f"%{search}%")
            | Matter.case_number.ilike(f"%{search}%")
        )

    # Get total count
    total = query.count()

    # Apply pagination
    matters = query.offset(skip).limit(limit).all()

    return MatterListResponse(
        matters=[MatterResponse.from_orm(m) for m in matters],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.put("/{matter_id}", response_model=MatterResponse)
async def update_matter(
    matter_id: str,
    request: MatterUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Update a matter"""
    matter = (
        db.query(Matter)
        .filter(Matter.id == matter_id, Matter.organization_id == organization_id)
        .first()
    )

    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(matter, field, value)

    # Handle status changes
    if request.status == MatterStatus.CLOSED and matter.date_closed is None:
        matter.date_closed = datetime.utcnow()
    elif request.status != MatterStatus.CLOSED:
        matter.date_closed = None

    db.commit()
    db.refresh(matter)

    return MatterResponse.from_orm(matter)


@router.get("/{matter_id}/mcp-context", response_model=MCPContextResponse)
async def get_matter_mcp_context(
    matter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get all MCP-enriched data for a matter"""
    try:
        # Verify matter belongs to organization
        matter = (
            db.query(Matter)
            .filter(Matter.id == matter_id, Matter.organization_id == organization_id)
            .first()
        )

        if not matter:
            raise HTTPException(status_code=404, detail="Matter not found")

        mcp_manager = MCPManager()
        matter_service = MatterService(db, mcp_manager)

        context = await matter_service.get_matter_mcp_context(matter_id)

        return MCPContextResponse(**context)

    except Exception as e:
        logger.error(f"Error getting MCP context: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{matter_id}/sync-court-data")
async def sync_court_data(
    matter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Manually sync matter with court MCP data"""
    try:
        # Verify matter belongs to organization
        matter = (
            db.query(Matter)
            .filter(Matter.id == matter_id, Matter.organization_id == organization_id)
            .first()
        )

        if not matter:
            raise HTTPException(status_code=404, detail="Matter not found")

        mcp_manager = MCPManager()
        matter_service = MatterService(db, mcp_manager)

        result = await matter_service.sync_court_data_for_matter(matter_id)

        return result

    except Exception as e:
        logger.error(f"Error syncing court data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{matter_id}/deadlines")
async def get_matter_deadlines(
    matter_id: str,
    include_completed: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get deadlines for a matter"""
    # Verify matter belongs to organization
    matter = (
        db.query(Matter)
        .filter(Matter.id == matter_id, Matter.organization_id == organization_id)
        .first()
    )

    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    query = db.query(Deadline).filter(Deadline.matter_id == matter_id)

    if not include_completed:
        query = query.filter(Deadline.completed_at.is_(None))

    deadlines = query.order_by(Deadline.due_date).all()

    return [
        {
            "id": d.id,
            "title": d.title,
            "description": d.description,
            "due_date": d.due_date.isoformat(),
            "is_court_deadline": d.is_court_deadline,
            "completed_at": d.completed_at.isoformat() if d.completed_at else None,
            "mcp_sync_source": d.mcp_sync_source,
        }
        for d in deadlines
    ]


@router.get("/{matter_id}/communications")
async def get_matter_communications(
    matter_id: str,
    communication_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Get communications for a matter"""
    # Verify matter belongs to organization
    matter = (
        db.query(Matter)
        .filter(Matter.id == matter_id, Matter.organization_id == organization_id)
        .first()
    )

    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    query = db.query(Communication).filter(Communication.matter_id == matter_id)

    if communication_type:
        query = query.filter(Communication.communication_type == communication_type)

    total = query.count()
    communications = (
        query.order_by(Communication.timestamp.desc()).offset(skip).limit(limit).all()
    )

    return {
        "communications": [
            {
                "id": c.id,
                "type": c.communication_type,
                "direction": c.direction,
                "subject": c.subject,
                "participants": c.participants,
                "timestamp": c.timestamp.isoformat(),
                "mcp_source": c.mcp_source,
            }
            for c in communications
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.delete("/{matter_id}")
async def delete_matter(
    matter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """Delete a matter (soft delete by setting status to archived)"""
    matter = (
        db.query(Matter)
        .filter(Matter.id == matter_id, Matter.organization_id == organization_id)
        .first()
    )

    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    # Soft delete by archiving
    matter.status = MatterStatus.ARCHIVED
    matter.date_closed = datetime.utcnow()

    db.commit()

    return {"message": "Matter archived successfully", "matter_id": matter_id}
