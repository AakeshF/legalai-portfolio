from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from database import get_db
from models import User, Organization, ConsentType, ConsentScope
from auth import get_current_user
from services.consent_manager import ConsentManager

router = APIRouter(prefix="/api/consent", tags=["consent"])


# Pydantic models
class ConsentRequest(BaseModel):
    consent_type: str = Field(..., pattern="^(cloud_ai|local_ai|third_party_sharing|data_retention|analytics)$")
    granted: bool
    scope: str = Field("organization", pattern="^(organization|user|document|session)$")
    purpose: Optional[str] = None
    providers_allowed: Optional[List[str]] = None
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650)
    document_id: Optional[str] = None


class ConsentResponse(BaseModel):
    id: int
    consent_type: str
    scope: str
    granted: bool
    granted_at: str
    expires_at: Optional[str]
    purpose: Optional[str]
    providers_allowed: Optional[List[str]]
    
    class Config:
        from_attributes = True


class ConsentCheckResponse(BaseModel):
    granted: bool
    scope: Optional[str]
    expires_at: Optional[str] = None
    providers_allowed: Optional[List[str]] = None
    purpose: Optional[str] = None
    reason: Optional[str] = None
    require_explicit: Optional[bool] = None


class OrganizationPreferences(BaseModel):
    require_explicit_consent: bool = True
    default_ai_provider: Optional[str] = None
    allowed_providers: List[str] = []
    allow_cloud_processing: bool = True
    require_local_only: bool = False
    data_retention_days: int = Field(90, ge=1, le=3650)
    notify_on_processing: bool = False
    consent_renewal_days: int = Field(365, ge=1, le=3650)


class ComplianceReportResponse(BaseModel):
    organization_id: str
    report_period: Dict[str, Optional[str]]
    summary: Dict[str, Any]
    by_type: Dict[str, Dict[str, int]]
    generated_at: str


# Consent management endpoints
@router.post("/record", response_model=ConsentResponse)
async def record_consent(
    request: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record user consent for AI processing"""
    manager = ConsentManager(db)
    
    # Convert string enums
    consent_type = ConsentType[request.consent_type.upper()]
    scope = ConsentScope[request.scope.upper()]
    
    # Get user's IP and user agent from request context
    # In production, these would come from the request headers
    ip_address = "127.0.0.1"  # TODO: Get from request
    user_agent = "Mozilla/5.0"  # TODO: Get from request
    
    consent = manager.record_consent(
        organization_id=current_user.organization_id,
        consent_type=consent_type,
        granted=request.granted,
        user_id=current_user.id if scope in [ConsentScope.USER, ConsentScope.DOCUMENT] else None,
        document_id=request.document_id if scope == ConsentScope.DOCUMENT else None,
        scope=scope,
        purpose=request.purpose,
        providers_allowed=request.providers_allowed,
        expires_in_days=request.expires_in_days,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return ConsentResponse(
        id=consent.id,
        consent_type=consent.consent_type.value,
        scope=consent.consent_scope.value,
        granted=consent.granted,
        granted_at=consent.granted_at.isoformat(),
        expires_at=consent.expires_at.isoformat() if consent.expires_at else None,
        purpose=consent.purpose,
        providers_allowed=json.loads(consent.providers_allowed) if consent.providers_allowed else None
    )


@router.get("/check")
async def check_consent(
    consent_type: str = Query(..., pattern="^(cloud_ai|local_ai|third_party_sharing|data_retention|analytics)$"),
    provider: Optional[str] = None,
    document_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ConsentCheckResponse:
    """Check if consent is granted for a specific action"""
    manager = ConsentManager(db)
    
    # Convert string enum
    consent_type_enum = ConsentType[consent_type.upper()]
    
    result = manager.check_consent(
        organization_id=current_user.organization_id,
        consent_type=consent_type_enum,
        user_id=current_user.id,
        document_id=document_id,
        provider=provider
    )
    
    return ConsentCheckResponse(**result)


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_consent_history(
    include_revoked: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's consent history"""
    manager = ConsentManager(db)
    
    return manager.get_consent_history(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        include_revoked=include_revoked
    )


@router.post("/revoke/{consent_id}")
async def revoke_consent(
    consent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a previously granted consent"""
    manager = ConsentManager(db)
    
    # Verify consent belongs to user
    from models import ConsentRecord
    consent = db.query(ConsentRecord).filter(
        ConsentRecord.id == consent_id,
        ConsentRecord.organization_id == current_user.organization_id
    ).first()
    
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found"
        )
    
    # Check permissions
    if consent.user_id and consent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke another user's consent"
        )
    
    success = manager.revoke_consent(consent_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke consent"
        )
    
    return {"status": "success", "message": "Consent revoked"}


# Organization preferences (admin only)
@router.get("/organization/preferences", response_model=OrganizationPreferences)
async def get_organization_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get organization consent preferences"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can view organization preferences"
        )
    
    manager = ConsentManager(db)
    preferences = manager.get_organization_preferences(current_user.organization_id)
    
    if not preferences:
        # Return defaults
        return OrganizationPreferences()
    
    return preferences


@router.put("/organization/preferences")
async def update_organization_preferences(
    preferences: OrganizationPreferences,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update organization consent preferences"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update organization preferences"
        )
    
    manager = ConsentManager(db)
    
    updated = manager.set_organization_preferences(
        current_user.organization_id,
        preferences.dict()
    )
    
    return {
        "status": "success",
        "message": "Organization preferences updated",
        "updated_at": updated.updated_at.isoformat()
    }


@router.get("/compliance/report", response_model=ComplianceReportResponse)
async def get_compliance_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate consent compliance report"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can view compliance reports"
        )
    
    manager = ConsentManager(db)
    
    report = manager.get_compliance_report(
        organization_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return report


# Batch consent operations
@router.post("/batch/grant")
async def grant_batch_consent(
    consent_types: List[str],
    scope: str = "user",
    providers_allowed: Optional[List[str]] = None,
    expires_in_days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Grant consent for multiple types at once"""
    manager = ConsentManager(db)
    scope_enum = ConsentScope[scope.upper()]
    
    results = []
    for consent_type_str in consent_types:
        try:
            consent_type = ConsentType[consent_type_str.upper()]
            consent = manager.record_consent(
                organization_id=current_user.organization_id,
                consent_type=consent_type,
                granted=True,
                user_id=current_user.id if scope_enum == ConsentScope.USER else None,
                scope=scope_enum,
                providers_allowed=providers_allowed,
                expires_in_days=expires_in_days
            )
            results.append({
                "consent_type": consent_type.value,
                "success": True,
                "consent_id": consent.id
            })
        except Exception as e:
            results.append({
                "consent_type": consent_type_str,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results}


# Required for proper JSON handling
import json