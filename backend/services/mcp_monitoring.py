"""
MCP Monitoring and Analytics Service

Provides comprehensive monitoring, health checks, and performance analytics
for the Model Context Protocol (MCP) integration layer.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import time
import asyncio
from enum import Enum
import json
from collections import defaultdict
import statistics

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import MCPMetrics, MCPHealthStatus, MCPAlert
from logger import get_logger
from config import settings

logger = get_logger(__name__)


class ServerStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    ERROR = "error"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ServerHealth:
    status: ServerStatus
    response_time: Optional[float] = None
    last_check: Optional[datetime] = None
    capabilities: List[str] = None
    version: Optional[str] = None
    uptime_percentage: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self):
        return {
            "status": self.status,
            "response_time": self.response_time,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "capabilities": self.capabilities or [],
            "version": self.version,
            "uptime_percentage": self.uptime_percentage,
            "error": self.error,
        }


@dataclass
class PerformanceMetrics:
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    total_requests: int
    success_rate: float
    error_rate: float

    def to_dict(self):
        return {
            "avg_response_time": self.avg_response_time,
            "p95_response_time": self.p95_response_time,
            "p99_response_time": self.p99_response_time,
            "total_requests": self.total_requests,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
        }


@dataclass
class CacheAnalytics:
    hit_rate: float
    miss_patterns: List[Dict[str, Any]]
    stale_data_incidents: int
    cache_size: int
    eviction_rate: float
    recommendations: List[str]

    def to_dict(self):
        return {
            "hit_rate": self.hit_rate,
            "miss_patterns": self.miss_patterns,
            "stale_data_incidents": self.stale_data_incidents,
            "cache_size": self.cache_size,
            "eviction_rate": self.eviction_rate,
            "recommendations": self.recommendations,
        }


class MetricsCollector:
    """Collects and stores MCP metrics"""

    def __init__(self):
        self.buffer = []
        self.buffer_size = 100
        self.flush_interval = 30  # seconds

    async def record(self, metrics: Dict[str, Any]):
        """Record metrics to buffer"""
        self.buffer.append(metrics)

        if len(self.buffer) >= self.buffer_size:
            await self.flush()

    async def flush(self):
        """Flush metrics buffer to database"""
        if not self.buffer:
            return

        async for db in get_db():
            try:
                for metric in self.buffer:
                    db_metric = MCPMetrics(
                        server_name=metric["server"],
                        action=metric["action"],
                        duration=metric["duration"],
                        success=metric["success"],
                        error=metric.get("error"),
                        timestamp=metric["timestamp"],
                        metadata=json.dumps(metric.get("metadata", {})),
                    )
                    db.add(db_metric)

                await db.commit()
                self.buffer.clear()

            except Exception as e:
                logger.error(f"Error flushing metrics: {str(e)}")
                await db.rollback()


class HealthChecker:
    """Monitors health of MCP servers"""

    def __init__(self):
        self.health_history = defaultdict(list)
        self.max_history = 100

    async def update_server_health(self, server: str, success: bool):
        """Update server health history"""
        self.health_history[server].append(
            {"success": success, "timestamp": datetime.utcnow()}
        )

        # Keep only recent history
        if len(self.health_history[server]) > self.max_history:
            self.health_history[server] = self.health_history[server][
                -self.max_history :
            ]

    async def calculate_uptime(self, server: str, window_hours: int = 24) -> float:
        """Calculate uptime percentage for a server"""
        history = self.health_history.get(server, [])
        if not history:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        recent_checks = [h for h in history if h["timestamp"] > cutoff]

        if not recent_checks:
            return 0.0

        successful = sum(1 for h in recent_checks if h["success"])
        return (successful / len(recent_checks)) * 100


class PerformanceTracker:
    """Tracks and analyzes MCP performance"""

    def __init__(self):
        self.performance_data = defaultdict(lambda: defaultdict(list))
        self.max_samples = 1000

    async def analyze_performance(self, server: str, action: str, duration: float):
        """Analyze performance metrics"""
        key = f"{server}:{action}"
        self.performance_data[server][action].append(duration)

        # Keep only recent samples
        if len(self.performance_data[server][action]) > self.max_samples:
            self.performance_data[server][action] = self.performance_data[server][
                action
            ][-self.max_samples :]

    def get_statistics(self, server: str, action: str) -> Dict[str, float]:
        """Get performance statistics for a server/action"""
        durations = self.performance_data.get(server, {}).get(action, [])
        if not durations:
            return {}

        sorted_durations = sorted(durations)
        return {
            "avg": statistics.mean(durations),
            "min": min(durations),
            "max": max(durations),
            "p50": sorted_durations[len(sorted_durations) // 2],
            "p95": sorted_durations[int(len(sorted_durations) * 0.95)],
            "p99": sorted_durations[int(len(sorted_durations) * 0.99)],
        }


class MCPMonitoringService:
    """Main monitoring service for MCP integration"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
        self.performance_tracker = PerformanceTracker()
        self.mcp_servers = {}  # Will be populated by MCP manager

    async def initialize(self, mcp_servers: Dict[str, Any]):
        """Initialize monitoring with MCP servers"""
        self.mcp_servers = mcp_servers

        # Start background tasks
        asyncio.create_task(self._periodic_health_check())
        asyncio.create_task(self._periodic_metrics_flush())

    async def track_mcp_request(
        self,
        server: str,
        action: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Track an MCP request"""
        # Record metrics
        await self.metrics_collector.record(
            {
                "server": server,
                "action": action,
                "duration": duration,
                "success": success,
                "error": error,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {},
            }
        )

        # Update health status
        await self.health_checker.update_server_health(server, success)

        # Track performance
        await self.performance_tracker.analyze_performance(server, action, duration)

        # Check for alerts
        await self._check_alerts(server, action, duration, success, error)

    async def _periodic_health_check(self):
        """Periodically check health of all servers"""
        while True:
            try:
                await self.check_all_servers()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in periodic health check: {str(e)}")
                await asyncio.sleep(60)

    async def _periodic_metrics_flush(self):
        """Periodically flush metrics to database"""
        while True:
            try:
                await self.metrics_collector.flush()
                await asyncio.sleep(30)  # Flush every 30 seconds
            except Exception as e:
                logger.error(f"Error in periodic metrics flush: {str(e)}")
                await asyncio.sleep(30)

    async def check_all_servers(self) -> Dict[str, ServerHealth]:
        """Check health of all MCP servers"""
        health_status = {}

        for server_name, server in self.mcp_servers.items():
            try:
                start_time = time.time()

                # Perform health check
                if hasattr(server, "health_check"):
                    result = await server.health_check()
                else:
                    # Basic connectivity check
                    result = {"status": "ok", "capabilities": []}

                response_time = time.time() - start_time

                # Calculate uptime
                uptime = await self.health_checker.calculate_uptime(server_name)

                # Determine status
                if response_time > 5.0:
                    status = ServerStatus.DEGRADED
                elif uptime < 90:
                    status = ServerStatus.DEGRADED
                else:
                    status = ServerStatus.HEALTHY

                health_status[server_name] = ServerHealth(
                    status=status,
                    response_time=response_time,
                    last_check=datetime.utcnow(),
                    capabilities=result.get("capabilities", []),
                    version=result.get("version"),
                    uptime_percentage=uptime,
                )

                # Record health check
                await self.track_mcp_request(
                    server=server_name,
                    action="health_check",
                    duration=response_time,
                    success=True,
                )

            except Exception as e:
                health_status[server_name] = ServerHealth(
                    status=ServerStatus.ERROR,
                    error=str(e),
                    last_check=datetime.utcnow(),
                )

                # Record failed health check
                await self.track_mcp_request(
                    server=server_name,
                    action="health_check",
                    duration=0,
                    success=False,
                    error=str(e),
                )

        # Store health status in database
        await self._store_health_status(health_status)

        return health_status

    async def _store_health_status(self, health_status: Dict[str, ServerHealth]):
        """Store health status in database"""
        async for db in get_db():
            try:
                for server_name, health in health_status.items():
                    # Update or create health status
                    existing = await db.execute(
                        select(MCPHealthStatus).where(
                            MCPHealthStatus.server_name == server_name
                        )
                    )
                    existing = existing.scalar_one_or_none()

                    if existing:
                        existing.status = health.status
                        existing.response_time = health.response_time
                        existing.last_check = health.last_check
                        existing.error = health.error
                        existing.metadata = json.dumps(
                            {
                                "capabilities": health.capabilities or [],
                                "version": health.version,
                                "uptime_percentage": health.uptime_percentage,
                            }
                        )
                    else:
                        db_health = MCPHealthStatus(
                            server_name=server_name,
                            status=health.status,
                            response_time=health.response_time,
                            last_check=health.last_check,
                            error=health.error,
                            metadata=json.dumps(
                                {
                                    "capabilities": health.capabilities or [],
                                    "version": health.version,
                                    "uptime_percentage": health.uptime_percentage,
                                }
                            ),
                        )
                        db.add(db_health)

                await db.commit()

            except Exception as e:
                logger.error(f"Error storing health status: {str(e)}")
                await db.rollback()

    async def get_analytics_dashboard(self, timeframe: str = "24h") -> Dict[str, Any]:
        """Get comprehensive analytics dashboard"""
        # Parse timeframe
        hours = self._parse_timeframe(timeframe)
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        async for db in get_db():
            # Get server performance
            server_performance = await self._get_server_performance(db, cutoff)

            # Get action metrics
            action_metrics = await self._get_action_metrics(db, cutoff)

            # Get error analysis
            error_analysis = await self._get_error_analysis(db, cutoff)

            # Get usage patterns
            usage_patterns = await self._get_usage_patterns(db, cutoff)

            # Generate optimization suggestions
            suggestions = await self._generate_suggestions(
                server_performance, action_metrics, error_analysis
            )

            return {
                "timeframe": timeframe,
                "generated_at": datetime.utcnow().isoformat(),
                "server_performance": server_performance,
                "action_metrics": action_metrics,
                "error_analysis": error_analysis,
                "usage_patterns": usage_patterns,
                "optimization_suggestions": suggestions,
            }

    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to hours"""
        if timeframe.endswith("h"):
            return int(timeframe[:-1])
        elif timeframe.endswith("d"):
            return int(timeframe[:-1]) * 24
        elif timeframe.endswith("w"):
            return int(timeframe[:-1]) * 24 * 7
        else:
            return 24  # Default to 24 hours

    async def _get_server_performance(
        self, db: AsyncSession, cutoff: datetime
    ) -> Dict[str, Any]:
        """Get server performance metrics"""
        result = await db.execute(
            select(
                MCPMetrics.server_name,
                func.count(MCPMetrics.id).label("total_requests"),
                func.avg(MCPMetrics.duration).label("avg_duration"),
                func.sum(MCPMetrics.success.cast(int)).label("successful_requests"),
            )
            .where(MCPMetrics.timestamp > cutoff)
            .group_by(MCPMetrics.server_name)
        )

        performance = {}
        for row in result:
            success_rate = (
                (row.successful_requests / row.total_requests * 100)
                if row.total_requests > 0
                else 0
            )
            performance[row.server_name] = {
                "total_requests": row.total_requests,
                "avg_response_time": round(row.avg_duration, 3),
                "success_rate": round(success_rate, 2),
                "error_rate": round(100 - success_rate, 2),
            }

        return performance

    async def _get_action_metrics(
        self, db: AsyncSession, cutoff: datetime
    ) -> Dict[str, Any]:
        """Get metrics by action type"""
        result = await db.execute(
            select(
                MCPMetrics.action,
                func.count(MCPMetrics.id).label("count"),
                func.avg(MCPMetrics.duration).label("avg_duration"),
                func.min(MCPMetrics.duration).label("min_duration"),
                func.max(MCPMetrics.duration).label("max_duration"),
            )
            .where(MCPMetrics.timestamp > cutoff)
            .group_by(MCPMetrics.action)
        )

        metrics = {}
        for row in result:
            metrics[row.action] = {
                "count": row.count,
                "avg_duration": round(row.avg_duration, 3),
                "min_duration": round(row.min_duration, 3),
                "max_duration": round(row.max_duration, 3),
            }

        return metrics

    async def _get_error_analysis(
        self, db: AsyncSession, cutoff: datetime
    ) -> Dict[str, Any]:
        """Analyze errors"""
        result = await db.execute(
            select(
                MCPMetrics.server_name,
                MCPMetrics.error,
                func.count(MCPMetrics.id).label("count"),
            )
            .where(and_(MCPMetrics.timestamp > cutoff, MCPMetrics.success == False))
            .group_by(MCPMetrics.server_name, MCPMetrics.error)
        )

        errors = defaultdict(list)
        for row in result:
            if row.error:
                errors[row.server_name].append({"error": row.error, "count": row.count})

        return dict(errors)

    async def _get_usage_patterns(
        self, db: AsyncSession, cutoff: datetime
    ) -> Dict[str, Any]:
        """Analyze usage patterns"""
        # Get hourly distribution
        result = await db.execute(
            select(
                func.extract("hour", MCPMetrics.timestamp).label("hour"),
                func.count(MCPMetrics.id).label("count"),
            )
            .where(MCPMetrics.timestamp > cutoff)
            .group_by("hour")
        )

        hourly_distribution = {int(row.hour): row.count for row in result}

        # Get most active servers
        result = await db.execute(
            select(MCPMetrics.server_name, func.count(MCPMetrics.id).label("count"))
            .where(MCPMetrics.timestamp > cutoff)
            .group_by(MCPMetrics.server_name)
            .order_by(func.count(MCPMetrics.id).desc())
            .limit(5)
        )

        most_active = [
            {"server": row.server_name, "requests": row.count} for row in result
        ]

        return {
            "hourly_distribution": hourly_distribution,
            "most_active_servers": most_active,
        }

    async def _generate_suggestions(
        self,
        server_performance: Dict[str, Any],
        action_metrics: Dict[str, Any],
        error_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate optimization suggestions"""
        suggestions = []

        # Check for slow servers
        for server, perf in server_performance.items():
            if perf["avg_response_time"] > 3.0:
                suggestions.append(
                    {
                        "type": "performance",
                        "severity": AlertSeverity.MEDIUM,
                        "server": server,
                        "message": f"Server '{server}' averaging {perf['avg_response_time']}s response time",
                        "recommendation": "Consider optimizing queries or adding caching",
                    }
                )

            if perf["error_rate"] > 5:
                suggestions.append(
                    {
                        "type": "reliability",
                        "severity": AlertSeverity.HIGH,
                        "server": server,
                        "message": f"Server '{server}' has {perf['error_rate']}% error rate",
                        "recommendation": "Investigate server connectivity and configuration",
                    }
                )

        # Check for slow actions
        for action, metrics in action_metrics.items():
            if metrics["avg_duration"] > 5.0:
                suggestions.append(
                    {
                        "type": "performance",
                        "severity": AlertSeverity.MEDIUM,
                        "action": action,
                        "message": f"Action '{action}' averaging {metrics['avg_duration']}s",
                        "recommendation": "Consider breaking down into smaller operations",
                    }
                )

        # Check for frequent errors
        for server, errors in error_analysis.items():
            total_errors = sum(e["count"] for e in errors)
            if total_errors > 50:
                most_common = max(errors, key=lambda x: x["count"])
                suggestions.append(
                    {
                        "type": "reliability",
                        "severity": AlertSeverity.HIGH,
                        "server": server,
                        "message": f"Server '{server}' has {total_errors} errors",
                        "recommendation": f"Most common error: {most_common['error']}",
                    }
                )

        return suggestions

    async def _check_alerts(
        self,
        server: str,
        action: str,
        duration: float,
        success: bool,
        error: Optional[str],
    ):
        """Check if any alerts should be triggered"""
        alerts = []

        # Check for slow response
        if duration > 10.0:
            alerts.append(
                {
                    "severity": AlertSeverity.HIGH,
                    "type": "slow_response",
                    "server": server,
                    "action": action,
                    "message": f"Extremely slow response: {duration}s",
                }
            )
        elif duration > 5.0:
            alerts.append(
                {
                    "severity": AlertSeverity.MEDIUM,
                    "type": "slow_response",
                    "server": server,
                    "action": action,
                    "message": f"Slow response: {duration}s",
                }
            )

        # Check for errors
        if not success:
            alerts.append(
                {
                    "severity": AlertSeverity.HIGH,
                    "type": "error",
                    "server": server,
                    "action": action,
                    "message": f"Request failed: {error}",
                }
            )

        # Store alerts
        if alerts:
            await self._store_alerts(alerts)

    async def _store_alerts(self, alerts: List[Dict[str, Any]]):
        """Store alerts in database"""
        async for db in get_db():
            try:
                for alert in alerts:
                    db_alert = MCPAlert(
                        severity=alert["severity"],
                        type=alert["type"],
                        server_name=alert.get("server"),
                        message=alert["message"],
                        metadata=json.dumps(
                            {
                                "action": alert.get("action"),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        ),
                        created_at=datetime.utcnow(),
                        resolved=False,
                    )
                    db.add(db_alert)

                await db.commit()

            except Exception as e:
                logger.error(f"Error storing alerts: {str(e)}")
                await db.rollback()

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        async for db in get_db():
            result = await db.execute(
                select(MCPAlert)
                .where(MCPAlert.resolved == False)
                .order_by(MCPAlert.created_at.desc())
            )

            alerts = []
            for alert in result.scalars():
                alerts.append(
                    {
                        "id": alert.id,
                        "severity": alert.severity,
                        "type": alert.type,
                        "server": alert.server_name,
                        "message": alert.message,
                        "created_at": alert.created_at.isoformat(),
                        "metadata": (
                            json.loads(alert.metadata) if alert.metadata else {}
                        ),
                    }
                )

            return alerts

    async def resolve_alert(self, alert_id: int):
        """Resolve an alert"""
        async for db in get_db():
            try:
                alert = await db.get(MCPAlert, alert_id)
                if alert:
                    alert.resolved = True
                    alert.resolved_at = datetime.utcnow()
                    await db.commit()

            except Exception as e:
                logger.error(f"Error resolving alert: {str(e)}")
                await db.rollback()
