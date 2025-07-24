from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from database import get_db
from models import (
    User, Organization, AnonymizationPattern, AnonymizationRule,
    RedactionToken
)
from auth import get_current_user

router = APIRouter(prefix="/api/anonymization", tags=["anonymization"])


# Pydantic models for API requests/responses
class PatternCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    regex_pattern: str = Field(..., min_length=1)
    pattern_type: str = Field(..., min_length=1, max_length=50)
    confidence_threshold: float = Field(0.8, ge=0.0, le=1.0)
    is_active: bool = True
    priority: int = Field(0, ge=0)


class PatternUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    regex_pattern: Optional[str] = Field(None, min_length=1)
    pattern_type: Optional[str] = Field(None, min_length=1, max_length=50)
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0)


class PatternResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    regex_pattern: str
    pattern_type: str
    confidence_threshold: float
    is_active: bool
    priority: int
    organization_id: Optional[str]
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RuleCreate(BaseModel):
    pattern_type: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., pattern="^(redact|preserve|conditional)$")
    condition: Optional[dict] = None
    requires_consent: bool = False
    consent_message: Optional[str] = None
    is_active: bool = True
    priority: int = Field(0, ge=0)


class RuleUpdate(BaseModel):
    pattern_type: Optional[str] = Field(None, min_length=1, max_length=50)
    action: Optional[str] = Field(None, pattern="^(redact|preserve|conditional)$")
    condition: Optional[dict] = None
    requires_consent: Optional[bool] = None
    consent_message: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0)


class RuleResponse(BaseModel):
    id: int
    pattern_type: str
    action: str
    condition: Optional[dict]
    requires_consent: bool
    consent_message: Optional[str]
    is_active: bool
    priority: int
    organization_id: Optional[str]
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TestAnonymizationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    use_org_patterns: bool = True
    use_user_patterns: bool = True
    custom_patterns: Optional[dict] = None


class TestAnonymizationResponse(BaseModel):
    original: str
    redacted: str
    sensitive_patterns: List[dict]
    needs_consent: bool
    confidence_score: float


# Pattern management endpoints
@router.post("/patterns", response_model=PatternResponse)
async def create_pattern(
    pattern: PatternCreate,
    scope: str = "user",  # "user" or "organization"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new anonymization pattern"""
    if scope not in ["user", "organization"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scope must be 'user' or 'organization'"
        )
    
    # Check permissions for organization scope
    if scope == "organization" and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can create organization patterns"
        )
    
    # Validate regex pattern
    import re
    try:
        re.compile(pattern.regex_pattern)
    except re.error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex pattern: {str(e)}"
        )
    
    # Create pattern
    db_pattern = AnonymizationPattern(
        **pattern.dict(),
        organization_id=current_user.organization_id if scope == "organization" else None,
        user_id=current_user.id if scope == "user" else None,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_pattern)
    db.commit()
    db.refresh(db_pattern)
    
    return db_pattern


@router.get("/patterns", response_model=List[PatternResponse])
async def list_patterns(
    scope: Optional[str] = None,
    pattern_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List anonymization patterns"""
    query = db.query(AnonymizationPattern)
    
    # Filter by scope
    if scope == "user":
        query = query.filter(AnonymizationPattern.user_id == current_user.id)
    elif scope == "organization":
        query = query.filter(AnonymizationPattern.organization_id == current_user.organization_id)
    else:
        # Return both user and organization patterns
        query = query.filter(
            (AnonymizationPattern.user_id == current_user.id) |
            (AnonymizationPattern.organization_id == current_user.organization_id)
        )
    
    # Additional filters
    if pattern_type:
        query = query.filter(AnonymizationPattern.pattern_type == pattern_type)
    if is_active is not None:
        query = query.filter(AnonymizationPattern.is_active == is_active)
    
    # Order by priority
    patterns = query.order_by(AnonymizationPattern.priority.desc()).all()
    
    return patterns


@router.get("/patterns/{pattern_id}", response_model=PatternResponse)
async def get_pattern(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific anonymization pattern"""
    pattern = db.query(AnonymizationPattern).filter(
        AnonymizationPattern.id == pattern_id,
        (
            (AnonymizationPattern.user_id == current_user.id) |
            (AnonymizationPattern.organization_id == current_user.organization_id)
        )
    ).first()
    
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    return pattern


@router.patch("/patterns/{pattern_id}", response_model=PatternResponse)
async def update_pattern(
    pattern_id: int,
    pattern_update: PatternUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an anonymization pattern"""
    pattern = db.query(AnonymizationPattern).filter(
        AnonymizationPattern.id == pattern_id
    ).first()
    
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    # Check permissions
    if pattern.user_id and pattern.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update another user's pattern"
        )
    
    if pattern.organization_id and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update organization patterns"
        )
    
    # Validate regex if provided
    if pattern_update.regex_pattern:
        import re
        try:
            re.compile(pattern_update.regex_pattern)
        except re.error as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid regex pattern: {str(e)}"
            )
    
    # Update pattern
    update_data = pattern_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pattern, field, value)
    
    pattern.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(pattern)
    
    return pattern


@router.delete("/patterns/{pattern_id}")
async def delete_pattern(
    pattern_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an anonymization pattern"""
    pattern = db.query(AnonymizationPattern).filter(
        AnonymizationPattern.id == pattern_id
    ).first()
    
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    # Check permissions
    if pattern.user_id and pattern.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's pattern"
        )
    
    if pattern.organization_id and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can delete organization patterns"
        )
    
    db.delete(pattern)
    db.commit()
    
    return {"status": "success", "message": "Pattern deleted"}


# Rule management endpoints
@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    rule: RuleCreate,
    scope: str = "user",  # "user" or "organization"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new anonymization rule"""
    if scope not in ["user", "organization"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scope must be 'user' or 'organization'"
        )
    
    # Check permissions for organization scope
    if scope == "organization" and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can create organization rules"
        )
    
    # Create rule
    db_rule = AnonymizationRule(
        **rule.dict(),
        organization_id=current_user.organization_id if scope == "organization" else None,
        user_id=current_user.id if scope == "user" else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    
    return db_rule


@router.get("/rules", response_model=List[RuleResponse])
async def list_rules(
    scope: Optional[str] = None,
    pattern_type: Optional[str] = None,
    action: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List anonymization rules"""
    query = db.query(AnonymizationRule)
    
    # Filter by scope
    if scope == "user":
        query = query.filter(AnonymizationRule.user_id == current_user.id)
    elif scope == "organization":
        query = query.filter(AnonymizationRule.organization_id == current_user.organization_id)
    else:
        # Return both user and organization rules
        query = query.filter(
            (AnonymizationRule.user_id == current_user.id) |
            (AnonymizationRule.organization_id == current_user.organization_id)
        )
    
    # Additional filters
    if pattern_type:
        query = query.filter(AnonymizationRule.pattern_type == pattern_type)
    if action:
        query = query.filter(AnonymizationRule.action == action)
    if is_active is not None:
        query = query.filter(AnonymizationRule.is_active == is_active)
    
    # Order by priority
    rules = query.order_by(AnonymizationRule.priority.desc()).all()
    
    return rules


@router.patch("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    rule_update: RuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an anonymization rule"""
    rule = db.query(AnonymizationRule).filter(
        AnonymizationRule.id == rule_id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    # Check permissions
    if rule.user_id and rule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update another user's rule"
        )
    
    if rule.organization_id and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update organization rules"
        )
    
    # Update rule
    update_data = rule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    rule.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(rule)
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an anonymization rule"""
    rule = db.query(AnonymizationRule).filter(
        AnonymizationRule.id == rule_id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    # Check permissions
    if rule.user_id and rule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's rule"
        )
    
    if rule.organization_id and current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can delete organization rules"
        )
    
    db.delete(rule)
    db.commit()
    
    return {"status": "success", "message": "Rule deleted"}


# Test endpoint
@router.post("/test", response_model=TestAnonymizationResponse)
async def test_anonymization(
    request: TestAnonymizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test anonymization on sample text"""
    from services.anonymization_service import AnonymizationService
    
    service = AnonymizationService()
    
    # Perform anonymization
    result = service.anonymize_text(
        text=request.text,
        db=db,
        user_id=current_user.id if request.use_user_patterns else None,
        org_id=current_user.organization_id if request.use_org_patterns else None,
        custom_patterns=request.custom_patterns
    )
    
    return TestAnonymizationResponse(
        original=result.original,
        redacted=result.redacted,
        sensitive_patterns=[
            {
                "type": p.type,
                "pattern": p.pattern,
                "confidence": p.confidence,
                "original_text": p.original_text[:20] + "..." if len(p.original_text) > 20 else p.original_text,
                "replacement": p.replacement
            }
            for p in result.sensitive_patterns
        ],
        needs_consent=result.needs_consent,
        confidence_score=result.confidence_score
    )


# Redaction token management
@router.get("/tokens")
async def list_redaction_tokens(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List redaction tokens for the current user"""
    tokens = db.query(RedactionToken).filter(
        (RedactionToken.user_id == current_user.id) |
        (RedactionToken.organization_id == current_user.organization_id)
    ).order_by(RedactionToken.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": t.id,
            "token": t.token,
            "created_at": t.created_at,
            "expires_at": t.expires_at
        }
        for t in tokens
    ]


@router.post("/deanonymize")
async def deanonymize_text(
    text: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reverse anonymization using stored tokens"""
    from services.anonymization_service import AnonymizationService
    
    service = AnonymizationService()
    
    deanonymized = service.deanonymize_text(
        text=text,
        db=db,
        user_id=current_user.id,
        org_id=current_user.organization_id
    )
    
    return {"deanonymized_text": deanonymized}