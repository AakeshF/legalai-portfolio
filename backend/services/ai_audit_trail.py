# services/ai_audit_trail.py - AI decision audit trail system
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Integer, Text, Float, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class AIAuditLog(Base):
    """Database model for AI decision audit logs"""

    __tablename__ = "ai_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Request details
    request_id = Column(String(36), unique=True, index=True)
    request_type = Column(String(50))  # chat, analysis, comparison, etc.
    request_timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # AI provider details
    provider_used = Column(String(50), nullable=False)
    model_used = Column(String(100))
    provider_fallback = Column(String(200))  # JSON array of attempted providers

    # Input data
    input_hash = Column(String(64))  # SHA-256 hash of input for privacy
    input_size = Column(Integer)  # Size in characters
    document_ids = Column(Text)  # JSON array of document IDs

    # Output data
    output_hash = Column(String(64))  # SHA-256 hash of output
    output_size = Column(Integer)
    response_time_ms = Column(Integer)

    # Consent tracking
    consent_id = Column(Integer, ForeignKey("consent_records.id"))
    consent_verified = Column(String(20))  # granted, denied, default

    # Cost and usage
    tokens_used = Column(Integer)
    estimated_cost = Column(Float)

    # Decision details
    decision_type = Column(String(100))  # risk_assessment, party_extraction, etc.
    decision_summary = Column(Text)  # Brief summary of AI decision
    confidence_score = Column(Float)

    # Data location
    processing_location = Column(String(50))  # cloud, local, hybrid
    data_residency = Column(String(50))  # Country/region code

    # Compliance metadata
    retention_expires = Column(DateTime)
    anonymized = Column(DateTime)
    deleted = Column(DateTime)

    # Create indexes for common queries
    __table_args__ = (
        Index("idx_org_timestamp", "organization_id", "request_timestamp"),
        Index("idx_user_timestamp", "user_id", "request_timestamp"),
        Index("idx_provider_timestamp", "provider_used", "request_timestamp"),
    )


class AIDecisionDetail(Base):
    """Detailed AI decisions for comprehensive audit"""

    __tablename__ = "ai_decision_details"

    id = Column(Integer, primary_key=True, index=True)
    audit_log_id = Column(Integer, ForeignKey("ai_audit_logs.id"), nullable=False)

    # Decision components
    decision_category = Column(String(50))  # legal_risk, compliance, extraction
    decision_item = Column(String(200))  # Specific item decided
    decision_value = Column(Text)  # The actual decision/extraction
    confidence = Column(Float)

    # Supporting evidence
    evidence_type = Column(String(50))  # document_section, pattern_match, etc.
    evidence_reference = Column(Text)  # Reference to source

    created_at = Column(DateTime, default=datetime.utcnow)


class AIAuditTrail:
    """Manage AI decision audit trails for compliance and transparency"""

    def __init__(self, db: Session):
        self.db = db
        self.retention_days = 365  # Default retention period
        logger.info("AI Audit Trail system initialized")

    def log_ai_request(
        self,
        organization_id: int,
        user_id: int,
        request_type: str,
        provider: str,
        model: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """Log an AI request and response"""

        import uuid

        request_id = str(uuid.uuid4())

        # Hash sensitive data
        input_hash = self._hash_data(json.dumps(input_data))
        output_hash = self._hash_data(json.dumps(output_data))

        # Extract document IDs if present
        document_ids = metadata.get("document_ids", [])
        if not isinstance(document_ids, list):
            document_ids = [document_ids] if document_ids else []

        # Create audit log
        audit_log = AIAuditLog(
            organization_id=organization_id,
            user_id=user_id,
            request_id=request_id,
            request_type=request_type,
            provider_used=provider,
            model_used=model,
            provider_fallback=json.dumps(metadata.get("fallback_providers", [])),
            input_hash=input_hash,
            input_size=len(json.dumps(input_data)),
            document_ids=json.dumps(document_ids),
            output_hash=output_hash,
            output_size=len(json.dumps(output_data)),
            response_time_ms=metadata.get("response_time_ms", 0),
            consent_id=metadata.get("consent_id"),
            consent_verified=metadata.get("consent_status", "unknown"),
            tokens_used=metadata.get("tokens_used", 0),
            estimated_cost=self._estimate_cost(
                provider, metadata.get("tokens_used", 0)
            ),
            decision_type=metadata.get("decision_type"),
            decision_summary=self._generate_summary(output_data),
            confidence_score=metadata.get("confidence_score"),
            processing_location=metadata.get("processing_location", "cloud"),
            data_residency=metadata.get("data_residency", "us"),
            retention_expires=datetime.utcnow() + timedelta(days=self.retention_days),
        )

        self.db.add(audit_log)
        self.db.flush()  # Get the ID

        # Log detailed decisions if provided
        if "decisions" in metadata:
            self._log_decision_details(audit_log.id, metadata["decisions"])

        self.db.commit()

        logger.info(
            f"AI request logged: id={request_id}, org={organization_id}, "
            f"provider={provider}, type={request_type}"
        )

        return request_id

    def _hash_data(self, data: str) -> str:
        """Create SHA-256 hash of data for privacy"""
        return hashlib.sha256(data.encode()).hexdigest()

    def _estimate_cost(self, provider: str, tokens: int) -> float:
        """Estimate cost based on provider and token usage"""
        # Approximate costs per 1M tokens (input + output average)
        cost_per_million = {
            "openai": 10.0,  # GPT-4 Turbo
            "claude": 15.0,  # Claude 3.5 Sonnet
            "gemini": 3.5,  # Gemini 1.5 Pro
            "local": 0.0,
        }

        rate = cost_per_million.get(provider, 1.0)
        return (tokens / 1_000_000) * rate

    def _generate_summary(self, output_data: Dict[str, Any]) -> str:
        """Generate a summary of the AI decision"""
        summary_parts = []

        # Extract key information from output
        if "risk_assessment" in output_data:
            risk = output_data["risk_assessment"]
            summary_parts.append(f"Risk: {risk.get('level', 'unknown')}")

        if "structured_data" in output_data:
            data = output_data["structured_data"]
            if "action_items" in data and data["action_items"]:
                summary_parts.append(f"Actions: {len(data['action_items'])}")
            if "key_findings" in data and data["key_findings"]:
                summary_parts.append(f"Findings: {len(data['key_findings'])}")

        if "extracted_entities" in output_data:
            entities = output_data["extracted_entities"]
            entity_counts = []
            for entity_type, values in entities.items():
                if values and isinstance(values, list):
                    entity_counts.append(f"{entity_type}: {len(values)}")
            if entity_counts:
                summary_parts.append("Extracted " + ", ".join(entity_counts))

        return "; ".join(summary_parts) if summary_parts else "General AI response"

    def _log_decision_details(self, audit_log_id: int, decisions: List[Dict[str, Any]]):
        """Log detailed decision information"""
        for decision in decisions:
            detail = AIDecisionDetail(
                audit_log_id=audit_log_id,
                decision_category=decision.get("category"),
                decision_item=decision.get("item"),
                decision_value=json.dumps(decision.get("value")),
                confidence=decision.get("confidence"),
                evidence_type=decision.get("evidence_type"),
                evidence_reference=decision.get("evidence_reference"),
            )
            self.db.add(detail)

    def get_audit_log(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific audit log by request ID"""

        log = self.db.query(AIAuditLog).filter_by(request_id=request_id).first()
        if not log:
            return None

        # Get decision details
        details = self.db.query(AIDecisionDetail).filter_by(audit_log_id=log.id).all()

        return {
            "request_id": log.request_id,
            "organization_id": log.organization_id,
            "user_id": log.user_id,
            "timestamp": log.request_timestamp.isoformat(),
            "request_type": log.request_type,
            "provider": log.provider_used,
            "model": log.model_used,
            "response_time_ms": log.response_time_ms,
            "tokens_used": log.tokens_used,
            "estimated_cost": log.estimated_cost,
            "decision_summary": log.decision_summary,
            "confidence_score": log.confidence_score,
            "consent_verified": log.consent_verified,
            "processing_location": log.processing_location,
            "decision_details": [
                {
                    "category": d.decision_category,
                    "item": d.decision_item,
                    "value": json.loads(d.decision_value) if d.decision_value else None,
                    "confidence": d.confidence,
                }
                for d in details
            ],
        }

    def search_audit_logs(
        self,
        organization_id: Optional[int] = None,
        user_id: Optional[int] = None,
        provider: Optional[str] = None,
        request_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search audit logs with filters"""

        query = self.db.query(AIAuditLog)

        if organization_id:
            query = query.filter(AIAuditLog.organization_id == organization_id)
        if user_id:
            query = query.filter(AIAuditLog.user_id == user_id)
        if provider:
            query = query.filter(AIAuditLog.provider_used == provider)
        if request_type:
            query = query.filter(AIAuditLog.request_type == request_type)
        if start_date:
            query = query.filter(AIAuditLog.request_timestamp >= start_date)
        if end_date:
            query = query.filter(AIAuditLog.request_timestamp <= end_date)

        # Exclude deleted records
        query = query.filter(AIAuditLog.deleted.is_(None))

        logs = query.order_by(AIAuditLog.request_timestamp.desc()).limit(limit).all()

        return [
            {
                "request_id": log.request_id,
                "timestamp": log.request_timestamp.isoformat(),
                "request_type": log.request_type,
                "provider": log.provider_used,
                "model": log.model_used,
                "response_time_ms": log.response_time_ms,
                "tokens_used": log.tokens_used,
                "estimated_cost": log.estimated_cost,
                "decision_summary": log.decision_summary,
                "consent_verified": log.consent_verified,
            }
            for log in logs
        ]

    def get_usage_analytics(
        self,
        organization_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get AI usage analytics for an organization"""

        query = self.db.query(AIAuditLog).filter(
            AIAuditLog.organization_id == organization_id, AIAuditLog.deleted.is_(None)
        )

        if start_date:
            query = query.filter(AIAuditLog.request_timestamp >= start_date)
        if end_date:
            query = query.filter(AIAuditLog.request_timestamp <= end_date)

        logs = query.all()

        # Calculate analytics
        total_requests = len(logs)
        total_tokens = sum(log.tokens_used or 0 for log in logs)
        total_cost = sum(log.estimated_cost or 0 for log in logs)

        # Group by provider
        by_provider = {}
        for log in logs:
            provider = log.provider_used
            if provider not in by_provider:
                by_provider[provider] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0,
                    "avg_response_time": 0,
                }
            by_provider[provider]["requests"] += 1
            by_provider[provider]["tokens"] += log.tokens_used or 0
            by_provider[provider]["cost"] += log.estimated_cost or 0

        # Calculate average response times
        for provider, stats in by_provider.items():
            provider_logs = [log for log in logs if log.provider_used == provider]
            if provider_logs:
                avg_time = sum(
                    log.response_time_ms or 0 for log in provider_logs
                ) / len(provider_logs)
                stats["avg_response_time"] = round(avg_time)

        # Group by request type
        by_type = {}
        for log in logs:
            req_type = log.request_type or "unknown"
            if req_type not in by_type:
                by_type[req_type] = 0
            by_type[req_type] += 1

        return {
            "organization_id": organization_id,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "summary": {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 2),
                "avg_tokens_per_request": (
                    round(total_tokens / total_requests) if total_requests > 0 else 0
                ),
            },
            "by_provider": by_provider,
            "by_request_type": by_type,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def export_audit_logs(
        self,
        organization_id: int,
        format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """Export audit logs for compliance reporting"""

        logs = self.search_audit_logs(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Higher limit for exports
        )

        if format == "json":
            return json.dumps(
                {
                    "export_date": datetime.utcnow().isoformat(),
                    "organization_id": organization_id,
                    "record_count": len(logs),
                    "logs": logs,
                },
                indent=2,
            )

        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)

            return output.getvalue()

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def apply_retention_policy(self, dry_run: bool = True) -> Dict[str, int]:
        """Apply data retention policy to audit logs"""

        # Find logs past retention period
        cutoff_date = datetime.utcnow()

        expired_logs = (
            self.db.query(AIAuditLog)
            .filter(
                AIAuditLog.retention_expires <= cutoff_date,
                AIAuditLog.deleted.is_(None),
            )
            .all()
        )

        anonymized_count = 0
        deleted_count = 0

        for log in expired_logs:
            if not dry_run:
                # Anonymize sensitive data
                log.input_hash = "ANONYMIZED"
                log.output_hash = "ANONYMIZED"
                log.decision_summary = "ANONYMIZED"
                log.anonymized = datetime.utcnow()

                # Delete after additional period (e.g., 90 days after anonymization)
                if log.anonymized and (datetime.utcnow() - log.anonymized).days > 90:
                    log.deleted = datetime.utcnow()
                    deleted_count += 1
                else:
                    anonymized_count += 1

        if not dry_run:
            self.db.commit()

        return {
            "expired_logs": len(expired_logs),
            "anonymized": anonymized_count,
            "deleted": deleted_count,
            "dry_run": dry_run,
        }
