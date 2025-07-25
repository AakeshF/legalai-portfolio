# health.py - Enhanced health check system
import os
import time
import psutil
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import asyncio

from database import engine, SessionLocal
from logger import get_logger
from config import settings

logger = get_logger(__name__)


class HealthChecker:
    """
    Comprehensive health check system for production monitoring
    """

    def __init__(self):
        self.start_time = time.time()
        self.checks_performed = 0
        self.last_check_time = None
        self.cached_results = {}
        self.cache_duration = 30  # seconds

    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        start_time = time.time()

        try:
            with SessionLocal() as db:
                # Test basic connectivity
                result = db.execute(text("SELECT 1")).scalar()

                # Get table counts
                documents_count = db.execute(
                    text("SELECT COUNT(*) FROM documents")
                ).scalar()
                sessions_count = db.execute(
                    text("SELECT COUNT(*) FROM chat_sessions")
                ).scalar()
                messages_count = db.execute(
                    text("SELECT COUNT(*) FROM chat_messages")
                ).scalar()

                # Check database size (SQLite specific)
                if "sqlite" in settings.database_url:
                    db_file = settings.database_url.replace("sqlite:///", "")
                    if os.path.exists(db_file):
                        db_size = os.path.getsize(db_file)
                    else:
                        db_size = 0
                else:
                    db_size = None

                response_time = time.time() - start_time

                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time * 1000, 2),
                    "connection_pool": {
                        "size": engine.pool.size(),
                        "checked_in": engine.pool.checkedin(),
                        "overflow": engine.pool.overflow(),
                        "total": engine.pool.checkedout(),
                    },
                    "statistics": {
                        "documents": documents_count,
                        "chat_sessions": sessions_count,
                        "chat_messages": messages_count,
                    },
                    "database_size_bytes": db_size,
                }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def check_ai_service(self) -> Dict[str, Any]:
        """Check AI service availability"""
        start_time = time.time()

        try:
            # Check if API key is configured
            api_key = getattr(settings, "ai_api_key", None) or getattr(
                settings, "openai_api_key", None
            )
            if not api_key:
                return {
                    "status": "degraded",
                    "mode": "demo",
                    "reason": "No API key configured",
                }

            # Test API connectivity
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=5.0,
                )

                response_time = time.time() - start_time

                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time_ms": round(response_time * 1000, 2),
                        "mode": "production",
                        "available_models": len(response.json().get("data", [])),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "response_time_ms": round(response_time * 1000, 2),
                        "status_code": response.status_code,
                        "mode": "demo",
                    }

        except httpx.TimeoutException:
            return {"status": "unhealthy", "error": "API timeout", "mode": "demo"}
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__,
                "mode": "demo",
            }

    async def check_file_storage(self) -> Dict[str, Any]:
        """Check file storage availability and capacity"""
        try:
            upload_dir = settings.upload_directory

            # Check if directory exists and is writable
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)

            # Test write permissions
            test_file = os.path.join(upload_dir, ".health_check")
            with open(test_file, "w") as f:
                f.write("health check")
            os.remove(test_file)

            # Get storage statistics
            stat = os.statvfs(upload_dir)
            total_space = stat.f_blocks * stat.f_frsize
            available_space = stat.f_available * stat.f_frsize
            used_space = total_space - available_space
            usage_percent = (used_space / total_space) * 100

            # Count files
            files = [
                f
                for f in os.listdir(upload_dir)
                if os.path.isfile(os.path.join(upload_dir, f))
            ]
            total_size = sum(
                os.path.getsize(os.path.join(upload_dir, f)) for f in files
            )

            return {
                "status": "healthy" if usage_percent < 90 else "warning",
                "writable": True,
                "usage_percent": round(usage_percent, 2),
                "available_space_gb": round(available_space / (1024**3), 2),
                "total_space_gb": round(total_space / (1024**3), 2),
                "files_count": len(files),
                "files_total_size_mb": round(total_size / (1024**2), 2),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "writable": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")

            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()

            return {
                "status": (
                    "healthy" if cpu_percent < 80 and memory.percent < 80 else "warning"
                ),
                "cpu": {"usage_percent": cpu_percent, "count": cpu_count},
                "memory": {
                    "usage_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                },
                "disk": {
                    "usage_percent": disk.percent,
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                },
                "process": {
                    "memory_mb": round(process_memory.rss / (1024**2), 2),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                },
            }
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def get_comprehensive_health(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get comprehensive health status of all services"""
        current_time = time.time()

        # Check cache
        if use_cache and self.cached_results and self.last_check_time:
            if current_time - self.last_check_time < self.cache_duration:
                return self.cached_results

        # Perform all checks concurrently
        database_task = asyncio.create_task(self.check_database())
        ai_service_task = asyncio.create_task(self.check_ai_service())
        file_storage_task = asyncio.create_task(self.check_file_storage())

        # System resources check is synchronous
        system_resources = self.check_system_resources()

        # Wait for async checks
        database = await database_task
        ai_service = await ai_service_task
        file_storage = await file_storage_task

        # Calculate overall status
        statuses = [
            database["status"],
            ai_service["status"],
            file_storage["status"],
            system_resources["status"],
        ]

        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        # Calculate uptime
        uptime_seconds = current_time - self.start_time
        uptime_days = int(uptime_seconds // 86400)
        uptime_hours = int((uptime_seconds % 86400) // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)

        self.checks_performed += 1

        result = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "uptime": {
                "days": uptime_days,
                "hours": uptime_hours,
                "minutes": uptime_minutes,
                "total_seconds": int(uptime_seconds),
            },
            "checks_performed": self.checks_performed,
            "services": {
                "database": database,
                "ai_service": ai_service,
                "file_storage": file_storage,
                "system_resources": system_resources,
            },
        }

        # Update cache
        self.cached_results = result
        self.last_check_time = current_time

        return result

    async def get_simple_health(self) -> Dict[str, Any]:
        """Get simple health status for load balancer checks"""
        try:
            # Quick database check
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))

            return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
        except Exception:
            return {"status": "error", "timestamp": datetime.utcnow().isoformat()}


# Global health checker instance
health_checker = HealthChecker()
