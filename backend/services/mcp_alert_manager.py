"""
MCP Alert Manager

Automated alert system for monitoring MCP server health, performance,
and cache behavior with configurable rules and notifications.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
from enum import Enum
import json

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import MCPAlert, MCPMetrics, MCPHealthStatus
from logger import get_logger
from config import settings
from email_service import EmailService

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    ERROR_RATE = "error_rate"
    SLOW_RESPONSE = "slow_response"
    SERVER_DOWN = "server_down"
    CACHE_PERFORMANCE = "cache_performance"
    RESOURCE_USAGE = "resource_usage"
    CUSTOM = "custom"


@dataclass
class Alert:
    severity: AlertSeverity
    type: AlertType
    title: str
    description: str
    server_name: Optional[str] = None
    actions: List[str] = field(default_factory=list)
    auto_resolve: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self):
        return {
            "severity": self.severity,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "server_name": self.server_name,
            "actions": self.actions,
            "auto_resolve": self.auto_resolve,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class AlertRule(ABC):
    """Base class for alert rules"""
    
    def __init__(self, name: str, severity: AlertSeverity):
        self.name = name
        self.severity = severity
        self.title = name
        self.can_auto_resolve = False
        
    @abstractmethod
    async def is_triggered(self, context: Dict[str, Any]) -> bool:
        """Check if alert should be triggered"""
        pass
    
    @abstractmethod
    def get_description(self, context: Dict[str, Any]) -> str:
        """Get alert description"""
        pass
    
    def get_recommended_actions(self, context: Dict[str, Any]) -> List[str]:
        """Get recommended actions for the alert"""
        return []


class HighErrorRateRule(AlertRule):
    """Alert when error rate exceeds threshold"""
    
    def __init__(self, threshold: float = 0.1):
        super().__init__("High Error Rate", AlertSeverity.HIGH)
        self.threshold = threshold
        self.title = f"Error rate exceeds {threshold*100}%"
        
    async def is_triggered(self, context: Dict[str, Any]) -> bool:
        server_performance = context.get("server_performance", {})
        
        for server, perf in server_performance.items():
            error_rate = perf.get("error_rate", 0) / 100
            if error_rate > self.threshold:
                context["triggered_server"] = server
                context["error_rate"] = error_rate
                return True
        
        return False
    
    def get_description(self, context: Dict[str, Any]) -> str:
        server = context.get("triggered_server", "Unknown")
        error_rate = context.get("error_rate", 0) * 100
        return f"Server '{server}' has {error_rate:.1f}% error rate"
    
    def get_recommended_actions(self, context: Dict[str, Any]) -> List[str]:
        return [
            "Check server logs for error details",
            "Verify server connectivity",
            "Review recent configuration changes",
            "Consider restarting the server if errors persist"
        ]


class SlowResponseRule(AlertRule):
    """Alert when response time exceeds threshold"""
    
    def __init__(self, threshold: float = 5.0):
        super().__init__("Slow Response Time", AlertSeverity.MEDIUM)
        self.threshold = threshold
        self.title = f"Response time exceeds {threshold}s"
        
    async def is_triggered(self, context: Dict[str, Any]) -> bool:
        server_performance = context.get("server_performance", {})
        
        for server, perf in server_performance.items():
            avg_response_time = perf.get("avg_response_time", 0)
            if avg_response_time > self.threshold:
                context["triggered_server"] = server
                context["response_time"] = avg_response_time
                return True
        
        return False
    
    def get_description(self, context: Dict[str, Any]) -> str:
        server = context.get("triggered_server", "Unknown")
        response_time = context.get("response_time", 0)
        return f"Server '{server}' averaging {response_time:.2f}s response time"
    
    def get_recommended_actions(self, context: Dict[str, Any]) -> List[str]:
        return [
            "Analyze slow queries",
            "Check server resource usage",
            "Consider implementing caching",
            "Optimize database queries"
        ]


class ServerDownRule(AlertRule):
    """Alert when server is down"""
    
    def __init__(self, max_downtime: int = 300):
        super().__init__("Server Down", AlertSeverity.CRITICAL)
        self.max_downtime = max_downtime  # seconds
        self.title = "Server is not responding"
        self.can_auto_resolve = True
        
    async def is_triggered(self, context: Dict[str, Any]) -> bool:
        health_status = context.get("health_status", {})
        
        for server_name, health in health_status.items():
            if health.get("status") == "error":
                # Check how long it's been down
                last_check = health.get("last_check")
                if last_check:
                    downtime = (datetime.utcnow() - datetime.fromisoformat(last_check)).seconds
                    if downtime > self.max_downtime:
                        context["triggered_server"] = server_name
                        context["downtime"] = downtime
                        context["error"] = health.get("error", "Unknown error")
                        return True
        
        return False
    
    def get_description(self, context: Dict[str, Any]) -> str:
        server = context.get("triggered_server", "Unknown")
        downtime = context.get("downtime", 0)
        error = context.get("error", "Unknown error")
        return f"Server '{server}' has been down for {downtime}s. Error: {error}"
    
    def get_recommended_actions(self, context: Dict[str, Any]) -> List[str]:
        return [
            "Attempt to restart the server",
            "Check server logs",
            "Verify network connectivity",
            "Contact system administrator if issue persists"
        ]


class CacheHitRateRule(AlertRule):
    """Alert when cache hit rate is too low"""
    
    def __init__(self, min_hit_rate: float = 0.6):
        super().__init__("Low Cache Hit Rate", AlertSeverity.MEDIUM)
        self.min_hit_rate = min_hit_rate
        self.title = f"Cache hit rate below {min_hit_rate*100}%"
        
    async def is_triggered(self, context: Dict[str, Any]) -> bool:
        cache_analytics = context.get("cache_analytics", {})
        hit_rate = cache_analytics.get("hit_rate", 1.0)
        
        if hit_rate < self.min_hit_rate:
            context["hit_rate"] = hit_rate
            return True
        
        return False
    
    def get_description(self, context: Dict[str, Any]) -> str:
        hit_rate = context.get("hit_rate", 0) * 100
        return f"Cache hit rate is {hit_rate:.1f}%, below threshold of {self.min_hit_rate*100}%"
    
    def get_recommended_actions(self, context: Dict[str, Any]) -> List[str]:
        return [
            "Review cache key patterns",
            "Increase cache TTL for frequently accessed data",
            "Consider pre-warming cache",
            "Analyze miss patterns"
        ]


class CustomRule(AlertRule):
    """Custom rule with user-defined logic"""
    
    def __init__(
        self,
        name: str,
        severity: AlertSeverity,
        condition: Callable[[Dict[str, Any]], bool],
        description_template: str,
        actions: List[str] = None
    ):
        super().__init__(name, severity)
        self.condition = condition
        self.description_template = description_template
        self.actions = actions or []
        
    async def is_triggered(self, context: Dict[str, Any]) -> bool:
        return self.condition(context)
    
    def get_description(self, context: Dict[str, Any]) -> str:
        return self.description_template.format(**context)
    
    def get_recommended_actions(self, context: Dict[str, Any]) -> List[str]:
        return self.actions


class MCPAlertManager:
    """Manages automated alerts for MCP monitoring"""
    
    def __init__(self):
        self.alert_rules = [
            HighErrorRateRule(threshold=0.1),
            SlowResponseRule(threshold=5.0),
            ServerDownRule(max_downtime=300),
            CacheHitRateRule(min_hit_rate=0.6)
        ]
        self.active_alerts: Dict[str, Alert] = {}
        self.notification_channels = []
        self._initialized = False
        
    async def initialize(self):
        """Initialize alert manager"""
        if self._initialized:
            return
            
        self._initialized = True
        
        # Initialize notification channels
        if settings.email_enabled:
            self.notification_channels.append(self._send_email_notification)
        
        # Start alert checking
        asyncio.create_task(self._periodic_alert_check())
        
        logger.info("MCP Alert Manager initialized")
    
    def add_rule(self, rule: AlertRule):
        """Add a custom alert rule"""
        self.alert_rules.append(rule)
    
    async def check_alerts(self, context: Optional[Dict[str, Any]] = None) -> List[Alert]:
        """Check all alert rules and return triggered alerts"""
        if context is None:
            context = await self._gather_context()
        
        triggered_alerts = []
        
        for rule in self.alert_rules:
            try:
                if await rule.is_triggered(context):
                    alert = Alert(
                        severity=rule.severity,
                        type=AlertType.CUSTOM,
                        title=rule.title,
                        description=rule.get_description(context),
                        server_name=context.get("triggered_server"),
                        actions=rule.get_recommended_actions(context),
                        auto_resolve=rule.can_auto_resolve,
                        metadata={"rule": rule.name, "context": context}
                    )
                    
                    # Check if this is a new alert
                    alert_key = f"{rule.name}:{context.get('triggered_server', 'global')}"
                    
                    if alert_key not in self.active_alerts:
                        triggered_alerts.append(alert)
                        self.active_alerts[alert_key] = alert
                        
                        # Store in database
                        await self._store_alert(alert)
                        
                        # Send notifications
                        await self._send_notifications(alert)
                        
                elif rule.can_auto_resolve:
                    # Check if we should auto-resolve
                    alert_key = f"{rule.name}:{context.get('triggered_server', 'global')}"
                    
                    if alert_key in self.active_alerts:
                        # Auto-resolve the alert
                        await self._resolve_alert(alert_key)
                        
            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {str(e)}")
        
        return triggered_alerts
    
    async def _gather_context(self) -> Dict[str, Any]:
        """Gather context data for alert checking"""
        from services.mcp_monitoring import MCPMonitoringService
        from services.mcp_cache_monitor import MCPCacheMonitor
        
        monitor = MCPMonitoringService()
        cache_monitor = MCPCacheMonitor()
        
        # Get recent analytics
        analytics = await monitor.get_analytics_dashboard("1h")
        
        # Get health status
        health_status = await monitor.check_all_servers()
        
        # Get cache analytics
        cache_analytics = await cache_monitor.analyze_cache_performance(timeframe_hours=1)
        
        return {
            "server_performance": analytics.get("server_performance", {}),
            "action_metrics": analytics.get("action_metrics", {}),
            "error_analysis": analytics.get("error_analysis", {}),
            "health_status": {
                name: health.to_dict() for name, health in health_status.items()
            },
            "cache_analytics": cache_analytics.to_dict()
        }
    
    async def _store_alert(self, alert: Alert):
        """Store alert in database"""
        async for db in get_db():
            try:
                db_alert = MCPAlert(
                    severity=alert.severity,
                    type=alert.type,
                    server_name=alert.server_name,
                    message=alert.description,
                    metadata=json.dumps({
                        "title": alert.title,
                        "actions": alert.actions,
                        "auto_resolve": alert.auto_resolve,
                        "metadata": alert.metadata
                    }),
                    created_at=alert.created_at,
                    resolved=False
                )
                db.add(db_alert)
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error storing alert: {str(e)}")
                await db.rollback()
    
    async def _resolve_alert(self, alert_key: str):
        """Resolve an alert"""
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            del self.active_alerts[alert_key]
            
            # Update database
            async for db in get_db():
                try:
                    # Find the alert in database
                    result = await db.execute(
                        select(MCPAlert).where(
                            and_(
                                MCPAlert.resolved == False,
                                MCPAlert.server_name == alert.server_name,
                                MCPAlert.type == alert.type
                            )
                        ).order_by(MCPAlert.created_at.desc())
                    )
                    
                    db_alert = result.scalar_one_or_none()
                    if db_alert:
                        db_alert.resolved = True
                        db_alert.resolved_at = datetime.utcnow()
                        await db.commit()
                        
                        # Send resolution notification
                        await self._send_resolution_notification(alert)
                        
                except Exception as e:
                    logger.error(f"Error resolving alert: {str(e)}")
                    await db.rollback()
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        for channel in self.notification_channels:
            try:
                await channel(alert)
            except Exception as e:
                logger.error(f"Error sending notification: {str(e)}")
    
    async def _send_email_notification(self, alert: Alert):
        """Send email notification for an alert"""
        email_service = EmailService()
        
        # Build email content
        subject = f"[{alert.severity.upper()}] MCP Alert: {alert.title}"
        
        body = f"""
        <h2>MCP Alert Triggered</h2>
        
        <p><strong>Severity:</strong> {alert.severity.upper()}</p>
        <p><strong>Type:</strong> {alert.type}</p>
        <p><strong>Server:</strong> {alert.server_name or 'Global'}</p>
        <p><strong>Time:</strong> {alert.created_at.isoformat()}</p>
        
        <h3>Description</h3>
        <p>{alert.description}</p>
        
        <h3>Recommended Actions</h3>
        <ul>
        {''.join(f'<li>{action}</li>' for action in alert.actions)}
        </ul>
        
        <p>Please check the MCP monitoring dashboard for more details.</p>
        """
        
        # Send to configured recipients
        recipients = settings.alert_email_recipients
        if recipients:
            for recipient in recipients:
                await email_service.send_email(
                    to=recipient,
                    subject=subject,
                    body=body,
                    is_html=True
                )
    
    async def _send_resolution_notification(self, alert: Alert):
        """Send notification that an alert has been resolved"""
        email_service = EmailService()
        
        subject = f"[RESOLVED] MCP Alert: {alert.title}"
        body = f"""
        <h2>MCP Alert Resolved</h2>
        
        <p>The following alert has been automatically resolved:</p>
        
        <p><strong>Alert:</strong> {alert.title}</p>
        <p><strong>Server:</strong> {alert.server_name or 'Global'}</p>
        <p><strong>Original Time:</strong> {alert.created_at.isoformat()}</p>
        <p><strong>Resolved Time:</strong> {datetime.utcnow().isoformat()}</p>
        
        <p>The issue appears to have been resolved. No further action is required.</p>
        """
        
        recipients = settings.alert_email_recipients
        if recipients:
            for recipient in recipients:
                await email_service.send_email(
                    to=recipient,
                    subject=subject,
                    body=body,
                    is_html=True
                )
    
    async def _periodic_alert_check(self):
        """Periodically check for alerts"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.check_alerts()
                
            except Exception as e:
                logger.error(f"Error in periodic alert check: {str(e)}")
    
    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alert status"""
        async for db in get_db():
            # Get active alerts count by severity
            result = await db.execute(
                select(
                    MCPAlert.severity,
                    func.count(MCPAlert.id).label('count')
                ).where(
                    MCPAlert.resolved == False
                ).group_by(MCPAlert.severity)
            )
            
            severity_counts = {row.severity: row.count for row in result}
            
            # Get recent resolved alerts
            cutoff = datetime.utcnow() - timedelta(hours=24)
            result = await db.execute(
                select(func.count(MCPAlert.id)).where(
                    and_(
                        MCPAlert.resolved == True,
                        MCPAlert.resolved_at > cutoff
                    )
                )
            )
            resolved_24h = result.scalar() or 0
            
            return {
                "active_alerts": len(self.active_alerts),
                "by_severity": severity_counts,
                "resolved_last_24h": resolved_24h,
                "alert_rules": len(self.alert_rules),
                "notification_channels": len(self.notification_channels)
            }