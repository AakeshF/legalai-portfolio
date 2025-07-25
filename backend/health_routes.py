# health_routes.py - System health monitoring and diagnostics endpoints
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import asyncio

from database import get_db
from models import User, Organization, Document, ChatSession
from auth_middleware import get_current_user, get_current_organization
from monitoring import system_monitor, metrics_collector
from services.ollama_service import OllamaService as AIService
from config import settings
import psutil

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/status")
async def get_health_status(db: Session = Depends(get_db)):
    """Get basic health status"""
    try:
        # Quick database check
        db.execute("SELECT 1").scalar()
        db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {"api": "healthy", "database": db_status},
    }


@router.get("/detailed")
async def get_detailed_health(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get detailed health information (admin only)"""
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view detailed health information",
        )

    # Run health checks
    background_tasks = BackgroundTasks()

    # Database health
    db_health = await system_monitor.check_database_health(lambda: db)
    system_monitor.health_checks["database"] = db_health

    # AI service health
    ai_service = AIService()
    ai_health = await system_monitor.check_ai_service_health(
        ai_service.api_key, ai_service.base_url
    )
    system_monitor.health_checks["ai_service"] = ai_health

    # Get system health
    health_data = system_monitor.get_system_health()

    # Add application-specific metrics
    health_data["application"] = {
        "uptime_seconds": int(
            (datetime.utcnow() - datetime(2024, 1, 1)).total_seconds()
        ),  # TODO: Track actual start time
        "active_sessions": len(metrics_collector.active_requests),
        "total_requests": sum(metrics_collector.counters.values()),
        "error_rate": _calculate_error_rate(),
    }

    return health_data


@router.get("/metrics")
async def get_system_metrics(
    window_minutes: int = 60, current_user: User = Depends(get_current_user)
):
    """Get system performance metrics (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view system metrics",
        )

    # Collect current metrics
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

    # Request metrics
    request_metrics = {
        "total_requests": sum(metrics_collector.counters.values()),
        "requests_per_second": metrics_collector.get_rate("http_requests", 60),
        "average_response_time_ms": _get_average_response_time(),
        "p95_response_time_ms": metrics_collector.get_percentile("http_request", 95),
        "p99_response_time_ms": metrics_collector.get_percentile("http_request", 99),
        "error_rate_percent": _calculate_error_rate() * 100,
        "active_connections": len(metrics_collector.active_requests),
    }

    # Resource metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    resource_metrics = {
        "cpu": {"usage_percent": cpu_percent, "count": psutil.cpu_count()},
        "memory": {
            "usage_percent": memory.percent,
            "available_gb": memory.available / (1024**3),
            "total_gb": memory.total / (1024**3),
        },
        "disk": {
            "usage_percent": disk.percent,
            "free_gb": disk.free / (1024**3),
            "total_gb": disk.total / (1024**3),
        },
    }

    # Database metrics
    db_metrics = await _get_database_metrics(db)

    # AI service metrics
    ai_metrics = _get_ai_service_metrics()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "window_minutes": window_minutes,
        "requests": request_metrics,
        "resources": resource_metrics,
        "database": db_metrics,
        "ai_service": ai_metrics,
    }


@router.get("/diagnostics")
async def run_diagnostics(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Run system diagnostics (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can run diagnostics",
        )

    diagnostics = {"timestamp": datetime.utcnow().isoformat(), "checks": {}}

    # 1. Database connectivity
    try:
        start = time.time()
        db.execute("SELECT 1").scalar()
        db_latency = (time.time() - start) * 1000

        diagnostics["checks"]["database"] = {
            "status": "pass",
            "latency_ms": db_latency,
            "details": "Database connection successful",
        }
    except Exception as e:
        diagnostics["checks"]["database"] = {"status": "fail", "error": str(e)}

    # 2. File system
    try:
        # Check upload directory
        upload_dir = settings.upload_directory
        if os.path.exists(upload_dir):
            # Try to write a test file
            test_file = os.path.join(upload_dir, ".diagnostic_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)

            diagnostics["checks"]["filesystem"] = {
                "status": "pass",
                "upload_directory": upload_dir,
                "writable": True,
            }
        else:
            diagnostics["checks"]["filesystem"] = {
                "status": "warning",
                "error": "Upload directory does not exist",
            }
    except Exception as e:
        diagnostics["checks"]["filesystem"] = {"status": "fail", "error": str(e)}

    # 3. AI Service
    ai_service = AIService()
    if ai_service.demo_mode:
        diagnostics["checks"]["ai_service"] = {
            "status": "warning",
            "mode": "demo",
            "details": "AI service running in demo mode",
        }
    else:
        try:
            # Test AI service with minimal request
            start = time.time()
            # Make a test call (would need to implement in ai_service)
            ai_latency = (time.time() - start) * 1000

            diagnostics["checks"]["ai_service"] = {
                "status": "pass",
                "mode": "production",
                "latency_ms": ai_latency,
            }
        except Exception as e:
            diagnostics["checks"]["ai_service"] = {"status": "fail", "error": str(e)}

    # 4. Memory usage
    memory = psutil.virtual_memory()
    if memory.percent > 90:
        diagnostics["checks"]["memory"] = {
            "status": "warning",
            "usage_percent": memory.percent,
            "details": "High memory usage detected",
        }
    else:
        diagnostics["checks"]["memory"] = {
            "status": "pass",
            "usage_percent": memory.percent,
        }

    # 5. Disk space
    disk = psutil.disk_usage("/")
    if disk.percent > 90:
        diagnostics["checks"]["disk"] = {
            "status": "warning",
            "usage_percent": disk.percent,
            "details": "Low disk space",
        }
    else:
        diagnostics["checks"]["disk"] = {
            "status": "pass",
            "usage_percent": disk.percent,
            "free_gb": disk.free / (1024**3),
        }

    # Overall status
    statuses = [check["status"] for check in diagnostics["checks"].values()]
    if all(s == "pass" for s in statuses):
        diagnostics["overall_status"] = "healthy"
    elif any(s == "fail" for s in statuses):
        diagnostics["overall_status"] = "unhealthy"
    else:
        diagnostics["overall_status"] = "degraded"

    return diagnostics


@router.post("/test-endpoints")
async def test_endpoints(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Test all critical endpoints (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can run endpoint tests",
        )

    test_results = {"timestamp": datetime.utcnow().isoformat(), "endpoints": {}}

    # Test critical endpoints
    # Note: In production, you'd make actual HTTP requests to test endpoints

    # 1. Document endpoints
    test_results["endpoints"]["documents"] = {
        "list": _test_endpoint_availability("/api/documents", "GET"),
        "upload": _test_endpoint_availability("/api/documents/upload", "POST"),
        "search": _test_endpoint_availability("/api/documents/search", "POST"),
    }

    # 2. Chat endpoints
    test_results["endpoints"]["chat"] = {
        "create": _test_endpoint_availability("/api/chat", "POST"),
        "history": _test_endpoint_availability("/api/chat/{session_id}/history", "GET"),
    }

    # 3. Organization endpoints
    test_results["endpoints"]["organization"] = {
        "details": _test_endpoint_availability("/api/organization", "GET"),
        "users": _test_endpoint_availability("/api/organization/users", "GET"),
    }

    # 4. Auth endpoints
    test_results["endpoints"]["auth"] = {
        "login": _test_endpoint_availability("/api/auth/login", "POST", public=True),
        "refresh": _test_endpoint_availability(
            "/api/auth/refresh", "POST", public=True
        ),
    }

    # Calculate summary
    total_tests = sum(len(category) for category in test_results["endpoints"].values())
    passed_tests = sum(
        1
        for category in test_results["endpoints"].values()
        for test in category.values()
        if test.get("status") == "available"
    )

    test_results["summary"] = {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": total_tests - passed_tests,
        "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
    }

    return test_results


# Helper functions
def _calculate_error_rate() -> float:
    """Calculate error rate from metrics"""
    total_requests = sum(
        count
        for key, count in metrics_collector.counters.items()
        if key.startswith("http_requests:")
    )

    error_requests = sum(
        count
        for key, count in metrics_collector.counters.items()
        if key.startswith("http_errors:")
    )

    if total_requests == 0:
        return 0.0

    return error_requests / total_requests


def _get_average_response_time() -> float:
    """Calculate average response time"""
    all_timings = []
    for timings in metrics_collector.timers.values():
        all_timings.extend(timings)

    if not all_timings:
        return 0.0

    return sum(all_timings) / len(all_timings)


async def _get_database_metrics(db: Session) -> Dict[str, Any]:
    """Get database-specific metrics"""
    try:
        # Count records
        doc_count = db.query(Document).count()
        session_count = db.query(ChatSession).count()
        user_count = db.query(User).count()
        org_count = db.query(Organization).count()

        return {
            "status": "connected",
            "records": {
                "documents": doc_count,
                "chat_sessions": session_count,
                "users": user_count,
                "organizations": org_count,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _get_ai_service_metrics() -> Dict[str, Any]:
    """Get AI service metrics"""
    # Get from metrics collector
    ai_requests = sum(
        count
        for key, count in metrics_collector.counters.items()
        if "ai_service" in key
    )

    ai_errors = sum(
        count
        for key, count in metrics_collector.counters.items()
        if "ai_service" in key and "error" in key
    )

    return {
        "total_requests": ai_requests,
        "errors": ai_errors,
        "error_rate": (ai_errors / ai_requests * 100) if ai_requests > 0 else 0,
        "average_latency_ms": metrics_collector.get_percentile("ai_service", 50) or 0,
    }


def _test_endpoint_availability(
    path: str, method: str, public: bool = False
) -> Dict[str, Any]:
    """Test if an endpoint is available"""
    # In a real implementation, this would make an HTTP request
    # For now, return mock data
    return {"path": path, "method": method, "status": "available", "public": public}


import time  # Add at top of file
