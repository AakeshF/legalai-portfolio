from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from database import get_db
from models import User, PromptLog, PromptStatus, PromptReviewQueue
from auth import get_current_user, require_admin
from services.prompt_processor import PromptProcessor
from services.admin_review_service import AdminReviewService

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


# Pydantic models
class PromptSubmitRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    prompt: str = Field(..., min_length=1)
    model_requested: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PromptSubmitResponse(BaseModel):
    prompt_id: int
    status: str
    requires_review: bool
    review_reason: Optional[str] = None
    estimated_wait_time: Optional[int] = None
    processed_prompt: Optional[str] = None
    requires_consent: bool = False
    consent_details: Optional[Dict[str, Any]] = None


class PromptStatusResponse(BaseModel):
    prompt_id: int
    status: str
    created_at: str
    requires_review: bool
    processed_prompt: Optional[str] = None
    rejection_reason: Optional[str] = None
    queue_position: Optional[int] = None


class PromptHistoryItem(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}
    
    id: int
    original_prompt: str
    status: str
    model_requested: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    response_output: Optional[str]


# User endpoints
@router.post("/submit", response_model=PromptSubmitResponse)
async def submit_prompt(
    request: PromptSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a prompt for processing"""
    processor = PromptProcessor()
    
    try:
        result = await processor.process_prompt(
            prompt=request.prompt,
            db=db,
            user_id=current_user.id,
            org_id=current_user.organization_id,
            model_requested=request.model_requested,
            context=request.context
        )
        
        return PromptSubmitResponse(
            prompt_id=result["prompt_id"],
            status=result["status"],
            requires_review=result.get("requires_review", False),
            review_reason=result.get("review_reason"),
            estimated_wait_time=result.get("estimated_wait_time"),
            processed_prompt=result.get("processed_prompt"),
            requires_consent=result.get("requires_consent", False),
            consent_details=result.get("consent_details")
        )
    except Exception as e:
        logger.error(f"Error submitting prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status/{prompt_id}", response_model=PromptStatusResponse)
async def get_prompt_status(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the status of a submitted prompt"""
    processor = PromptProcessor()
    
    result = await processor.get_prompt_status(
        prompt_id=prompt_id,
        db=db,
        user_id=current_user.id
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return PromptStatusResponse(**result)


@router.get("/history", response_model=List[PromptHistoryItem])
async def get_prompt_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: Optional[PromptStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's prompt history"""
    query = db.query(PromptLog).filter(
        PromptLog.user_id == current_user.id
    )
    
    # Apply filters
    if status_filter:
        query = query.filter(PromptLog.status == status_filter)
    if date_from:
        query = query.filter(PromptLog.created_at >= date_from)
    if date_to:
        query = query.filter(PromptLog.created_at <= date_to)
    
    # Order by newest first
    prompts = query.order_by(PromptLog.created_at.desc()).offset(offset).limit(limit).all()
    
    return prompts


# Admin endpoints
@router.get("/admin/pending")
async def get_pending_prompts(
    priority: Optional[str] = None,
    assigned_to_me: bool = False,
    unassigned: bool = False,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get prompts awaiting review (admin only)"""
    service = AdminReviewService()
    
    filters = {}
    if priority:
        filters["priority"] = priority
    if assigned_to_me:
        filters["assigned_to_me"] = True
    if unassigned:
        filters["unassigned"] = True
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    
    return await service.get_pending_prompts(
        db=db,
        org_id=current_user.organization_id,
        admin_id=current_user.id,
        filters=filters
    )


@router.post("/admin/{prompt_id}/assign")
async def assign_prompt_for_review(
    prompt_id: int,
    queue_id: int,
    assign_to_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Assign a prompt to an admin for review"""
    service = AdminReviewService()
    
    try:
        return await service.assign_prompt(
            db=db,
            queue_id=queue_id,
            admin_id=current_user.id,
            assign_to_id=assign_to_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/admin/{prompt_id}/approve")
async def approve_prompt(
    prompt_id: int,
    edited_prompt: Optional[str] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Approve a prompt with optional edits"""
    service = AdminReviewService()
    
    try:
        return await service.approve_prompt(
            db=db,
            prompt_id=prompt_id,
            admin_id=current_user.id,
            edited_prompt=edited_prompt,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/admin/{prompt_id}/reject")
async def reject_prompt(
    prompt_id: int,
    reason: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Reject a prompt with reason"""
    service = AdminReviewService()
    
    try:
        return await service.reject_prompt(
            db=db,
            prompt_id=prompt_id,
            admin_id=current_user.id,
            reason=reason,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


class FlagPromptRequest(BaseModel):
    flag_type: str = Field(..., pattern="^(security_concern|compliance_issue|needs_escalation|other)$")
    details: Optional[str] = None

@router.post("/admin/{prompt_id}/flag")
async def flag_prompt(
    prompt_id: int,
    request: FlagPromptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Flag a prompt for special attention"""
    service = AdminReviewService()
    
    try:
        return await service.flag_prompt(
            db=db,
            prompt_id=prompt_id,
            admin_id=current_user.id,
            flag_type=request.flag_type,
            details=request.details
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/admin/analytics")
async def get_review_analytics(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get analytics and statistics for prompt reviews"""
    service = AdminReviewService()
    
    return await service.get_analytics(
        db=db,
        org_id=current_user.organization_id,
        date_from=date_from,
        date_to=date_to
    )


# WebSocket endpoint for real-time updates
from fastapi import WebSocket, WebSocketDisconnect
import json

active_connections: Dict[str, List[WebSocket]] = {}


@router.websocket("/ws/{prompt_id}")
async def websocket_prompt_status(
    websocket: WebSocket,
    prompt_id: int,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time prompt status updates"""
    await websocket.accept()
    
    # Add to active connections
    if prompt_id not in active_connections:
        active_connections[prompt_id] = []
    active_connections[prompt_id].append(websocket)
    
    try:
        while True:
            # Wait for any message from client (keep-alive)
            await websocket.receive_text()
            
            # Send current status
            prompt = db.query(PromptLog).filter(
                PromptLog.id == prompt_id
            ).first()
            
            if prompt:
                await websocket.send_json({
                    "prompt_id": prompt_id,
                    "status": prompt.status.value,
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        # Remove from active connections
        active_connections[prompt_id].remove(websocket)
        if not active_connections[prompt_id]:
            del active_connections[prompt_id]


# Background task to notify WebSocket clients
async def notify_prompt_status_change(prompt_id: int, new_status: str):
    """Notify all connected clients about prompt status change"""
    if prompt_id in active_connections:
        for websocket in active_connections[prompt_id]:
            try:
                await websocket.send_json({
                    "prompt_id": prompt_id,
                    "status": new_status,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except:
                # Connection might be closed
                pass