import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import logging
import json
from dataclasses import dataclass
from enum import Enum

from models import (
    User,
    Organization,
    Document,
    PromptLog,
    ConsentRecord,
    AIAuditLog,
    ConsentType,
    ConsentScope,
)
from services.sensitive_data_detector import SensitiveDataDetector
from services.consent_manager import ConsentManager

logger = logging.getLogger(__name__)


class SecurityAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_CONSENT = "require_consent"
    REQUIRE_REVIEW = "require_review"
    REDACT = "redact"
    LOG_ONLY = "log_only"


class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PRIVILEGED = "privileged"


@dataclass
class SecurityDecision:
    action: SecurityAction
    classification: DataClassification
    reasons: List[str]
    required_consents: List[ConsentType]
    redaction_required: bool
    audit_log_id: Optional[int] = None


@dataclass
class SecurityIncident:
    incident_type: str
    severity: str  # low, medium, high, critical
    description: str
    user_id: str
    organization_id: str
    timestamp: datetime
    details: Dict[str, Any]
    resolved: bool = False


class SecurityEnforcementService:
    """
    Comprehensive security enforcement for AI operations
    """

    def __init__(self):
        self.sensitive_detector = SensitiveDataDetector()
        self.incident_handlers = {}
        self._policy_cache = {}
        self._cache_ttl = timedelta(minutes=5)

    async def enforce_security_policy(
        self,
        content: str,
        operation_type: str,
        db: Session,
        user_id: str,
        org_id: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecurityDecision:
        """
        Enforce security policies on content before AI processing
        """
        # Step 1: Detect sensitive data
        sensitivity_analysis = await self.sensitive_detector.analyze(
            content, db, user_id, org_id
        )

        # Step 2: Classify data
        classification = self._classify_data(sensitivity_analysis)

        # Step 3: Get applicable policies
        policies = await self._get_security_policies(db, org_id, classification)

        # Step 4: Check consent requirements
        consent_manager = ConsentManager(db)
        required_consents = []
        consent_granted = True

        for consent_type in self._get_required_consents(classification, operation_type):
            consent_result = consent_manager.check_consent(
                org_id, consent_type, user_id, document_id
            )
            if not consent_result.get("granted", False):
                consent_granted = False
                required_consents.append(consent_type)

        # Step 5: Make security decision
        decision = self._make_security_decision(
            classification,
            sensitivity_analysis,
            policies,
            consent_granted,
            required_consents,
        )

        # Step 6: Log audit trail
        audit_log_id = await self._log_security_audit(
            db, user_id, org_id, operation_type, decision, metadata
        )
        decision.audit_log_id = audit_log_id

        # Step 7: Handle incidents if needed
        if decision.action in [SecurityAction.BLOCK, SecurityAction.REQUIRE_REVIEW]:
            await self._create_security_incident(
                db, user_id, org_id, operation_type, decision, sensitivity_analysis
            )

        return decision

    def _classify_data(
        self, sensitivity_analysis: Dict[str, Any]
    ) -> DataClassification:
        """Classify data based on sensitivity analysis"""
        sensitivity_score = sensitivity_analysis.get("overall_sensitivity", 0)
        categories = sensitivity_analysis.get("categories", {})

        # Check for privileged content
        if "privileged" in categories or "attorney_client" in categories.get(
            "legal", []
        ):
            return DataClassification.PRIVILEGED

        # Check for restricted content
        if sensitivity_score > 0.8 or any(
            cat in categories for cat in ["medical", "financial"]
        ):
            return DataClassification.RESTRICTED

        # Check for confidential content
        if sensitivity_score > 0.5 or "legal" in categories:
            return DataClassification.CONFIDENTIAL

        # Check for internal content
        if sensitivity_score > 0.2 or "pii" in categories:
            return DataClassification.INTERNAL

        return DataClassification.PUBLIC

    async def _get_security_policies(
        self, db: Session, org_id: str, classification: DataClassification
    ) -> Dict[str, Any]:
        """Get applicable security policies"""
        cache_key = f"{org_id}:{classification.value}"

        # Check cache
        if cache_key in self._policy_cache:
            cached_time, policies = self._policy_cache[cache_key]
            if datetime.utcnow() - cached_time < self._cache_ttl:
                return policies

        # Get organization settings
        org = db.query(Organization).filter(Organization.id == org_id).first()

        # Default policies by classification
        default_policies = {
            DataClassification.PUBLIC: {
                "allow_cloud_ai": True,
                "require_consent": False,
                "require_review": False,
                "redaction_level": "none",
            },
            DataClassification.INTERNAL: {
                "allow_cloud_ai": True,
                "require_consent": False,
                "require_review": False,
                "redaction_level": "minimal",
            },
            DataClassification.CONFIDENTIAL: {
                "allow_cloud_ai": True,
                "require_consent": True,
                "require_review": False,
                "redaction_level": "standard",
            },
            DataClassification.RESTRICTED: {
                "allow_cloud_ai": False,
                "require_consent": True,
                "require_review": True,
                "redaction_level": "strict",
            },
            DataClassification.PRIVILEGED: {
                "allow_cloud_ai": False,
                "require_consent": True,
                "require_review": True,
                "redaction_level": "maximum",
            },
        }

        policies = default_policies.get(classification, {})

        # Apply organization overrides
        if hasattr(org, "security_policies") and org.security_policies:
            policies.update(org.security_policies.get(classification.value, {}))

        # Cache policies
        self._policy_cache[cache_key] = (datetime.utcnow(), policies)

        return policies

    def _get_required_consents(
        self, classification: DataClassification, operation_type: str
    ) -> List[ConsentType]:
        """Determine required consents based on classification"""
        consents = []

        if classification in [
            DataClassification.CONFIDENTIAL,
            DataClassification.RESTRICTED,
            DataClassification.PRIVILEGED,
        ]:
            consents.append(ConsentType.CLOUD_AI)

        if classification == DataClassification.RESTRICTED:
            consents.append(ConsentType.THIRD_PARTY_SHARING)

        if operation_type == "storage":
            consents.append(ConsentType.DATA_RETENTION)

        if operation_type == "analytics":
            consents.append(ConsentType.ANALYTICS)

        return consents

    def _make_security_decision(
        self,
        classification: DataClassification,
        sensitivity_analysis: Dict[str, Any],
        policies: Dict[str, Any],
        consent_granted: bool,
        required_consents: List[ConsentType],
    ) -> SecurityDecision:
        """Make final security decision"""
        reasons = []
        action = SecurityAction.ALLOW

        # Check consent requirements
        if required_consents and not consent_granted:
            action = SecurityAction.REQUIRE_CONSENT
            reasons.append(
                f"Missing consent for: {', '.join(c.value for c in required_consents)}"
            )

        # Check review requirements
        elif policies.get("require_review", False):
            action = SecurityAction.REQUIRE_REVIEW
            reasons.append(f"Manual review required for {classification.value} data")

        # Check cloud AI restrictions
        elif not policies.get("allow_cloud_ai", True):
            action = SecurityAction.BLOCK
            reasons.append(f"Cloud AI not allowed for {classification.value} data")

        # Determine redaction requirements
        redaction_required = policies.get("redaction_level", "none") != "none"
        if redaction_required and action == SecurityAction.ALLOW:
            action = SecurityAction.REDACT
            reasons.append(f"Redaction required: {policies['redaction_level']} level")

        return SecurityDecision(
            action=action,
            classification=classification,
            reasons=reasons,
            required_consents=required_consents,
            redaction_required=redaction_required,
        )

    async def _log_security_audit(
        self,
        db: Session,
        user_id: str,
        org_id: str,
        operation_type: str,
        decision: SecurityDecision,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log security decision to audit trail"""
        audit_log = AIAuditLog(
            organization_id=org_id,
            user_id=user_id,
            request_type=operation_type,
            decision_type="security_enforcement",
            decision_summary=json.dumps(
                {
                    "action": decision.action.value,
                    "classification": decision.classification.value,
                    "reasons": decision.reasons,
                    "redaction_required": decision.redaction_required,
                }
            ),
            metadata=metadata or {},
            created_at=datetime.utcnow(),
        )

        db.add(audit_log)
        db.commit()

        return audit_log.id

    async def _create_security_incident(
        self,
        db: Session,
        user_id: str,
        org_id: str,
        operation_type: str,
        decision: SecurityDecision,
        sensitivity_analysis: Dict[str, Any],
    ):
        """Create security incident for blocked or flagged operations"""
        severity = "high" if decision.action == SecurityAction.BLOCK else "medium"

        incident = SecurityIncident(
            incident_type=f"{operation_type}_blocked",
            severity=severity,
            description=f"{operation_type} blocked due to {decision.classification.value} data",
            user_id=user_id,
            organization_id=org_id,
            timestamp=datetime.utcnow(),
            details={
                "decision": {
                    "action": decision.action.value,
                    "reasons": decision.reasons,
                },
                "sensitivity": sensitivity_analysis.get("summary", ""),
                "categories": sensitivity_analysis.get("categories", {}),
            },
        )

        # Store incident (in production, this would go to a dedicated incident table)
        logger.warning(f"Security incident created: {incident}")

        # Notify security team
        await self._notify_security_team(incident)

    async def _notify_security_team(self, incident: SecurityIncident):
        """Notify security team of incidents"""
        # In production, this would send emails, Slack messages, etc.
        logger.info(f"Security team notified of incident: {incident.incident_type}")

    async def generate_compliance_report(
        self,
        db: Session,
        org_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get audit logs
        audit_logs = (
            db.query(AIAuditLog)
            .filter(
                AIAuditLog.organization_id == org_id,
                AIAuditLog.request_timestamp.between(start_date, end_date),
            )
            .all()
        )

        # Analyze security decisions
        total_requests = len(audit_logs)
        blocked_requests = sum(
            1
            for log in audit_logs
            if log.decision_summary
            and json.loads(log.decision_summary).get("action") == "block"
        )

        # Get consent compliance
        consent_manager = ConsentManager(db)
        consent_report = consent_manager.get_compliance_report(
            org_id, start_date, end_date
        )

        # Analyze data classifications
        classifications = {}
        for log in audit_logs:
            if log.decision_summary:
                decision = json.loads(log.decision_summary)
                classification = decision.get("classification", "unknown")
                classifications[classification] = (
                    classifications.get(classification, 0) + 1
                )

        # Get prompt review statistics
        prompt_reviews = (
            db.query(PromptLog)
            .filter(
                PromptLog.organization_id == org_id,
                PromptLog.created_at.between(start_date, end_date),
            )
            .all()
        )

        review_stats = {
            "total_prompts": len(prompt_reviews),
            "auto_approved": sum(1 for p in prompt_reviews if p.auto_approved),
            "manually_reviewed": sum(1 for p in prompt_reviews if p.reviewed_at),
            "rejected": sum(1 for p in prompt_reviews if p.status.value == "rejected"),
        }

        return {
            "organization_id": org_id,
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "security_summary": {
                "total_requests": total_requests,
                "blocked_requests": blocked_requests,
                "block_rate": (
                    (blocked_requests / total_requests * 100)
                    if total_requests > 0
                    else 0
                ),
                "data_classifications": classifications,
            },
            "consent_compliance": consent_report["summary"],
            "prompt_review_stats": review_stats,
            "compliance_score": self._calculate_compliance_score(
                consent_report, review_stats, blocked_requests, total_requests
            ),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _calculate_compliance_score(
        self,
        consent_report: Dict[str, Any],
        review_stats: Dict[str, Any],
        blocked_requests: int,
        total_requests: int,
    ) -> float:
        """Calculate overall compliance score (0-100)"""
        scores = []

        # Consent compliance score
        consent_rate = consent_report["summary"].get("consent_rate", 0)
        scores.append(consent_rate)

        # Review compliance score
        if review_stats["total_prompts"] > 0:
            review_rate = (
                (review_stats["auto_approved"] + review_stats["manually_reviewed"])
                / review_stats["total_prompts"]
                * 100
            )
            scores.append(review_rate)

        # Security compliance score
        if total_requests > 0:
            security_score = 100 - (blocked_requests / total_requests * 100)
            scores.append(security_score)

        # Average all scores
        return round(sum(scores) / len(scores) if scores else 0, 2)

    async def enforce_data_retention_policy(
        self, db: Session, org_id: str
    ) -> Dict[str, int]:
        """Enforce data retention policies"""
        org = db.query(Organization).filter(Organization.id == org_id).first()

        # Get retention period from consent preferences
        from models import ConsentPreference

        pref = (
            db.query(ConsentPreference)
            .filter(ConsentPreference.organization_id == org_id)
            .first()
        )

        retention_days = pref.data_retention_days if pref else 90
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Mark old data for deletion
        results = {"prompt_logs": 0, "audit_logs": 0, "documents": 0}

        # Anonymize old prompt logs
        old_prompts = (
            db.query(PromptLog)
            .filter(
                PromptLog.organization_id == org_id, PromptLog.created_at < cutoff_date
            )
            .all()
        )

        for prompt in old_prompts:
            prompt.original_prompt = "[REDACTED]"
            prompt.redacted_prompt = "[REDACTED]"
            prompt.final_prompt = "[REDACTED]"
            prompt.response_output = "[REDACTED]"
            results["prompt_logs"] += 1

        # Mark old audit logs
        old_audits = (
            db.query(AIAuditLog)
            .filter(
                AIAuditLog.organization_id == org_id,
                AIAuditLog.request_timestamp < cutoff_date,
                AIAuditLog.anonymized.is_(None),
            )
            .all()
        )

        for audit in old_audits:
            audit.anonymized = datetime.utcnow()
            results["audit_logs"] += 1

        db.commit()

        logger.info(f"Data retention policy enforced for org {org_id}: {results}")
        return results
