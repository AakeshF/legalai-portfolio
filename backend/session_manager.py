# session_manager.py - Secure session management for enterprise legal compliance
import secrets
import json
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import hmac
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
try:
    import redis
except ImportError:
    redis = None  # Redis is optional
import logging

from database import Base
from models import User
from encryption import get_encryption_service

logger = logging.getLogger(__name__)

@dataclass
class SessionConfig:
    """Configuration for secure sessions"""
    max_idle_time: int = 900  # 15 minutes
    absolute_timeout: int = 28800  # 8 hours
    max_concurrent_sessions: int = 3
    require_ip_match: bool = True
    require_user_agent_match: bool = True
    enable_activity_tracking: bool = True
    secure_cookie_only: bool = True
    enable_session_recording: bool = True  # For compliance

class SecureSession(Base):
    """Database model for secure session storage"""
    __tablename__ = "secure_sessions"
    
    id = Column(String, primary_key=True)
    session_token_hash = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(String, nullable=False, index=True)
    
    # Session metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    # Security context
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=False)
    device_fingerprint = Column(String, nullable=True)
    
    # Session state
    is_active = Column(Boolean, default=True)
    terminated_reason = Column(String, nullable=True)
    
    # Activity tracking
    activity_count = Column(Integer, default=0)
    last_endpoint = Column(String, nullable=True)
    
    # Compliance data
    session_recording = Column(JSON, nullable=True)  # Encrypted session activity

class SessionActivity(Base):
    """Track detailed session activity for security monitoring"""
    __tablename__ = "session_activities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=True)
    ip_address = Column(String, nullable=False)
    risk_score = Column(Integer, default=0)  # 0-100
    
    # Additional context
    details = Column(JSON, nullable=True)

class SecureSessionManager:
    """
    Enterprise-grade session management with security features:
    - Automatic session timeout
    - Device fingerprinting
    - Activity monitoring
    - Concurrent session limits
    - Session recording for compliance
    """
    
    def __init__(self, db_session_factory, config: SessionConfig = None, redis_client: Optional[Any] = None):
        self.db_session_factory = db_session_factory
        self.config = config or SessionConfig()
        self.redis_client = redis_client  # Optional Redis for session caching
        self.encryption_service = get_encryption_service()
        
    def create_session(
        self,
        user: User,
        ip_address: str,
        user_agent: str,
        device_fingerprint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new secure session
        
        Returns:
            Session data including secure token
        """
        db = self.db_session_factory()
        
        try:
            # Check concurrent session limit
            active_sessions = db.query(SecureSession).filter(
                SecureSession.user_id == user.id,
                SecureSession.is_active == True,
                SecureSession.expires_at > datetime.utcnow()
            ).count()
            
            if active_sessions >= self.config.max_concurrent_sessions:
                # Terminate oldest session
                oldest_session = db.query(SecureSession).filter(
                    SecureSession.user_id == user.id,
                    SecureSession.is_active == True
                ).order_by(SecureSession.created_at.asc()).first()
                
                if oldest_session:
                    self._terminate_session(db, oldest_session, "max_sessions_exceeded")
            
            # Generate secure session token
            session_token = self._generate_session_token()
            session_id = str(uuid.uuid4())
            
            # Hash token for storage
            token_hash = self._hash_token(session_token)
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(seconds=self.config.absolute_timeout)
            
            # Create session record
            session = SecureSession(
                id=session_id,
                session_token_hash=token_hash,
                user_id=user.id,
                organization_id=user.organization_id,
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                is_active=True,
                activity_count=0,
                session_recording=[]
            )
            
            db.add(session)
            db.commit()
            
            # Cache session in Redis if available
            if self.redis_client:
                self._cache_session(session_id, {
                    "user_id": user.id,
                    "organization_id": user.organization_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                }, self.config.absolute_timeout)
            
            logger.info(f"Session created", extra={
                "session_id": session_id,
                "user_id": user.id,
                "ip_address": ip_address
            })
            
            return {
                "session_token": session_token,
                "session_id": session_id,
                "expires_at": expires_at.isoformat(),
                "max_idle_time": self.config.max_idle_time
            }
            
        finally:
            db.close()
    
    def validate_session(
        self,
        session_token: str,
        ip_address: str,
        user_agent: str
    ) -> Optional[Dict[str, Any]]:
        """
        Validate session and update activity
        
        Returns:
            Session data if valid, None otherwise
        """
        # Hash the token
        token_hash = self._hash_token(session_token)
        
        # Try Redis cache first
        if self.redis_client:
            cached = self._get_cached_session(token_hash)
            if cached:
                # Validate cached session
                if self._validate_session_context(cached, ip_address, user_agent):
                    return cached
        
        db = self.db_session_factory()
        
        try:
            # Find session by token hash
            session = db.query(SecureSession).filter(
                SecureSession.session_token_hash == token_hash,
                SecureSession.is_active == True
            ).first()
            
            if not session:
                return None
            
            # Check expiration
            if datetime.utcnow() > session.expires_at:
                self._terminate_session(db, session, "expired")
                return None
            
            # Check idle timeout
            idle_time = (datetime.utcnow() - session.last_activity).total_seconds()
            if idle_time > self.config.max_idle_time:
                self._terminate_session(db, session, "idle_timeout")
                return None
            
            # Validate security context
            if self.config.require_ip_match and session.ip_address != ip_address:
                logger.warning(f"IP mismatch for session", extra={
                    "session_id": session.id,
                    "expected_ip": session.ip_address,
                    "actual_ip": ip_address
                })
                self._terminate_session(db, session, "ip_mismatch")
                return None
            
            if self.config.require_user_agent_match and session.user_agent != user_agent:
                logger.warning(f"User agent mismatch for session", extra={
                    "session_id": session.id
                })
                self._terminate_session(db, session, "user_agent_mismatch")
                return None
            
            # Update activity
            session.last_activity = datetime.utcnow()
            session.activity_count += 1
            db.commit()
            
            # Return session data
            session_data = {
                "session_id": session.id,
                "user_id": session.user_id,
                "organization_id": session.organization_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "activity_count": session.activity_count
            }
            
            # Update cache
            if self.redis_client:
                self._cache_session(session.id, session_data, self.config.max_idle_time)
            
            return session_data
            
        finally:
            db.close()
    
    def record_activity(
        self,
        session_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        ip_address: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Record session activity for monitoring and compliance"""
        if not self.config.enable_activity_tracking:
            return
        
        db = self.db_session_factory()
        
        try:
            # Calculate risk score based on activity
            risk_score = self._calculate_activity_risk(endpoint, method, status_code, details)
            
            # Record activity
            activity = SessionActivity(
                session_id=session_id,
                timestamp=datetime.utcnow(),
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                ip_address=ip_address,
                risk_score=risk_score,
                details=details
            )
            
            db.add(activity)
            
            # Update session recording if enabled
            if self.config.enable_session_recording:
                session = db.query(SecureSession).filter(
                    SecureSession.id == session_id
                ).first()
                
                if session:
                    # Append to encrypted session recording
                    recording = session.session_recording or []
                    recording.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "endpoint": endpoint,
                        "method": method,
                        "status": status_code,
                        "risk": risk_score
                    })
                    
                    # Keep only last 100 activities
                    if len(recording) > 100:
                        recording = recording[-100:]
                    
                    session.session_recording = recording
                    session.last_endpoint = endpoint
            
            db.commit()
            
            # Check for suspicious activity
            if risk_score > 70:
                logger.warning(f"High risk activity detected", extra={
                    "session_id": session_id,
                    "endpoint": endpoint,
                    "risk_score": risk_score,
                    "details": details
                })
            
        finally:
            db.close()
    
    def terminate_session(self, session_id: str, reason: str = "user_logout"):
        """Terminate a session"""
        db = self.db_session_factory()
        
        try:
            session = db.query(SecureSession).filter(
                SecureSession.id == session_id
            ).first()
            
            if session:
                self._terminate_session(db, session, reason)
                
                # Clear cache
                if self.redis_client:
                    self._clear_cached_session(session.session_token_hash)
                
                logger.info(f"Session terminated", extra={
                    "session_id": session_id,
                    "reason": reason
                })
            
        finally:
            db.close()
    
    def terminate_user_sessions(self, user_id: str, reason: str = "security"):
        """Terminate all sessions for a user"""
        db = self.db_session_factory()
        
        try:
            sessions = db.query(SecureSession).filter(
                SecureSession.user_id == user_id,
                SecureSession.is_active == True
            ).all()
            
            for session in sessions:
                self._terminate_session(db, session, reason)
            
            logger.info(f"All sessions terminated for user", extra={
                "user_id": user_id,
                "count": len(sessions),
                "reason": reason
            })
            
        finally:
            db.close()
    
    def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        db = self.db_session_factory()
        
        try:
            sessions = db.query(SecureSession).filter(
                SecureSession.user_id == user_id,
                SecureSession.is_active == True,
                SecureSession.expires_at > datetime.utcnow()
            ).all()
            
            return [
                {
                    "session_id": s.id,
                    "created_at": s.created_at.isoformat(),
                    "last_activity": s.last_activity.isoformat(),
                    "ip_address": s.ip_address,
                    "user_agent": s.user_agent,
                    "activity_count": s.activity_count,
                    "expires_at": s.expires_at.isoformat()
                }
                for s in sessions
            ]
            
        finally:
            db.close()
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions (run periodically)"""
        db = self.db_session_factory()
        
        try:
            # Find expired sessions
            expired = db.query(SecureSession).filter(
                SecureSession.expires_at < datetime.utcnow(),
                SecureSession.is_active == True
            ).all()
            
            for session in expired:
                session.is_active = False
                session.terminated_reason = "expired"
            
            # Clean up old session activities (keep 30 days)
            cutoff = datetime.utcnow() - timedelta(days=30)
            db.query(SessionActivity).filter(
                SessionActivity.timestamp < cutoff
            ).delete()
            
            db.commit()
            
            logger.info(f"Cleaned up {len(expired)} expired sessions")
            
        finally:
            db.close()
    
    # Private methods
    def _generate_session_token(self) -> str:
        """Generate cryptographically secure session token"""
        return secrets.token_urlsafe(64)
    
    def _hash_token(self, token: str) -> str:
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _terminate_session(self, db: Session, session: SecureSession, reason: str):
        """Mark session as terminated"""
        session.is_active = False
        session.terminated_reason = reason
        db.commit()
    
    def _calculate_activity_risk(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        details: Optional[Dict[str, Any]]
    ) -> int:
        """Calculate risk score for activity (0-100)"""
        risk_score = 0
        
        # Failed requests
        if status_code >= 400:
            risk_score += 20
        
        # Sensitive endpoints
        sensitive_endpoints = [
            "/api/documents/export",
            "/api/organization/users",
            "/api/auth/password",
            "/api/admin"
        ]
        
        if any(endpoint.startswith(ep) for ep in sensitive_endpoints):
            risk_score += 30
        
        # Dangerous methods
        if method in ["DELETE", "PUT"]:
            risk_score += 10
        
        # Multiple failed attempts
        if details and details.get("failed_attempts", 0) > 3:
            risk_score += 40
        
        return min(risk_score, 100)
    
    def _cache_session(self, session_id: str, data: Dict[str, Any], ttl: int):
        """Cache session in Redis"""
        if self.redis_client:
            self.redis_client.setex(
                f"session:{session_id}",
                ttl,
                json.dumps(data)
            )
    
    def _get_cached_session(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Get session from Redis cache"""
        if self.redis_client:
            data = self.redis_client.get(f"session:{token_hash}")
            if data:
                return json.loads(data)
        return None
    
    def _clear_cached_session(self, token_hash: str):
        """Clear session from cache"""
        if self.redis_client:
            self.redis_client.delete(f"session:{token_hash}")
    
    def _validate_session_context(
        self,
        session_data: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ) -> bool:
        """Validate session security context"""
        if self.config.require_ip_match:
            if session_data.get("ip_address") != ip_address:
                return False
        
        if self.config.require_user_agent_match:
            if session_data.get("user_agent") != user_agent:
                return False
        
        return True

import uuid  # Add at top