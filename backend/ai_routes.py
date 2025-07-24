# ai_routes.py - AI backend management endpoints
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel

from database import get_db
from models import User, Organization
from auth_middleware import get_current_user, get_current_organization
from services.hybrid_ai_service import hybrid_ai_service, AIBackend
from audit_logger import AuditLogger, AuditEvent, AuditEventType
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Request/Response schemas
class AIBackendConfig(BaseModel):
    ai_backend: str  # cloud, local, auto
    local_llm_endpoint: Optional[str] = None
    local_llm_model: Optional[str] = None
    ai_fallback_enabled: bool = True

class AIBackendTestRequest(BaseModel):
    message: str = "Hello, can you help me with legal analysis?"
    backend: str  # cloud or local

@router.get("/backends/status")
async def get_ai_backends_status(
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Get status of available AI backends"""
    status = await hybrid_ai_service.get_backend_status()
    
    # Add organization's current configuration
    status["organization_config"] = {
        "current_backend": current_org.ai_backend,
        "local_endpoint": current_org.local_llm_endpoint,
        "local_model": current_org.local_llm_model,
        "fallback_enabled": current_org.ai_fallback_enabled
    }
    
    return status

@router.get("/backends/config")
async def get_ai_backend_config(
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Get current AI backend configuration for organization"""
    return {
        "ai_backend": current_org.ai_backend,
        "local_llm_endpoint": current_org.local_llm_endpoint,
        "local_llm_model": current_org.local_llm_model,
        "ai_fallback_enabled": current_org.ai_fallback_enabled
    }

@router.put("/backends/config")
async def update_ai_backend_config(
    config: AIBackendConfig,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """Update AI backend configuration (admin only)"""
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change AI backend settings"
        )
    
    # Validate backend choice
    if config.ai_backend not in ["cloud", "local", "auto"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backend. Must be 'cloud', 'local', or 'auto'"
        )
    
    # If local backend, validate endpoint
    if config.ai_backend in ["local", "auto"] and not config.local_llm_endpoint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local LLM endpoint required for local or auto mode"
        )
    
    # Update organization settings
    current_org.ai_backend = config.ai_backend
    current_org.local_llm_endpoint = config.local_llm_endpoint
    current_org.local_llm_model = config.local_llm_model or "llama2"
    current_org.ai_fallback_enabled = config.ai_fallback_enabled
    
    db.commit()
    
    # Log configuration change
    logger.info(f"AI backend configuration updated", extra={
        "organization_id": current_org.id,
        "user_id": current_user.id,
        "new_backend": config.ai_backend
    })
    
    return {
        "message": "AI backend configuration updated successfully",
        "config": {
            "ai_backend": current_org.ai_backend,
            "local_llm_endpoint": current_org.local_llm_endpoint,
            "local_llm_model": current_org.local_llm_model,
            "ai_fallback_enabled": current_org.ai_fallback_enabled
        }
    }

@router.post("/backends/test")
async def test_ai_backend(
    test_request: AIBackendTestRequest,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Test a specific AI backend"""
    # Create temporary org config for testing
    test_org = Organization()
    test_org.ai_backend = test_request.backend
    test_org.local_llm_endpoint = current_org.local_llm_endpoint
    test_org.local_llm_model = current_org.local_llm_model
    test_org.ai_fallback_enabled = False  # No fallback for testing
    
    try:
        # Test the backend
        response = await hybrid_ai_service.process_chat_message(
            message=test_request.message,
            documents=[],
            chat_history=[],
            organization=test_org
        )
        
        return {
            "success": True,
            "backend": test_request.backend,
            "response": response.get("answer", ""),
            "model": response.get("model", "unknown"),
            "latency_ms": response.get("performance_metrics", {}).get("latency_ms", 0)
        }
        
    except Exception as e:
        logger.error(f"Backend test failed", extra={
            "backend": test_request.backend,
            "error": str(e)
        })
        
        return {
            "success": False,
            "backend": test_request.backend,
            "error": str(e)
        }

@router.get("/usage/stats")
async def get_ai_usage_stats(
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Get AI usage statistics for the organization"""
    # Get metrics from hybrid AI service
    backend_status = await hybrid_ai_service.get_backend_status()
    
    cloud_metrics = backend_status["backends"]["cloud"]
    local_metrics = backend_status["backends"]["local"]
    
    return {
        "usage": {
            "cloud": {
                "requests": cloud_metrics.get("requests", 0),
                "errors": cloud_metrics.get("errors", 0),
                "avg_latency_ms": cloud_metrics.get("avg_latency", 0),
                "success_rate": (
                    (cloud_metrics.get("requests", 0) - cloud_metrics.get("errors", 0)) / 
                    cloud_metrics.get("requests", 1) * 100
                ) if cloud_metrics.get("requests", 0) > 0 else 0
            },
            "local": {
                "requests": local_metrics.get("requests", 0),
                "errors": local_metrics.get("errors", 0),
                "avg_latency_ms": local_metrics.get("avg_latency", 0),
                "success_rate": (
                    (local_metrics.get("requests", 0) - local_metrics.get("errors", 0)) / 
                    local_metrics.get("requests", 1) * 100
                ) if local_metrics.get("requests", 0) > 0 else 0
            }
        },
        "current_backend": current_org.ai_backend,
        "fallback_count": 0  # Would track this in production
    }

@router.post("/backends/health-check")
async def check_backend_health(
    backend: str,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """Manually trigger health check for a backend"""
    if backend not in ["cloud", "local"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backend. Must be 'cloud' or 'local'"
        )
    
    # Force health check update
    if backend == "cloud":
        await hybrid_ai_service._update_backend_health(AIBackend.CLOUD)
    else:
        # Ensure local client is initialized with org settings
        hybrid_ai_service._get_local_client(current_org)
        await hybrid_ai_service._update_backend_health(AIBackend.LOCAL)
    
    # Get updated status
    health_info = hybrid_ai_service._backend_health[AIBackend(backend)]
    
    return {
        "backend": backend,
        "healthy": health_info["healthy"],
        "last_check": health_info["last_check"].isoformat() if health_info["last_check"] else None,
        "error": health_info["error"]
    }