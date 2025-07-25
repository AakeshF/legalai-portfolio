# monitoring.py - Production-grade monitoring and metrics collection
import time
import psutil
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
import json
import logging
from contextlib import asynccontextmanager
from fastapi import Request
import httpx

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Individual metric data point"""

    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None


@dataclass
class HealthCheck:
    """Health check result"""

    service: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates system metrics"""

    def __init__(self, retention_minutes: int = 60):
        self.metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=retention_minutes * 60)
        )
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.active_requests: Dict[str, int] = defaultdict(int)
        self.retention_minutes = retention_minutes

    def record_metric(self, metric: Metric):
        """Record a single metric"""
        key = f"{metric.name}:{json.dumps(metric.tags, sort_keys=True)}"
        self.metrics[key].append(
            {
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat(),
                "unit": metric.unit,
            }
        )

    def increment_counter(
        self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None
    ):
        """Increment a counter metric"""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        self.counters[key] += value
        self.record_metric(
            Metric(
                name=f"{name}_total",
                value=self.counters[key],
                timestamp=datetime.utcnow(),
                tags=tags or {},
            )
        )

    def record_timing(
        self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None
    ):
        """Record timing metric"""
        self.record_metric(
            Metric(
                name=f"{name}_duration_ms",
                value=duration_ms,
                timestamp=datetime.utcnow(),
                tags=tags or {},
                unit="milliseconds",
            )
        )

        # Keep recent timings for percentile calculations
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        self.timers[key].append(duration_ms)
        if len(self.timers[key]) > 1000:  # Keep last 1000 values
            self.timers[key] = self.timers[key][-1000:]

    def get_percentile(
        self, name: str, percentile: float, tags: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get percentile value for timing metric"""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        timings = self.timers.get(key, [])

        if not timings:
            return None

        sorted_timings = sorted(timings)
        index = int(len(sorted_timings) * percentile / 100)
        return sorted_timings[min(index, len(sorted_timings) - 1)]

    def get_rate(
        self, name: str, window_seconds: int = 60, tags: Optional[Dict[str, str]] = None
    ) -> float:
        """Calculate rate per second over window"""
        key = f"{name}_total:{json.dumps(tags or {}, sort_keys=True)}"
        metrics = list(self.metrics.get(key, []))

        if len(metrics) < 2:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        recent_metrics = [
            m for m in metrics if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]

        if len(recent_metrics) < 2:
            return 0.0

        time_diff = (
            datetime.fromisoformat(recent_metrics[-1]["timestamp"])
            - datetime.fromisoformat(recent_metrics[0]["timestamp"])
        ).total_seconds()

        if time_diff <= 0:
            return 0.0

        value_diff = recent_metrics[-1]["value"] - recent_metrics[0]["value"]
        return value_diff / time_diff

    @asynccontextmanager
    async def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_timing(name, duration_ms, tags)


class SystemMonitor:
    """Monitors system health and resources"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.health_checks: Dict[str, HealthCheck] = {}
        self._monitoring_task = None

    async def start(self):
        """Start monitoring background task"""
        self._monitoring_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Collect system metrics every 10 seconds
                await self._collect_system_metrics()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)

    async def _collect_system_metrics(self):
        """Collect system resource metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics.record_metric(
            Metric(
                name="system_cpu_usage_percent",
                value=cpu_percent,
                timestamp=datetime.utcnow(),
                unit="percent",
            )
        )

        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics.record_metric(
            Metric(
                name="system_memory_usage_percent",
                value=memory.percent,
                timestamp=datetime.utcnow(),
                unit="percent",
            )
        )
        self.metrics.record_metric(
            Metric(
                name="system_memory_available_mb",
                value=memory.available / (1024 * 1024),
                timestamp=datetime.utcnow(),
                unit="megabytes",
            )
        )

        # Disk usage
        disk = psutil.disk_usage("/")
        self.metrics.record_metric(
            Metric(
                name="system_disk_usage_percent",
                value=disk.percent,
                timestamp=datetime.utcnow(),
                unit="percent",
            )
        )

        # Process-specific metrics
        process = psutil.Process()
        self.metrics.record_metric(
            Metric(
                name="process_memory_mb",
                value=process.memory_info().rss / (1024 * 1024),
                timestamp=datetime.utcnow(),
                unit="megabytes",
            )
        )
        self.metrics.record_metric(
            Metric(
                name="process_cpu_percent",
                value=process.cpu_percent(),
                timestamp=datetime.utcnow(),
                unit="percent",
            )
        )
        self.metrics.record_metric(
            Metric(
                name="process_open_files",
                value=len(process.open_files()),
                timestamp=datetime.utcnow(),
            )
        )

    async def check_database_health(self, db_func) -> HealthCheck:
        """Check database connectivity and performance"""
        start_time = time.time()
        try:
            # Simple query to test connection
            db = db_func()
            result = db.execute("SELECT 1").scalar()
            db.close()

            latency_ms = (time.time() - start_time) * 1000

            return HealthCheck(
                service="database",
                status="healthy",
                latency_ms=latency_ms,
                last_check=datetime.utcnow(),
                details={"connected": True},
            )
        except Exception as e:
            return HealthCheck(
                service="database",
                status="unhealthy",
                last_check=datetime.utcnow(),
                details={"error": str(e)},
            )

    async def check_ai_service_health(self, api_key: str, base_url: str) -> HealthCheck:
        """Check AI service availability"""
        if not api_key:
            return HealthCheck(
                service="ai_service",
                status="unhealthy",
                last_check=datetime.utcnow(),
                details={"error": "No API key configured"},
            )

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Make a minimal API call to check connectivity
                response = await client.get(
                    f"{base_url}/models", headers={"Authorization": f"Bearer {api_key}"}
                )

                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    return HealthCheck(
                        service="ai_service",
                        status="healthy",
                        latency_ms=latency_ms,
                        last_check=datetime.utcnow(),
                        details={"available": True},
                    )
                else:
                    return HealthCheck(
                        service="ai_service",
                        status="degraded",
                        latency_ms=latency_ms,
                        last_check=datetime.utcnow(),
                        details={"status_code": response.status_code},
                    )
        except Exception as e:
            return HealthCheck(
                service="ai_service",
                status="unhealthy",
                last_check=datetime.utcnow(),
                details={"error": str(e)},
            )

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        # Calculate aggregate health
        all_healthy = all(
            check.status == "healthy" for check in self.health_checks.values()
        )
        any_unhealthy = any(
            check.status == "unhealthy" for check in self.health_checks.values()
        )

        if all_healthy:
            overall_status = "healthy"
        elif any_unhealthy:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        # Get current resource usage
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                name: {
                    "status": check.status,
                    "latency_ms": check.latency_ms,
                    "last_check": (
                        check.last_check.isoformat() if check.last_check else None
                    ),
                    "details": check.details,
                }
                for name, check in self.health_checks.items()
            },
            "resources": {
                "cpu_percent": cpu_usage,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
            },
        }


class RequestTracker:
    """Tracks HTTP request metrics"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector

    async def track_request(self, request: Request, call_next):
        """Middleware to track request metrics"""
        # Start tracking
        start_time = time.time()
        path = request.url.path
        method = request.method

        # Track active requests
        self.metrics.active_requests[path] += 1

        try:
            # Process request
            response = await call_next(request)

            # Record metrics
            duration_ms = (time.time() - start_time) * 1000

            self.metrics.record_timing(
                "http_request",
                duration_ms,
                tags={
                    "method": method,
                    "path": path,
                    "status": str(response.status_code),
                },
            )

            self.metrics.increment_counter(
                "http_requests",
                tags={
                    "method": method,
                    "path": path,
                    "status": str(response.status_code),
                },
            )

            # Track error rate
            if response.status_code >= 400:
                self.metrics.increment_counter(
                    "http_errors",
                    tags={
                        "method": method,
                        "path": path,
                        "status": str(response.status_code),
                    },
                )

            return response

        finally:
            self.metrics.active_requests[path] -= 1


# Global metrics instance
metrics_collector = MetricsCollector()
system_monitor = SystemMonitor(metrics_collector)
request_tracker = RequestTracker(metrics_collector)
