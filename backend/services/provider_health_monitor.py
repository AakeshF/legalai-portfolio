# services/provider_health_monitor.py - AI Provider health monitoring
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
import logging
from sqlalchemy import Column, String, DateTime, Float, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

Base = declarative_base()

class ProviderHealthStatus(Base):
    """Track health status of AI providers"""
    __tablename__ = "provider_health_status"
    
    id = Column(Integer, primary_key=True)
    provider = Column(String(50), unique=True, nullable=False)
    status = Column(String(20))  # healthy, degraded, unhealthy, down
    last_check = Column(DateTime, default=datetime.utcnow)
    response_time_ms = Column(Float)
    success_rate_24h = Column(Float)
    total_requests_24h = Column(Integer)
    failed_requests_24h = Column(Integer)
    last_error = Column(String(500))
    consecutive_failures = Column(Integer, default=0)
    
class ProviderHealthMonitor:
    """Monitor health and performance of AI providers"""
    
    def __init__(self, db: Session):
        self.db = db
        self.check_interval = 300  # 5 minutes
        self.providers = {
            "openai": {
                "health_endpoint": "https://api.openai.com/v1/models",
                "headers": lambda key: {"Authorization": f"Bearer {key}"}
            },
            "claude": {
                "health_endpoint": "https://api.anthropic.com/v1/messages",
                "headers": lambda key: {"x-api-key": key, "anthropic-version": "2023-06-01"}
            },
            "gemini": {
                "health_endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
                "headers": lambda key: {}  # API key in URL for Gemini
            }
        }
        
    async def check_provider_health(
        self, 
        provider: str, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check health of a specific provider"""
        
        if provider not in self.providers:
            return {
                "provider": provider,
                "status": "unknown",
                "error": "Provider not supported"
            }
        
        start_time = time.time()
        config = self.providers[provider]
        
        try:
            # Build request
            url = config["health_endpoint"]
            if provider == "gemini" and api_key:
                url += f"?key={api_key}"
            
            headers = config["headers"](api_key) if api_key else {}
            
            # Make health check request
            async with httpx.AsyncClient(timeout=10.0) as client:
                if provider == "claude":
                    # Claude requires a minimal message
                    response = await client.post(
                        url,
                        headers=headers,
                        json={
                            "model": "claude-3-haiku-20240307",
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 1
                        }
                    )
                else:
                    response = await client.get(url, headers=headers)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            # Determine health status
            if response.status_code in [200, 201]:
                status = "healthy"
                error = None
            elif response.status_code == 401:
                status = "unhealthy"
                error = "Invalid API key"
            elif response.status_code == 429:
                status = "degraded"
                error = "Rate limited"
            elif response.status_code >= 500:
                status = "down"
                error = f"Server error: {response.status_code}"
            else:
                status = "unhealthy"
                error = f"HTTP {response.status_code}"
            
            # Update database
            self._update_health_status(
                provider=provider,
                status=status,
                response_time=response_time,
                error=error
            )
            
            return {
                "provider": provider,
                "status": status,
                "response_time_ms": round(response_time, 2),
                "checked_at": datetime.utcnow().isoformat(),
                "error": error
            }
            
        except asyncio.TimeoutError:
            self._update_health_status(
                provider=provider,
                status="down",
                response_time=10000,  # Timeout
                error="Request timeout"
            )
            return {
                "provider": provider,
                "status": "down",
                "error": "Request timeout",
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self._update_health_status(
                provider=provider,
                status="down",
                response_time=None,
                error=str(e)
            )
            return {
                "provider": provider,
                "status": "down",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
    
    def _update_health_status(
        self,
        provider: str,
        status: str,
        response_time: Optional[float],
        error: Optional[str]
    ):
        """Update health status in database"""
        
        health_record = self.db.query(ProviderHealthStatus).filter_by(
            provider=provider
        ).first()
        
        if not health_record:
            health_record = ProviderHealthStatus(provider=provider)
            self.db.add(health_record)
        
        # Update status
        health_record.status = status
        health_record.last_check = datetime.utcnow()
        health_record.response_time_ms = response_time
        health_record.last_error = error
        
        # Update consecutive failures
        if status in ["unhealthy", "down"]:
            health_record.consecutive_failures += 1
        else:
            health_record.consecutive_failures = 0
        
        self.db.commit()
    
    async def check_all_providers(
        self,
        api_keys: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """Check health of all providers"""
        
        results = {}
        tasks = []
        
        for provider in self.providers.keys():
            api_key = api_keys.get(provider)
            task = self.check_provider_health(provider, api_key)
            tasks.append(task)
        
        # Check all providers concurrently
        health_results = await asyncio.gather(*tasks)
        
        for result in health_results:
            results[result["provider"]] = result
        
        return results
    
    def get_provider_statistics(
        self,
        provider: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get provider statistics over time period"""
        
        health_record = self.db.query(ProviderHealthStatus).filter_by(
            provider=provider
        ).first()
        
        if not health_record:
            return {
                "provider": provider,
                "status": "unknown",
                "statistics": None
            }
        
        # Calculate uptime percentage
        # This is simplified - in production, you'd track historical data
        uptime = 100.0
        if health_record.consecutive_failures > 0:
            # Rough estimate based on consecutive failures
            uptime = max(0, 100 - (health_record.consecutive_failures * 5))
        
        return {
            "provider": provider,
            "current_status": health_record.status,
            "last_check": health_record.last_check.isoformat(),
            "statistics": {
                "uptime_percentage": uptime,
                "average_response_time_ms": health_record.response_time_ms,
                "total_requests_24h": health_record.total_requests_24h or 0,
                "failed_requests_24h": health_record.failed_requests_24h or 0,
                "success_rate_24h": health_record.success_rate_24h or 100.0,
                "consecutive_failures": health_record.consecutive_failures
            }
        }
    
    def get_all_provider_status(self) -> List[Dict[str, Any]]:
        """Get current status of all providers"""
        
        all_status = self.db.query(ProviderHealthStatus).all()
        
        return [
            {
                "provider": status.provider,
                "status": status.status,
                "last_check": status.last_check.isoformat() if status.last_check else None,
                "response_time_ms": status.response_time_ms,
                "consecutive_failures": status.consecutive_failures,
                "last_error": status.last_error
            }
            for status in all_status
        ]
    
    async def start_monitoring(
        self,
        api_keys_callback,
        interval: int = 300
    ):
        """Start background monitoring of providers"""
        
        while True:
            try:
                # Get current API keys
                api_keys = await api_keys_callback()
                
                # Check all providers
                await self.check_all_providers(api_keys)
                
                logger.info("Provider health check completed")
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
            
            # Wait for next check
            await asyncio.sleep(interval)