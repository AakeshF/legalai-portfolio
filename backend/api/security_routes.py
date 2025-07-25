from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from database import get_db
from models import User
from auth import get_current_user, require_admin
from services.security_enforcement import SecurityEnforcementService, SecurityAction

router = APIRouter(prefix="/api/security", tags=["security"])


# Pydantic models
class SecurityCheckRequest(BaseModel):
    content: str = Field(..., min_length=1)
    operation_type: str = Field(..., pattern="^(chat|analysis|storage|export)$")
    document_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SecurityCheckResponse(BaseModel):
    action: str
    classification: str
    reasons: list[str]
    required_consents: list[str]
    redaction_required: bool
    audit_log_id: Optional[int]


class ComplianceReportRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class DataRetentionResponse(BaseModel):
    prompt_logs_anonymized: int
    audit_logs_marked: int
    documents_processed: int
    retention_days: int


class SecurityPolicyUpdate(BaseModel):
    classification: str = Field(
        ..., pattern="^(public|internal|confidential|restricted|privileged)$"
    )
    policies: Dict[str, Any]


# Security check endpoint
@router.post("/check", response_model=SecurityCheckResponse)
async def check_security(
    request: SecurityCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check security policies for content before processing"""
    service = SecurityEnforcementService()

    decision = await service.enforce_security_policy(
        content=request.content,
        operation_type=request.operation_type,
        db=db,
        user_id=current_user.id,
        org_id=current_user.organization_id,
        document_id=request.document_id,
        metadata=request.metadata,
    )

    # Handle blocking actions
    if decision.action == SecurityAction.BLOCK:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Operation blocked by security policy",
                "reasons": decision.reasons,
                "classification": decision.classification.value,
            },
        )

    return SecurityCheckResponse(
        action=decision.action.value,
        classification=decision.classification.value,
        reasons=decision.reasons,
        required_consents=[c.value for c in decision.required_consents],
        redaction_required=decision.redaction_required,
        audit_log_id=decision.audit_log_id,
    )


# Compliance reporting
@router.post("/compliance/report")
async def generate_compliance_report(
    request: ComplianceReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Generate compliance report (admin only)"""
    service = SecurityEnforcementService()

    report = await service.generate_compliance_report(
        db=db,
        org_id=current_user.organization_id,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    return report


@router.get("/compliance/score")
async def get_compliance_score(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get current compliance score"""
    service = SecurityEnforcementService()

    # Generate report for last 30 days
    report = await service.generate_compliance_report(
        db=db, org_id=current_user.organization_id
    )

    return {
        "compliance_score": report["compliance_score"],
        "period": report["report_period"],
        "components": {
            "consent_compliance": report["consent_compliance"]["consent_rate"],
            "security_compliance": 100 - report["security_summary"]["block_rate"],
            "review_compliance": (
                (
                    report["prompt_review_stats"]["auto_approved"]
                    + report["prompt_review_stats"]["manually_reviewed"]
                )
                / report["prompt_review_stats"]["total_prompts"]
                * 100
                if report["prompt_review_stats"]["total_prompts"] > 0
                else 100
            ),
        },
    }


# Data retention enforcement
@router.post("/retention/enforce", response_model=DataRetentionResponse)
async def enforce_data_retention(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Enforce data retention policy (admin only)"""
    service = SecurityEnforcementService()

    # Run in background to avoid timeout
    background_tasks.add_task(
        service.enforce_data_retention_policy, db, current_user.organization_id
    )

    # Get current retention settings
    from models import ConsentPreference

    pref = (
        db.query(ConsentPreference)
        .filter(ConsentPreference.organization_id == current_user.organization_id)
        .first()
    )

    retention_days = pref.data_retention_days if pref else 90

    return DataRetentionResponse(
        prompt_logs_anonymized=0,  # Will be updated by background task
        audit_logs_marked=0,
        documents_processed=0,
        retention_days=retention_days,
    )


# Security policies management
@router.get("/policies")
async def get_security_policies(
    db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Get current security policies (admin only)"""
    from services.security_enforcement import DataClassification

    # Get organization
    from models import Organization

    org = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )

    # Default policies
    default_policies = {
        "public": {
            "allow_cloud_ai": True,
            "require_consent": False,
            "require_review": False,
            "redaction_level": "none",
        },
        "internal": {
            "allow_cloud_ai": True,
            "require_consent": False,
            "require_review": False,
            "redaction_level": "minimal",
        },
        "confidential": {
            "allow_cloud_ai": True,
            "require_consent": True,
            "require_review": False,
            "redaction_level": "standard",
        },
        "restricted": {
            "allow_cloud_ai": False,
            "require_consent": True,
            "require_review": True,
            "redaction_level": "strict",
        },
        "privileged": {
            "allow_cloud_ai": False,
            "require_consent": True,
            "require_review": True,
            "redaction_level": "maximum",
        },
    }

    # Apply organization overrides
    if hasattr(org, "security_policies") and org.security_policies:
        for classification, policies in org.security_policies.items():
            if classification in default_policies:
                default_policies[classification].update(policies)

    return default_policies


@router.put("/policies/{classification}")
async def update_security_policy(
    classification: str,
    update: SecurityPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update security policy for a classification (admin only)"""
    # Validate classification
    valid_classifications = [
        "public",
        "internal",
        "confidential",
        "restricted",
        "privileged",
    ]
    if classification not in valid_classifications:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid classification. Must be one of: {', '.join(valid_classifications)}",
        )

    # Get organization
    from models import Organization

    org = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )

    # Initialize security_policies if not exists
    if not hasattr(org, "security_policies") or not org.security_policies:
        org.security_policies = {}

    # Update policies
    org.security_policies[classification] = update.policies

    # Save to database (assuming security_policies is a JSON column)
    # In production, this would be properly handled with SQLAlchemy
    db.commit()

    return {
        "status": "success",
        "message": f"Security policy updated for {classification}",
        "policies": update.policies,
    }


# Security incidents
@router.get("/incidents")
async def get_security_incidents(
    limit: int = 50,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get security incidents (admin only)"""
    # In production, this would query from a dedicated incidents table
    # For now, we'll return audit logs that indicate security issues
    from models import AIAuditLog
    import json

    query = db.query(AIAuditLog).filter(
        AIAuditLog.organization_id == current_user.organization_id,
        AIAuditLog.decision_type == "security_enforcement",
    )

    logs = query.order_by(AIAuditLog.request_timestamp.desc()).limit(limit).all()

    incidents = []
    for log in logs:
        if log.decision_summary:
            decision = json.loads(log.decision_summary)
            if decision.get("action") in ["block", "require_review"]:
                incidents.append(
                    {
                        "id": log.id,
                        "timestamp": log.request_timestamp.isoformat(),
                        "user_id": log.user_id,
                        "action": decision.get("action"),
                        "classification": decision.get("classification"),
                        "reasons": decision.get("reasons", []),
                        "severity": (
                            "high" if decision.get("action") == "block" else "medium"
                        ),
                    }
                )

    # Filter by severity if requested
    if severity:
        incidents = [i for i in incidents if i["severity"] == severity]

    return {"total": len(incidents), "incidents": incidents}


# Real-time security status
@router.get("/status")
async def get_security_status(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get real-time security status"""
    from sqlalchemy import func
    from models import AIAuditLog, PromptLog
    import json

    # Get stats for last 24 hours
    cutoff = datetime.utcnow() - timedelta(hours=24)

    # Count blocked requests
    blocked_count = (
        db.query(func.count(AIAuditLog.id))
        .filter(
            AIAuditLog.organization_id == current_user.organization_id,
            AIAuditLog.request_timestamp >= cutoff,
            AIAuditLog.decision_summary.like('%"action": "block"%'),
        )
        .scalar()
        or 0
    )

    # Count pending reviews
    pending_reviews = (
        db.query(func.count(PromptLog.id))
        .filter(
            PromptLog.organization_id == current_user.organization_id,
            PromptLog.status == "pending",
            PromptLog.created_at >= cutoff,
        )
        .scalar()
        or 0
    )

    # Get compliance score
    service = SecurityEnforcementService()
    report = await service.generate_compliance_report(db, current_user.organization_id)

    return {
        "status": "operational",
        "last_24_hours": {
            "blocked_requests": blocked_count,
            "pending_reviews": pending_reviews,
        },
        "compliance_score": report["compliance_score"],
        "security_level": "high" if report["compliance_score"] > 80 else "medium",
    }


from datetime import timedelta
