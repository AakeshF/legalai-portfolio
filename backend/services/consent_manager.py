# services/consent_manager.py - AI processing consent management
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    Text,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
import enum
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class ConsentType(enum.Enum):
    """Types of AI processing consent"""

    CLOUD_AI = "cloud_ai"
    LOCAL_AI = "local_ai"
    THIRD_PARTY_SHARING = "third_party_sharing"
    DATA_RETENTION = "data_retention"
    ANALYTICS = "analytics"


class ConsentScope(enum.Enum):
    """Scope of consent"""

    ORGANIZATION = "organization"
    USER = "user"
    DOCUMENT = "document"
    SESSION = "session"


class ConsentRecord(Base):
    """Database model for consent records"""

    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)

    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    consent_scope = Column(SQLEnum(ConsentScope), nullable=False)
    granted = Column(Boolean, nullable=False)

    # Consent details
    purpose = Column(Text)
    data_categories = Column(Text)  # JSON array of data categories
    providers_allowed = Column(Text)  # JSON array of allowed AI providers

    # Timestamps
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    # Audit trail
    granted_by = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String(45))
    user_agent = Column(String(255))

    # Legal basis
    legal_basis = Column(String(50))  # consent, legitimate_interest, contract, etc.
    version = Column(String(20))  # Privacy policy version


class ConsentPreference(Base):
    """Organization-wide consent preferences"""

    __tablename__ = "consent_preferences"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), unique=True)

    # Default preferences
    require_explicit_consent = Column(Boolean, default=True)
    default_ai_provider = Column(String(50))
    allowed_providers = Column(Text)  # JSON array

    # Data handling preferences
    allow_cloud_processing = Column(Boolean, default=True)
    require_local_only = Column(Boolean, default=False)
    data_retention_days = Column(Integer, default=90)

    # Notification preferences
    notify_on_processing = Column(Boolean, default=False)
    consent_renewal_days = Column(Integer, default=365)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConsentManager:
    """Manage AI processing consent for organizations and users"""

    def __init__(self, db: Session):
        self.db = db
        logger.info("Consent Manager initialized")

    def record_consent(
        self,
        organization_id: int,
        consent_type: ConsentType,
        granted: bool,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        scope: ConsentScope = ConsentScope.ORGANIZATION,
        purpose: Optional[str] = None,
        providers_allowed: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentRecord:
        """Record a consent decision"""

        # Check for existing active consent
        existing = self._get_active_consent(
            organization_id, consent_type, user_id, document_id, scope
        )

        if existing:
            # Revoke existing consent if the decision changed
            if existing.granted != granted:
                existing.revoked_at = datetime.utcnow()
                self.db.commit()
            else:
                # Update existing consent
                return existing

        # Create new consent record
        consent = ConsentRecord(
            organization_id=organization_id,
            user_id=user_id,
            document_id=document_id,
            consent_type=consent_type,
            consent_scope=scope,
            granted=granted,
            purpose=purpose,
            providers_allowed=(
                json.dumps(providers_allowed) if providers_allowed else None
            ),
            granted_by=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            legal_basis="consent",
            version="1.0",  # Should be tied to privacy policy version
        )

        if expires_in_days:
            consent.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        self.db.add(consent)
        self.db.commit()

        logger.info(
            f"Consent recorded: org={organization_id}, type={consent_type.value}, "
            f"granted={granted}, scope={scope.value}"
        )

        return consent

    def check_consent(
        self,
        organization_id: int,
        consent_type: ConsentType,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check if consent is granted for a specific action"""

        # Check organization preferences first
        preferences = self.get_organization_preferences(organization_id)

        # Check specific consent records (most specific to least specific)
        scopes_to_check = []

        if document_id:
            scopes_to_check.append((ConsentScope.DOCUMENT, user_id, document_id))
        if user_id:
            scopes_to_check.append((ConsentScope.USER, user_id, None))
        scopes_to_check.append((ConsentScope.ORGANIZATION, None, None))

        for scope, uid, did in scopes_to_check:
            consent = self._get_active_consent(
                organization_id, consent_type, uid, did, scope
            )

            if consent:
                # Check if provider is allowed
                if provider and consent.providers_allowed:
                    allowed_providers = json.loads(consent.providers_allowed)
                    if provider not in allowed_providers:
                        continue

                return {
                    "granted": consent.granted,
                    "scope": consent.consent_scope.value,
                    "expires_at": (
                        consent.expires_at.isoformat() if consent.expires_at else None
                    ),
                    "providers_allowed": (
                        json.loads(consent.providers_allowed)
                        if consent.providers_allowed
                        else None
                    ),
                    "purpose": consent.purpose,
                    "consent_id": consent.id,
                }

        # No explicit consent found, check if explicit consent is required
        if preferences and not preferences.require_explicit_consent:
            # Use default preferences
            return {
                "granted": (
                    preferences.allow_cloud_processing
                    if consent_type == ConsentType.CLOUD_AI
                    else True
                ),
                "scope": "default",
                "providers_allowed": (
                    json.loads(preferences.allowed_providers)
                    if preferences.allowed_providers
                    else None
                ),
                "source": "organization_defaults",
            }

        # No consent found and explicit consent required
        return {
            "granted": False,
            "scope": None,
            "reason": "no_consent_found",
            "require_explicit": True,
        }

    def _get_active_consent(
        self,
        organization_id: int,
        consent_type: ConsentType,
        user_id: Optional[int],
        document_id: Optional[int],
        scope: ConsentScope,
    ) -> Optional[ConsentRecord]:
        """Get active consent record"""

        query = self.db.query(ConsentRecord).filter(
            ConsentRecord.organization_id == organization_id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.consent_scope == scope,
            ConsentRecord.revoked_at.is_(None),
        )

        if scope == ConsentScope.USER and user_id:
            query = query.filter(ConsentRecord.user_id == user_id)
        elif scope == ConsentScope.DOCUMENT and document_id:
            query = query.filter(ConsentRecord.document_id == document_id)

        consent = query.first()

        # Check if consent is expired
        if consent and consent.expires_at and consent.expires_at < datetime.utcnow():
            return None

        return consent

    def revoke_consent(self, consent_id: int, revoked_by: Optional[int] = None) -> bool:
        """Revoke a consent"""

        consent = self.db.query(ConsentRecord).filter_by(id=consent_id).first()
        if not consent or consent.revoked_at:
            return False

        consent.revoked_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Consent {consent_id} revoked by user {revoked_by}")
        return True

    def get_consent_history(
        self,
        organization_id: int,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        include_revoked: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get consent history"""

        query = self.db.query(ConsentRecord).filter(
            ConsentRecord.organization_id == organization_id
        )

        if user_id:
            query = query.filter(ConsentRecord.user_id == user_id)
        if document_id:
            query = query.filter(ConsentRecord.document_id == document_id)
        if not include_revoked:
            query = query.filter(ConsentRecord.revoked_at.is_(None))

        consents = query.order_by(ConsentRecord.granted_at.desc()).all()

        return [
            {
                "id": c.id,
                "consent_type": c.consent_type.value,
                "scope": c.consent_scope.value,
                "granted": c.granted,
                "granted_at": c.granted_at.isoformat(),
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
                "purpose": c.purpose,
                "providers_allowed": (
                    json.loads(c.providers_allowed) if c.providers_allowed else None
                ),
            }
            for c in consents
        ]

    def set_organization_preferences(
        self, organization_id: int, preferences: Dict[str, Any]
    ) -> ConsentPreference:
        """Set organization-wide consent preferences"""

        pref = (
            self.db.query(ConsentPreference)
            .filter_by(organization_id=organization_id)
            .first()
        )

        if not pref:
            pref = ConsentPreference(organization_id=organization_id)
            self.db.add(pref)

        # Update preferences
        for key, value in preferences.items():
            if hasattr(pref, key):
                if key == "allowed_providers" and isinstance(value, list):
                    value = json.dumps(value)
                setattr(pref, key, value)

        pref.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Organization {organization_id} consent preferences updated")
        return pref

    def get_organization_preferences(
        self, organization_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get organization consent preferences"""

        pref = (
            self.db.query(ConsentPreference)
            .filter_by(organization_id=organization_id)
            .first()
        )

        if not pref:
            return None

        return {
            "require_explicit_consent": pref.require_explicit_consent,
            "default_ai_provider": pref.default_ai_provider,
            "allowed_providers": (
                json.loads(pref.allowed_providers) if pref.allowed_providers else []
            ),
            "allow_cloud_processing": pref.allow_cloud_processing,
            "require_local_only": pref.require_local_only,
            "data_retention_days": pref.data_retention_days,
            "notify_on_processing": pref.notify_on_processing,
            "consent_renewal_days": pref.consent_renewal_days,
        }

    def get_compliance_report(
        self,
        organization_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate consent compliance report"""

        query = self.db.query(ConsentRecord).filter(
            ConsentRecord.organization_id == organization_id
        )

        if start_date:
            query = query.filter(ConsentRecord.granted_at >= start_date)
        if end_date:
            query = query.filter(ConsentRecord.granted_at <= end_date)

        consents = query.all()

        # Analyze consents
        total_consents = len(consents)
        granted_consents = sum(1 for c in consents if c.granted and not c.revoked_at)
        revoked_consents = sum(1 for c in consents if c.revoked_at)
        expired_consents = sum(
            1
            for c in consents
            if c.expires_at and c.expires_at < datetime.utcnow() and not c.revoked_at
        )

        # Group by type
        by_type = {}
        for consent_type in ConsentType:
            type_consents = [c for c in consents if c.consent_type == consent_type]
            by_type[consent_type.value] = {
                "total": len(type_consents),
                "granted": sum(
                    1 for c in type_consents if c.granted and not c.revoked_at
                ),
                "revoked": sum(1 for c in type_consents if c.revoked_at),
            }

        return {
            "organization_id": organization_id,
            "report_period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "summary": {
                "total_consents": total_consents,
                "granted_consents": granted_consents,
                "revoked_consents": revoked_consents,
                "expired_consents": expired_consents,
                "consent_rate": (
                    (granted_consents / total_consents * 100)
                    if total_consents > 0
                    else 0
                ),
            },
            "by_type": by_type,
            "generated_at": datetime.utcnow().isoformat(),
        }
