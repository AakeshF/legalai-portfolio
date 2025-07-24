# services/mcp_servers/base_legal_mcp.py - Base class for legal MCP servers

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiohttp
import asyncio
import logging
from dataclasses import dataclass
import json
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with expiration"""
    data: Any
    expires_at: datetime
    hit_count: int = 0

class BaseLegalMCPServer(ABC):
    """Base class for all legal-specific MCP servers"""
    
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.retry_config = {
            "max_retries": 3,
            "initial_delay": 1,  # seconds
            "max_delay": 60,
            "exponential_base": 2
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    @abstractmethod
    async def query(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a query action with parameters"""
        pass
        
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities and supported actions"""
        pass
        
    def _generate_cache_key(self, action: str, params: Dict[str, Any]) -> str:
        """Generate a cache key from action and params"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(f"{action}:{param_str}".encode()).hexdigest()
        
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if not expired"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if entry.expires_at > datetime.utcnow():
                entry.hit_count += 1
                logger.debug(f"Cache hit for key {cache_key[:8]}... (hits: {entry.hit_count})")
                return entry.data
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logger.debug(f"Cache expired for key {cache_key[:8]}...")
        return None
        
    def _cache_result(self, cache_key: str, data: Any, ttl_minutes: int = 60):
        """Cache a result with TTL"""
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        self.cache[cache_key] = CacheEntry(data=data, expires_at=expires_at)
        logger.debug(f"Cached result for key {cache_key[:8]}... (TTL: {ttl_minutes} min)")
        
    def _clean_expired_cache(self):
        """Remove expired cache entries"""
        now = datetime.utcnow()
        expired_keys = [k for k, v in self.cache.items() if v.expires_at <= now]
        for key in expired_keys:
            del self.cache[key]
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
            
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry"""
        last_exception = None
        delay = self.retry_config["initial_delay"]
        
        for attempt in range(self.retry_config["max_retries"]):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.retry_config["max_retries"] - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay = min(delay * self.retry_config["exponential_base"], 
                              self.retry_config["max_delay"])
                    
        logger.error(f"All retry attempts failed: {str(last_exception)}")
        raise last_exception
        
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        async def _request():
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
                
        return await self._retry_with_backoff(_request)
        
    def validate_params(self, params: Dict[str, Any], required: List[str]) -> None:
        """Validate required parameters"""
        missing = [p for p in required if p not in params]
        if missing:
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")
            
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input for security"""
        # Remove potential SQL injection attempts
        dangerous_patterns = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
        sanitized = text
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, "")
        return sanitized.strip()