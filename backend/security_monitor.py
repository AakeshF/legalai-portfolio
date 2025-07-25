# security_monitor.py - Real-time security monitoring and threat detection
import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import re
import json
import logging
from enum import Enum

from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, Text
from sqlalchemy.orm import Session
from database import Base
from audit_logger import AuditLogger, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Types of security threats"""

    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL = "path_traversal"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    MALWARE_UPLOAD = "malware_upload"
    SESSION_HIJACKING = "session_hijacking"


@dataclass
class SecurityIncident:
    """Security incident data"""

    incident_id: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    timestamp: datetime
    user_id: Optional[str]
    ip_address: str
    description: str
    details: Dict[str, Any]
    indicators: List[str]
    mitigated: bool = False
    false_positive: bool = False


@dataclass
class UserBehaviorProfile:
    """User behavior profile for anomaly detection"""

    user_id: str
    typical_login_times: List[int] = field(default_factory=list)  # Hours of day
    typical_ip_addresses: Set[str] = field(default_factory=set)
    typical_user_agents: Set[str] = field(default_factory=set)
    typical_endpoints: Set[str] = field(default_factory=set)
    average_requests_per_hour: float = 0.0
    document_access_pattern: Dict[str, int] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)


class SecurityIncidentDB(Base):
    """Database model for security incidents"""

    __tablename__ = "security_incidents"

    incident_id = Column(String, primary_key=True)
    threat_type = Column(String, nullable=False)
    threat_level = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Actor information
    user_id = Column(String, nullable=True)
    organization_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)

    # Incident details
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    indicators = Column(JSON, nullable=True)

    # Response
    mitigated = Column(Boolean, default=False)
    mitigation_actions = Column(JSON, nullable=True)
    false_positive = Column(Boolean, default=False)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)


class SecurityMonitor:
    """
    Real-time security monitoring and threat detection system
    Implements behavioral analysis and threat intelligence
    """

    def __init__(self, db_session_factory, audit_logger: AuditLogger):
        self.db_session_factory = db_session_factory
        self.audit_logger = audit_logger

        # In-memory tracking
        self.failed_login_attempts: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self.request_patterns: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self.user_behaviors: Dict[str, UserBehaviorProfile] = {}
        self.active_incidents: Dict[str, SecurityIncident] = {}

        # Threat detection patterns
        self.sql_injection_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(from|where|table)\b)",
            r"(;|--|\/\*|\*\/|xp_|sp_|exec|execute)",
            r"(\b(and|or)\b\s*['\"]*\s*\d+\s*=\s*\d+)",
        ]

        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<(iframe|object|embed|svg|img)[^>]*>",
        ]

        self.path_traversal_patterns = [r"\.\./", r"\.\.\\", r"%2e%2e/", r"%252e%252e/"]

        # Monitoring task
        self._monitoring_task = None

    async def start_monitoring(self):
        """Start the security monitoring background task"""
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Security monitoring started")

    async def stop_monitoring(self):
        """Stop security monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Security monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                # Run periodic security checks
                await self._check_active_threats()
                await self._analyze_user_behaviors()
                await self._detect_anomalies()

                # Wait before next check
                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Security monitoring error: {e}")
                await asyncio.sleep(60)

    def record_login_attempt(
        self, user_email: str, ip_address: str, success: bool, user_agent: str
    ):
        """Record login attempt for threat detection"""
        key = f"{user_email}:{ip_address}"
        self.failed_login_attempts[key].append(
            {
                "timestamp": datetime.utcnow(),
                "success": success,
                "user_agent": user_agent,
            }
        )

        if not success:
            # Check for brute force
            recent_failures = [
                a
                for a in self.failed_login_attempts[key]
                if not a["success"]
                and datetime.utcnow() - a["timestamp"] < timedelta(minutes=15)
            ]

            if len(recent_failures) >= 5:
                self._create_incident(
                    threat_type=ThreatType.BRUTE_FORCE,
                    threat_level=ThreatLevel.HIGH,
                    ip_address=ip_address,
                    description=f"Multiple failed login attempts for {user_email}",
                    details={
                        "email": user_email,
                        "failed_attempts": len(recent_failures),
                        "time_window": "15 minutes",
                    },
                    indicators=["multiple_failed_logins", "rapid_attempts"],
                )

    def analyze_request(
        self,
        request_path: str,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        ip_address: str,
        user_id: Optional[str] = None,
    ) -> List[SecurityIncident]:
        """Analyze HTTP request for security threats"""
        incidents = []

        # Check for SQL injection
        sql_threats = self._detect_sql_injection(request_path, params, headers)
        if sql_threats:
            incident = self._create_incident(
                threat_type=ThreatType.SQL_INJECTION,
                threat_level=ThreatLevel.CRITICAL,
                ip_address=ip_address,
                user_id=user_id,
                description="SQL injection attempt detected",
                details={
                    "path": request_path,
                    "method": method,
                    "patterns": sql_threats,
                },
                indicators=["sql_keywords", "injection_syntax"],
            )
            incidents.append(incident)

        # Check for XSS
        xss_threats = self._detect_xss(params, headers)
        if xss_threats:
            incident = self._create_incident(
                threat_type=ThreatType.XSS_ATTEMPT,
                threat_level=ThreatLevel.HIGH,
                ip_address=ip_address,
                user_id=user_id,
                description="Cross-site scripting attempt detected",
                details={"path": request_path, "patterns": xss_threats},
                indicators=["script_tags", "javascript_code"],
            )
            incidents.append(incident)

        # Check for path traversal
        if self._detect_path_traversal(request_path, params):
            incident = self._create_incident(
                threat_type=ThreatType.PATH_TRAVERSAL,
                threat_level=ThreatLevel.HIGH,
                ip_address=ip_address,
                user_id=user_id,
                description="Path traversal attempt detected",
                details={"path": request_path, "method": method},
                indicators=["directory_traversal", "file_access_attempt"],
            )
            incidents.append(incident)

        # Track request patterns
        if user_id:
            self._track_user_request(user_id, request_path, ip_address)

        return incidents

    def detect_data_exfiltration(
        self,
        user_id: str,
        action: str,
        resource_count: int,
        time_window: int = 3600,  # 1 hour
    ) -> Optional[SecurityIncident]:
        """Detect potential data exfiltration"""
        # Get user's recent activity
        user_actions = self.request_patterns.get(user_id, deque())

        recent_downloads = [
            a
            for a in user_actions
            if a.get("action") in ["download", "export"]
            and datetime.utcnow() - a["timestamp"] < timedelta(seconds=time_window)
        ]

        # Calculate download rate
        if len(recent_downloads) > 50 or resource_count > 100:
            return self._create_incident(
                threat_type=ThreatType.DATA_EXFILTRATION,
                threat_level=ThreatLevel.CRITICAL,
                user_id=user_id,
                ip_address=recent_downloads[-1].get("ip_address", "unknown"),
                description="Potential data exfiltration detected",
                details={
                    "action": action,
                    "resource_count": resource_count,
                    "recent_downloads": len(recent_downloads),
                    "time_window": f"{time_window} seconds",
                },
                indicators=["mass_download", "rapid_export"],
            )

        return None

    def check_privilege_escalation(
        self, user_id: str, requested_role: str, current_role: str, endpoint: str
    ) -> Optional[SecurityIncident]:
        """Check for privilege escalation attempts"""
        if current_role != "admin" and requested_role == "admin":
            return self._create_incident(
                threat_type=ThreatType.PRIVILEGE_ESCALATION,
                threat_level=ThreatLevel.CRITICAL,
                user_id=user_id,
                ip_address="",  # Should be passed in
                description="Privilege escalation attempt",
                details={
                    "current_role": current_role,
                    "requested_role": requested_role,
                    "endpoint": endpoint,
                },
                indicators=["unauthorized_admin_access", "role_manipulation"],
            )

        return None

    def analyze_user_behavior(
        self, user_id: str, login_time: datetime, ip_address: str, user_agent: str
    ) -> List[SecurityIncident]:
        """Analyze user behavior for anomalies"""
        incidents = []

        # Get or create user profile
        profile = self.user_behaviors.get(user_id)
        if not profile:
            profile = UserBehaviorProfile(user_id=user_id)
            self.user_behaviors[user_id] = profile

        # Check login time anomaly
        hour = login_time.hour
        if profile.typical_login_times and hour not in profile.typical_login_times:
            # Unusual login time
            avg_hour = sum(profile.typical_login_times) / len(
                profile.typical_login_times
            )
            if abs(hour - avg_hour) > 6:  # More than 6 hours difference
                incident = self._create_incident(
                    threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                    threat_level=ThreatLevel.MEDIUM,
                    user_id=user_id,
                    ip_address=ip_address,
                    description="Unusual login time detected",
                    details={
                        "login_hour": hour,
                        "typical_hours": profile.typical_login_times[:5],
                    },
                    indicators=["unusual_time", "behavior_anomaly"],
                )
                incidents.append(incident)

        # Check IP address anomaly
        if (
            profile.typical_ip_addresses
            and ip_address not in profile.typical_ip_addresses
        ):
            if len(profile.typical_ip_addresses) > 3:  # Established pattern
                incident = self._create_incident(
                    threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                    threat_level=ThreatLevel.MEDIUM,
                    user_id=user_id,
                    ip_address=ip_address,
                    description="Login from unusual IP address",
                    details={
                        "new_ip": ip_address,
                        "known_ips": list(profile.typical_ip_addresses)[:5],
                    },
                    indicators=["new_location", "ip_anomaly"],
                )
                incidents.append(incident)

        # Update profile
        profile.typical_login_times.append(hour)
        profile.typical_ip_addresses.add(ip_address)
        profile.typical_user_agents.add(user_agent)
        profile.last_updated = datetime.utcnow()

        # Keep profile data reasonable size
        if len(profile.typical_login_times) > 100:
            profile.typical_login_times = profile.typical_login_times[-100:]
        if len(profile.typical_ip_addresses) > 20:
            # Keep most recent
            profile.typical_ip_addresses = set(list(profile.typical_ip_addresses)[-20:])

        return incidents

    def get_threat_summary(self) -> Dict[str, Any]:
        """Get current threat landscape summary"""
        db = self.db_session_factory()

        try:
            # Count incidents by type and level
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)

            incidents = (
                db.query(SecurityIncidentDB)
                .filter(SecurityIncidentDB.timestamp > recent_cutoff)
                .all()
            )

            threat_counts = defaultdict(int)
            level_counts = defaultdict(int)

            for incident in incidents:
                threat_counts[incident.threat_type] += 1
                level_counts[incident.threat_level] += 1

            # Get active incidents
            active = [
                inc for inc in self.active_incidents.values() if not inc.mitigated
            ]

            return {
                "summary": {
                    "total_incidents_24h": len(incidents),
                    "active_incidents": len(active),
                    "critical_threats": level_counts.get(ThreatLevel.CRITICAL, 0),
                    "high_threats": level_counts.get(ThreatLevel.HIGH, 0),
                },
                "threat_types": dict(threat_counts),
                "threat_levels": dict(level_counts),
                "top_threats": sorted(
                    threat_counts.items(), key=lambda x: x[1], reverse=True
                )[:5],
                "monitored_users": len(self.user_behaviors),
                "timestamp": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    # Private methods
    def _create_incident(
        self,
        threat_type: ThreatType,
        threat_level: ThreatLevel,
        ip_address: str,
        description: str,
        details: Dict[str, Any],
        indicators: List[str],
        user_id: Optional[str] = None,
    ) -> SecurityIncident:
        """Create and record security incident"""
        import uuid

        incident = SecurityIncident(
            incident_id=str(uuid.uuid4()),
            threat_type=threat_type,
            threat_level=threat_level,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            ip_address=ip_address,
            description=description,
            details=details,
            indicators=indicators,
        )

        # Store in memory
        self.active_incidents[incident.incident_id] = incident

        # Log to audit
        self.audit_logger.log_event(
            AuditEvent(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_id,
                ip_address=ip_address,
                action="threat_detected",
                details={
                    "threat_type": threat_type,
                    "threat_level": threat_level,
                    "description": description,
                    "indicators": indicators,
                },
            )
        )

        # Save to database
        self._save_incident(incident)

        # Trigger alerts for critical threats
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self._trigger_security_alert(incident)

        return incident

    def _save_incident(self, incident: SecurityIncident):
        """Save incident to database"""
        db = self.db_session_factory()

        try:
            db_incident = SecurityIncidentDB(
                incident_id=incident.incident_id,
                threat_type=incident.threat_type,
                threat_level=incident.threat_level,
                timestamp=incident.timestamp,
                user_id=incident.user_id,
                ip_address=incident.ip_address,
                description=incident.description,
                details=incident.details,
                indicators=incident.indicators,
                mitigated=incident.mitigated,
            )

            db.add(db_incident)
            db.commit()

        except Exception as e:
            logger.error(f"Failed to save security incident: {e}")
        finally:
            db.close()

    def _detect_sql_injection(
        self, path: str, params: Dict[str, Any], headers: Dict[str, str]
    ) -> List[str]:
        """Detect SQL injection patterns"""
        threats = []

        # Check all input sources
        all_inputs = [path]
        all_inputs.extend(str(v) for v in params.values())
        all_inputs.extend(str(v) for v in headers.values())

        for input_str in all_inputs:
            for pattern in self.sql_injection_patterns:
                if re.search(pattern, input_str, re.IGNORECASE):
                    threats.append(f"SQL pattern: {pattern}")

        return threats

    def _detect_xss(self, params: Dict[str, Any], headers: Dict[str, str]) -> List[str]:
        """Detect XSS patterns"""
        threats = []

        all_inputs = []
        all_inputs.extend(str(v) for v in params.values())
        all_inputs.extend(str(v) for v in headers.values())

        for input_str in all_inputs:
            for pattern in self.xss_patterns:
                if re.search(pattern, input_str, re.IGNORECASE):
                    threats.append(f"XSS pattern: {pattern}")

        return threats

    def _detect_path_traversal(self, path: str, params: Dict[str, Any]) -> bool:
        """Detect path traversal attempts"""
        all_inputs = [path]
        all_inputs.extend(str(v) for v in params.values())

        for input_str in all_inputs:
            for pattern in self.path_traversal_patterns:
                if re.search(pattern, input_str, re.IGNORECASE):
                    return True

        return False

    def _track_user_request(self, user_id: str, endpoint: str, ip_address: str):
        """Track user request patterns"""
        self.request_patterns[user_id].append(
            {
                "timestamp": datetime.utcnow(),
                "endpoint": endpoint,
                "ip_address": ip_address,
            }
        )

        # Update behavior profile
        if user_id in self.user_behaviors:
            profile = self.user_behaviors[user_id]
            profile.typical_endpoints.add(endpoint)

    async def _check_active_threats(self):
        """Check and update active threats"""
        # Clean up old incidents
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.active_incidents = {
            k: v for k, v in self.active_incidents.items() if v.timestamp > cutoff
        }

    async def _analyze_user_behaviors(self):
        """Analyze user behavior patterns"""
        # This would implement more sophisticated behavioral analysis
        pass

    async def _detect_anomalies(self):
        """Detect anomalous patterns across the system"""
        # This would implement system-wide anomaly detection
        pass

    def _trigger_security_alert(self, incident: SecurityIncident):
        """Trigger security alert for critical incidents"""
        logger.critical(
            f"SECURITY ALERT: {incident.threat_type} - {incident.description}"
        )
        # In production, this would send notifications to security team
