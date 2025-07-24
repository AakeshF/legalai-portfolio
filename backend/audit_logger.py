# audit_logger.py - Comprehensive audit logging for legal compliance
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

from database import Base
from models import User, Organization

logger = logging.getLogger(__name__)

class AuditEventType(str, Enum):
    """Types of audit events"""
    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGE = "auth.password.change"
    PASSWORD_RESET = "auth.password.reset"
    TOKEN_REFRESH = "auth.token.refresh"
    
    # Document events
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_VIEW = "document.view"
    DOCUMENT_DOWNLOAD = "document.download"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_REPROCESS = "document.reprocess"
    DOCUMENT_EXPORT = "document.export"
    
    # Chat events
    CHAT_MESSAGE = "chat.message"
    CHAT_SESSION_CREATE = "chat.session.create"
    CHAT_SESSION_DELETE = "chat.session.delete"
    CHAT_EXPORT = "chat.export"
    
    # Organization events
    ORG_CREATE = "organization.create"
    ORG_UPDATE = "organization.update"
    ORG_DELETE = "organization.delete"
    USER_INVITE = "organization.user.invite"
    USER_REMOVE = "organization.user.remove"
    USER_ROLE_CHANGE = "organization.user.role_change"
    
    # Data privacy events
    DATA_EXPORT_REQUEST = "privacy.data.export"
    DATA_DELETE_REQUEST = "privacy.data.delete"
    CONSENT_GIVEN = "privacy.consent.given"
    CONSENT_WITHDRAWN = "privacy.consent.withdrawn"
    
    # System events
    BACKUP_CREATED = "system.backup.created"
    BACKUP_RESTORED = "system.backup.restored"
    INTEGRATION_CONNECTED = "system.integration.connected"
    INTEGRATION_FAILED = "system.integration.failed"
    RATE_LIMIT_EXCEEDED = "system.rate_limit.exceeded"
    
    # Security events
    ACCESS_DENIED = "security.access.denied"
    SUSPICIOUS_ACTIVITY = "security.suspicious.activity"
    DATA_BREACH_ATTEMPT = "security.breach.attempt"

class AuditLog(Base):
    """Database model for audit logs"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Actor information
    user_id = Column(String, nullable=True, index=True)
    user_email = Column(String, nullable=True)
    organization_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Event details
    resource_type = Column(String, nullable=True, index=True)
    resource_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=True)
    result = Column(String, nullable=True)  # success, failure
    
    # Additional context
    details = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # For data integrity
    checksum = Column(String, nullable=False)  # SHA-256 hash of event data

@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_type: AuditEventType
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    organization_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    result: str = "success"
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        
        # Generate unique event ID
        self.event_id = f"{self.event_type}_{self.timestamp.isoformat()}_{hashlib.md5(f'{self.user_id}{self.resource_id}'.encode()).hexdigest()[:8]}"

class AuditLogger:
    """Centralized audit logging system"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._buffer: List[AuditEvent] = []
        self._buffer_size = 100  # Flush after 100 events
        
    def log_event(self, event: AuditEvent):
        """Log an audit event"""
        try:
            # Add to buffer for batch processing
            self._buffer.append(event)
            
            # Log to application logger for immediate visibility
            logger.info(
                f"AUDIT: {event.event_type} - User: {event.user_email or event.user_id} - "
                f"Resource: {event.resource_type}/{event.resource_id} - Result: {event.result}",
                extra=asdict(event)
            )
            
            # Flush buffer if it's full
            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def _flush_buffer(self):
        """Flush buffered events to database"""
        if not self._buffer:
            return
            
        db = self.db_session_factory()
        try:
            for event in self._buffer:
                # Calculate checksum for integrity
                event_data = json.dumps(asdict(event), sort_keys=True, default=str)
                checksum = hashlib.sha256(event_data.encode()).hexdigest()
                
                # Create database record
                audit_log = AuditLog(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    user_id=event.user_id,
                    user_email=event.user_email,
                    organization_id=event.organization_id,
                    ip_address=event.ip_address,
                    user_agent=event.user_agent,
                    resource_type=event.resource_type,
                    resource_id=event.resource_id,
                    action=event.action,
                    result=event.result,
                    details=event.details,
                    error_message=event.error_message,
                    checksum=checksum
                )
                
                db.add(audit_log)
            
            db.commit()
            self._buffer.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush audit buffer to database: {e}")
            db.rollback()
        finally:
            db.close()
    
    def log_login(self, user: User, ip_address: str, user_agent: str, success: bool, error: Optional[str] = None):
        """Log login attempt"""
        self.log_event(AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE,
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            organization_id=user.organization_id if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            result="success" if success else "failure",
            error_message=error
        ))
    
    def log_document_access(self, user: User, document_id: str, action: str, ip_address: str):
        """Log document access"""
        event_type_map = {
            "upload": AuditEventType.DOCUMENT_UPLOAD,
            "view": AuditEventType.DOCUMENT_VIEW,
            "download": AuditEventType.DOCUMENT_DOWNLOAD,
            "delete": AuditEventType.DOCUMENT_DELETE,
            "reprocess": AuditEventType.DOCUMENT_REPROCESS,
            "export": AuditEventType.DOCUMENT_EXPORT
        }
        
        self.log_event(AuditEvent(
            event_type=event_type_map.get(action, AuditEventType.DOCUMENT_VIEW),
            user_id=user.id,
            user_email=user.email,
            organization_id=user.organization_id,
            ip_address=ip_address,
            resource_type="document",
            resource_id=document_id,
            action=action
        ))
    
    def log_data_export(self, user: User, export_type: str, resource_count: int, ip_address: str):
        """Log data export request"""
        self.log_event(AuditEvent(
            event_type=AuditEventType.DATA_EXPORT_REQUEST,
            user_id=user.id,
            user_email=user.email,
            organization_id=user.organization_id,
            ip_address=ip_address,
            action="export",
            details={
                "export_type": export_type,
                "resource_count": resource_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        ))
    
    def log_security_event(self, event_type: str, user_id: Optional[str], details: Dict[str, Any], ip_address: str):
        """Log security-related events"""
        self.log_event(AuditEvent(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            ip_address=ip_address,
            result="detected",
            details=details
        ))
    
    async def get_audit_trail(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Retrieve audit trail with filters"""
        db = self.db_session_factory()
        try:
            query = db.query(AuditLog).filter(
                AuditLog.organization_id == organization_id
            )
            
            if start_date:
                query = query.filter(AuditLog.timestamp >= start_date)
            
            if end_date:
                query = query.filter(AuditLog.timestamp <= end_date)
            
            if event_types:
                query = query.filter(AuditLog.event_type.in_(event_types))
            
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            
            # Order by timestamp descending
            query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
            
            results = []
            for log in query.all():
                # Verify checksum
                log_dict = {
                    "event_id": log.event_id,
                    "event_type": log.event_type,
                    "timestamp": log.timestamp,
                    "user_id": log.user_id,
                    "user_email": log.user_email,
                    "organization_id": log.organization_id,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "action": log.action,
                    "result": log.result,
                    "details": log.details,
                    "error_message": log.error_message
                }
                
                # Calculate expected checksum
                event_data = json.dumps(log_dict, sort_keys=True, default=str)
                expected_checksum = hashlib.sha256(event_data.encode()).hexdigest()
                
                # Add integrity check
                log_dict["integrity_verified"] = expected_checksum == log.checksum
                
                results.append(log_dict)
            
            return results
            
        finally:
            db.close()
    
    def generate_compliance_report(
        self,
        organization_id: str,
        report_type: str = "gdpr",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate compliance report from audit logs"""
        db = self.db_session_factory()
        try:
            # Get relevant events for compliance
            privacy_events = [
                AuditEventType.DATA_EXPORT_REQUEST,
                AuditEventType.DATA_DELETE_REQUEST,
                AuditEventType.CONSENT_GIVEN,
                AuditEventType.CONSENT_WITHDRAWN
            ]
            
            query = db.query(AuditLog).filter(
                AuditLog.organization_id == organization_id,
                AuditLog.event_type.in_(privacy_events)
            )
            
            if start_date:
                query = query.filter(AuditLog.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditLog.timestamp <= end_date)
            
            events = query.all()
            
            # Generate report
            report = {
                "organization_id": organization_id,
                "report_type": report_type,
                "generated_at": datetime.utcnow().isoformat(),
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "summary": {
                    "total_privacy_events": len(events),
                    "data_export_requests": sum(1 for e in events if e.event_type == AuditEventType.DATA_EXPORT_REQUEST),
                    "data_deletion_requests": sum(1 for e in events if e.event_type == AuditEventType.DATA_DELETE_REQUEST),
                    "consent_given": sum(1 for e in events if e.event_type == AuditEventType.CONSENT_GIVEN),
                    "consent_withdrawn": sum(1 for e in events if e.event_type == AuditEventType.CONSENT_WITHDRAWN)
                },
                "events": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "type": e.event_type,
                        "user": e.user_email,
                        "details": e.details
                    }
                    for e in events
                ]
            }
            
            return report
            
        finally:
            db.close()