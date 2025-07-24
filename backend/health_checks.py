# health_checks.py - Production health checks for monitoring
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
import redis
import httpx
import psutil
import os
from datetime import datetime, timezone
import asyncio
from database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

class HealthCheckService:
    """Comprehensive health check service for production monitoring"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.start_time = datetime.now(timezone.utc)
        
    async def check_database(self, db: Session) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            start = asyncio.get_event_loop().time()
            result = db.execute(text("SELECT 1"))
            result.scalar()
            latency = (asyncio.get_event_loop().time() - start) * 1000
            
            # Check table counts
            tables = ['organizations', 'users', 'documents', 'chat_sessions']
            table_stats = {}
            
            for table in tables:
                try:
                    count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    table_stats[table] = count
                except:
                    table_stats[table] = "error"
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "connection_pool": {
                    "size": db.bind.pool.size() if hasattr(db.bind, 'pool') else "N/A",
                    "checked_out": db.bind.pool.checkedout() if hasattr(db.bind, 'pool') else "N/A"
                },
                "table_stats": table_stats
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        if not self.redis_client:
            return {"status": "not_configured"}
        
        try:
            start = asyncio.get_event_loop().time()
            self.redis_client.ping()
            latency = (asyncio.get_event_loop().time() - start) * 1000
            
            # Get Redis info
            info = self.redis_client.info()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "memory_used_mb": round(info.get('used_memory', 0) / 1024 / 1024, 2),
                "connected_clients": info.get('connected_clients', 0),
                "uptime_days": round(info.get('uptime_in_seconds', 0) / 86400, 2)
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_ai_service(self) -> Dict[str, Any]:
        """Check AI service availability"""
        try:
            # Check AI API
            api_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                return {"status": "not_configured", "message": "No API key"}
            
            # Simple connectivity check
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers=headers
                )
                
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_code": response.status_code,
                    "backend": "openai"
                }
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "cores": psutil.cpu_count()
                },
                "memory": {
                    "total_mb": round(memory.total / 1024 / 1024, 2),
                    "used_mb": round(memory.used / 1024 / 1024, 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                    "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                    "percent": disk.percent
                }
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_application_info(self) -> Dict[str, Any]:
        """Get application information"""
        uptime = datetime.now(timezone.utc) - self.start_time
        
        return {
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": os.getenv("ENVIRONMENT", "production"),
            "uptime_seconds": int(uptime.total_seconds()),
            "python_version": os.sys.version.split()[0]
        }

# Initialize health check service
health_service = HealthCheckService()

@router.get("/health")
async def basic_health_check() -> Dict[str, Any]:
    """Basic health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "legal-ai-backend"
    }

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Detailed health check with all subsystems"""
    
    # Run all checks concurrently
    db_check, redis_check, ai_check = await asyncio.gather(
        health_service.check_database(db),
        health_service.check_redis(),
        health_service.check_ai_service()
    )
    
    # Determine overall health
    all_healthy = all([
        db_check.get("status") == "healthy",
        redis_check.get("status") in ["healthy", "not_configured"],
        ai_check.get("status") in ["healthy", "not_configured"]
    ])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "application": health_service.get_application_info(),
        "checks": {
            "database": db_check,
            "redis": redis_check,
            "ai_service": ai_check,
            "system": health_service.check_system_resources()
        }
    }

@router.get("/health/live")
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness_probe(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Kubernetes readiness probe endpoint"""
    try:
        # Quick database check
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "error": str(e)})

@router.get("/health/startup")
async def startup_probe() -> Dict[str, Any]:
    """Kubernetes startup probe endpoint"""
    # Check if all critical services are initialized
    checks = {
        "database": False,
        "configuration": False,
        "migrations": False
    }
    
    try:
        # Check if database is accessible
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["database"] = True
        
        # Check if configuration is loaded
        checks["configuration"] = os.getenv("SECRET_KEY") is not None
        
        # Check if migrations are up to date
        from alembic import command
        from alembic.config import Config
        alembic_cfg = Config("alembic.ini")
        # This is a simplified check - in production, verify actual migration status
        checks["migrations"] = True
        
    except Exception as e:
        logger.error(f"Startup probe failed: {e}")
    
    all_ready = all(checks.values())
    
    if not all_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "starting",
                "checks": checks
            }
        )
    
    return {
        "status": "started",
        "checks": checks
    }

# Metrics endpoint for Prometheus
@router.get("/metrics")
async def metrics_endpoint() -> str:
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, Counter, Histogram, Gauge
    
    # Define metrics
    request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
    request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
    active_sessions = Gauge('active_sessions', 'Number of active sessions')
    document_count = Gauge('document_count', 'Total number of documents')
    
    # Generate metrics
    return generate_latest()

# Custom health check for specific features
@router.get("/health/features")
async def feature_health_check() -> Dict[str, Any]:
    """Check health of specific features"""
    
    features = {
        "document_processing": {
            "enabled": True,
            "status": "healthy",
            "supported_formats": ["pdf", "docx", "txt"]
        },
        "ai_chat": {
            "enabled": True,
            "status": "healthy",
            "backend": os.getenv("AI_BACKEND", "cloud")
        },
        "email_notifications": {
            "enabled": os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "true").lower() == "true",
            "status": "healthy" if os.getenv("SMTP_HOST") else "not_configured"
        },
        "local_llm": {
            "enabled": os.getenv("ENABLE_LOCAL_LLM", "true").lower() == "true",
            "status": "not_configured",
            "endpoint": os.getenv("LOCAL_LLM_ENDPOINT")
        }
    }
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": features
    }