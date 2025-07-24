from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from database import get_db
from models import User, ChatSession
from auth import get_current_user
from services.integrated_ai_assistant import integrated_ai_assistant

router = APIRouter(prefix="/api/ai/integrated", tags=["integrated-ai"])


# Pydantic models
class IntegratedAIRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    preferred_model: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class IntegratedAIResponse(BaseModel):
    status: str
    response: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    required_consents: Optional[List[str]] = None
    prompt_id: Optional[int] = None
    estimated_wait_time: Optional[int] = None


class SystemHealthResponse(BaseModel):
    overall: str
    components: Dict[str, Dict[str, Any]]
    timestamp: str


class UsageStatisticsResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    period: Dict[str, str]
    summary: Dict[str, Any]
    model_usage: List[Dict[str, Any]]
    total_estimated_cost: float


# Main AI endpoint
@router.post("/process", response_model=IntegratedAIResponse)
async def process_ai_request(
    request: IntegratedAIRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process an AI request through the complete security pipeline
    """
    # Validate session if provided
    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.organization_id == current_user.organization_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
    
    # Process request
    result = await integrated_ai_assistant.process_request(
        prompt=request.prompt,
        db=db,
        user_id=current_user.id,
        org_id=current_user.organization_id,
        session_id=request.session_id,
        document_ids=request.document_ids,
        preferred_model=request.preferred_model,
        context=request.context
    )
    
    # Handle different statuses
    if result["status"] == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": result["message"],
                "reasons": result.get("reasons", []),
                "classification": result.get("classification")
            }
        )
    
    return IntegratedAIResponse(**result)


# Health check endpoint
@router.get("/health", response_model=SystemHealthResponse)
async def check_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check health of all integrated AI components"""
    health = await integrated_ai_assistant.check_system_health(db)
    return health


# Usage statistics endpoint
@router.get("/usage", response_model=UsageStatisticsResponse)
async def get_usage_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI usage statistics for the organization"""
    stats = await integrated_ai_assistant.get_usage_statistics(
        db=db,
        org_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date
    )
    return stats


# Batch processing endpoint
@router.post("/batch")
async def process_batch_requests(
    requests: List[IntegratedAIRequest],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process multiple AI requests in batch"""
    if len(requests) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 requests allowed in batch"
        )
    
    results = []
    for req in requests:
        try:
            result = await integrated_ai_assistant.process_request(
                prompt=req.prompt,
                db=db,
                user_id=current_user.id,
                org_id=current_user.organization_id,
                session_id=req.session_id,
                document_ids=req.document_ids,
                preferred_model=req.preferred_model,
                context=req.context
            )
            results.append(result)
        except Exception as e:
            results.append({
                "status": "error",
                "message": str(e),
                "prompt": req.prompt[:50] + "..."
            })
    
    return {
        "total": len(requests),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "results": results
    }


# Session management
@router.post("/session/create")
async def create_chat_session(
    session_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat session"""
    import uuid
    
    session = ChatSession(
        id=str(uuid.uuid4()),
        session_name=session_name or f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        created_at=datetime.utcnow(),
        last_activity=datetime.utcnow()
    )
    
    db.add(session)
    db.commit()
    
    return {
        "session_id": session.id,
        "session_name": session.session_name,
        "created_at": session.created_at.isoformat()
    }


@router.get("/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat history for a session"""
    # Verify session ownership
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.organization_id == current_user.organization_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    from models import ChatMessage
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
    
    return {
        "session_id": session_id,
        "session_name": session.session_name,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "model_used": msg.model_used,
                "processing_time": msg.processing_time
            }
            for msg in reversed(messages)  # Return in chronological order
        ]
    }


# Model preferences
@router.put("/preferences/model")
async def update_model_preferences(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's AI model preferences"""
    if provider:
        current_user.ai_provider_preference = provider
    
    if model and provider:
        if not current_user.ai_model_preferences:
            current_user.ai_model_preferences = {}
        current_user.ai_model_preferences[provider] = model
    
    db.commit()
    
    return {
        "status": "success",
        "provider_preference": current_user.ai_provider_preference,
        "model_preferences": current_user.ai_model_preferences
    }


@router.get("/preferences/model")
async def get_model_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's AI model preferences"""
    return {
        "provider_preference": current_user.ai_provider_preference,
        "model_preferences": current_user.ai_model_preferences or {},
        "available_providers": ["openai", "claude", "gemini"]
    }