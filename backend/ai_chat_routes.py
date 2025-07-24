# ai_chat_routes.py - Integrated AI chat with multi-provider support, consent, and audit
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
import json
import uuid

from database import get_db
from models import User, Organization, Document, ChatSession, ChatMessage
from auth_middleware import get_current_user, get_current_organization
from services.multi_provider_ai_service import MultiProviderAIService
from services.api_key_manager import APIKeyManager
from services.consent_manager import ConsentManager, ConsentType
from services.ai_audit_trail import AIAuditTrail
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])

class ChatRequestV2(BaseModel):
    message: str
    session_id: Optional[str] = None
    document_ids: Optional[List[int]] = None
    analysis_type: Optional[str] = "general"
    preferred_provider: Optional[str] = None
    require_consent: bool = True

class ChatResponseV2(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    answer: str
    sources: List[Dict[str, Any]]
    session_id: str
    message_id: int
    provider_used: str
    model_used: str
    consent_status: str
    audit_id: str
    structured_data: Optional[Dict[str, Any]] = None
    response_metrics: Optional[Dict[str, Any]] = None

@router.post("/v2", response_model=ChatResponseV2)
async def chat_v2(
    request: ChatRequestV2,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Enhanced chat endpoint with multi-provider AI, consent, and audit trail"""
    
    start_time = datetime.utcnow()
    audit_id = str(uuid.uuid4())
    
    try:
        # Initialize services
        ai_service = MultiProviderAIService()
        consent_manager = ConsentManager(db)
        audit_trail = AIAuditTrail(db)
        key_manager = APIKeyManager(db)
        
        # Import cost tracker
        from services.ai_cost_tracker import AICostTracker
        cost_tracker = AICostTracker(db)
        
        # Check consent if required
        consent_status = "not_required"
        consent_id = None
        
        if request.require_consent:
            consent_check = consent_manager.check_consent(
                organization_id=current_org.id,
                consent_type=ConsentType.CLOUD_AI,
                user_id=current_user.id,
                provider=request.preferred_provider
            )
            
            if not consent_check["granted"]:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "AI processing consent required",
                        "consent_required": True,
                        "consent_type": "cloud_ai",
                        "reason": consent_check.get("reason", "no_consent")
                    }
                )
            
            consent_status = "granted"
            consent_id = consent_check.get("consent_id")
        
        # Get or create chat session
        if request.session_id:
            session = db.query(ChatSession).filter_by(
                id=request.session_id,
                organization_id=current_org.id
            ).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session = ChatSession(
                user_id=current_user.id,
                organization_id=current_org.id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message
            )
            db.add(session)
            db.commit()
        
        # Load documents if specified
        documents = []
        if request.document_ids:
            documents = db.query(Document).filter(
                Document.id.in_(request.document_ids),
                Document.organization_id == current_org.id
            ).all()
            
            if len(documents) != len(request.document_ids):
                raise HTTPException(status_code=404, detail="One or more documents not found")
        
        # Get chat history
        chat_history = []
        recent_messages = db.query(ChatMessage).filter_by(
            session_id=session.id
        ).order_by(ChatMessage.timestamp.desc()).limit(10).all()
        
        for msg in reversed(recent_messages):
            chat_history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Get organization preferences
        org_preferences = consent_manager.get_organization_preferences(current_org.id)
        org_preferences["organization_id"] = current_org.id  # Add org ID for rate limiting
        
        # Get user preferences
        user_preferences = {
            "ai_provider_preference": current_user.ai_provider_preference,
            "ai_model_preferences": current_user.ai_model_preferences,
            "ai_consent_given": current_user.ai_consent_given
        }
        
        # Estimate tokens for budget check
        estimated_tokens = len(request.message) // 4  # Rough estimate
        if documents:
            for doc in documents:
                if hasattr(doc, 'extracted_content') and doc.extracted_content:
                    estimated_tokens += len(doc.extracted_content[:3000]) // 4
        
        # Check budget before processing
        provider_to_check = request.preferred_provider or current_user.ai_provider_preference or "openai"
        budget_check = await cost_tracker.check_budget_before_request(
            current_org.id,
            provider_to_check,
            estimated_tokens * 2  # Multiply by 2 to account for response
        )
        
        if not budget_check["allowed"]:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "Monthly AI budget exceeded",
                    "current_cost": budget_check["current_cost"],
                    "budget": budget_check["budget"],
                    "message": "Please increase your AI budget or wait until next month"
                }
            )
        
        # Process with multi-provider AI service
        try:
            # Set API keys from secure storage
            providers = ["claude", "openai", "gemini"]
            for provider in providers:
                api_key = key_manager.get_api_key(current_org.id, provider)
                if api_key:
                    # Temporarily set in environment for the service
                    import os
                    env_map = {
                        "claude": "ANTHROPIC_API_KEY",
                        "openai": "OPENAI_API_KEY",
                        "gemini": "GOOGLE_API_KEY"
                    }
                    os.environ[env_map[provider]] = api_key
            
            # Process message
            ai_response = await ai_service.process_chat_message(
                message=request.message,
                documents=documents,
                chat_history=chat_history,
                analysis_type=request.analysis_type,
                preferred_provider=request.preferred_provider,
                org_settings=org_preferences,
                user_preferences=user_preferences
            )
            
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            # Log failed attempt
            background_tasks.add_task(
                log_ai_request,
                audit_trail,
                audit_id,
                current_org.id,
                current_user.id,
                request,
                None,
                str(e),
                consent_id,
                consent_status
            )
            raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")
        
        # Save user message
        user_message = ChatMessage(
            session_id=session.id,
            role="user",
            content=request.message,
            metadata=json.dumps({
                "document_ids": request.document_ids,
                "analysis_type": request.analysis_type
            })
        )
        db.add(user_message)
        
        # Save AI response
        ai_message = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=ai_response["answer"],
            metadata=json.dumps({
                "provider_used": ai_response.get("provider_used"),
                "model": ai_response.get("model"),
                "sources": ai_response.get("sources", []),
                "structured_data": ai_response.get("structured_data"),
                "response_metrics": ai_response.get("response_metrics"),
                "audit_id": audit_id
            })
        )
        db.add(ai_message)
        
        # Update session
        session.last_activity = datetime.utcnow()
        session.message_count = (session.message_count or 0) + 2
        
        db.commit()
        
        # Log to audit trail in background
        background_tasks.add_task(
            log_ai_request,
            audit_trail,
            audit_id,
            current_org.id,
            current_user.id,
            request,
            ai_response,
            None,
            consent_id,
            consent_status
        )
        
        # Record cost in background
        if "response_metrics" in ai_response and "tokens_used" in ai_response["response_metrics"]:
            background_tasks.add_task(
                cost_tracker.record_usage_cost,
                current_org.id,
                ai_response.get("provider_used", "unknown"),
                ai_response["response_metrics"]["tokens_used"],
                audit_id
            )
        
        return ChatResponseV2(
            answer=ai_response["answer"],
            sources=ai_response.get("sources", []),
            session_id=str(session.id),
            message_id=ai_message.id,
            provider_used=ai_response.get("provider_used", "unknown"),
            model_used=ai_response.get("model", "unknown"),
            consent_status=consent_status,
            audit_id=audit_id,
            structured_data=ai_response.get("structured_data"),
            response_metrics=ai_response.get("response_metrics")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def log_ai_request(
    audit_trail: AIAuditTrail,
    audit_id: str,
    org_id: int,
    user_id: int,
    request: ChatRequestV2,
    response: Optional[Dict[str, Any]],
    error: Optional[str],
    consent_id: Optional[int],
    consent_status: str
):
    """Background task to log AI requests to audit trail"""
    try:
        # Prepare input data
        input_data = {
            "message": request.message,
            "analysis_type": request.analysis_type,
            "document_count": len(request.document_ids) if request.document_ids else 0
        }
        
        # Prepare output data
        if response:
            output_data = {
                "answer_length": len(response.get("answer", "")),
                "sources": response.get("sources", []),
                "structured_data": response.get("structured_data")
            }
        else:
            output_data = {"error": error}
        
        # Prepare metadata
        metadata = {
            "request_id": audit_id,
            "document_ids": request.document_ids,
            "preferred_provider": request.preferred_provider,
            "consent_id": consent_id,
            "consent_status": consent_status,
            "response_time_ms": response.get("response_metrics", {}).get("response_time_ms") if response else 0,
            "tokens_used": response.get("response_metrics", {}).get("tokens_used", 0) if response else 0,
            "provider_used": response.get("provider_used") if response else None,
            "fallback_used": response.get("response_metrics", {}).get("fallback_used") if response else False,
            "processing_location": "cloud" if response and response.get("provider_used") != "local" else "local"
        }
        
        # Extract decisions if available
        if response and "structured_data" in response:
            decisions = []
            data = response["structured_data"]
            
            if "action_items" in data:
                for item in data["action_items"]:
                    decisions.append({
                        "category": "action_item",
                        "item": "Action Required",
                        "value": item,
                        "confidence": 0.9
                    })
            
            if "key_findings" in data:
                for finding in data["key_findings"]:
                    decisions.append({
                        "category": "finding",
                        "item": "Key Finding",
                        "value": finding,
                        "confidence": 0.85
                    })
            
            metadata["decisions"] = decisions
        
        audit_trail.log_ai_request(
            organization_id=org_id,
            user_id=user_id,
            request_type="chat",
            provider=response.get("provider_used", "unknown") if response else "failed",
            model=response.get("model", "unknown") if response else "none",
            input_data=input_data,
            output_data=output_data,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Failed to log AI request to audit trail: {e}")

@router.get("/sessions")
async def get_chat_sessions(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Get user's chat sessions"""
    
    sessions = db.query(ChatSession).filter_by(
        user_id=current_user.id,
        organization_id=current_org.id
    ).order_by(ChatSession.last_activity.desc()).offset(offset).limit(limit).all()
    
    return {
        "sessions": [
            {
                "id": str(session.id),
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat() if session.last_activity else None,
                "message_count": session.message_count
            }
            for session in sessions
        ]
    }

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Get messages from a chat session"""
    
    # Verify session ownership
    session = db.query(ChatSession).filter_by(
        id=session_id,
        user_id=current_user.id,
        organization_id=current_org.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(ChatMessage).filter_by(
        session_id=session_id
    ).order_by(ChatMessage.timestamp.asc()).offset(offset).limit(limit).all()
    
    return {
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": json.loads(msg.metadata) if msg.metadata else {}
            }
            for msg in messages
        ]
    }