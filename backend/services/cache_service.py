"""
Redis caching service for performance optimization
"""
import json
import hashlib
from typing import Optional, Any, Union
from datetime import timedelta
import redis
from redis.exceptions import RedisError
import logging
from functools import wraps
import pickle

from config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service with fallback to memory cache."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url or "redis://localhost:6379/0"
        self.redis_client = None
        self.memory_cache = {}  # Fallback memory cache
        self._connect()
    
    def _connect(self):
        """Connect to Redis with error handling."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We'll handle encoding/decoding
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis cache")
        except (RedisError, Exception) as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using memory cache.")
            self.redis_client = None
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments."""
        # Create a unique key from arguments
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_hash = hashlib.md5(
            json.dumps(key_data, sort_keys=True).encode()
        ).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return pickle.loads(value)
            else:
                # Fallback to memory cache
                return self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL (in seconds)."""
        try:
            serialized = pickle.dumps(value)
            
            if self.redis_client:
                if ttl:
                    self.redis_client.setex(key, ttl, serialized)
                else:
                    self.redis_client.set(key, serialized)
            else:
                # Fallback to memory cache
                self.memory_cache[key] = value
                # Simple memory cache size limit
                if len(self.memory_cache) > 1000:
                    # Remove oldest entries
                    for k in list(self.memory_cache.keys())[:100]:
                        del self.memory_cache[k]
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def delete(self, key: str):
        """Delete value from cache."""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self.memory_cache.pop(key, None)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            else:
                # Memory cache pattern matching
                keys_to_delete = [k for k in self.memory_cache.keys() if pattern.replace("*", "") in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
    
    def cache_decorator(self, prefix: str, ttl: int = 3600):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._make_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached
                
                # Call function and cache result
                result = await func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._make_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached
                
                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator


# Global cache instance
cache = CacheService()


# Cache key generators for different resources
class CacheKeys:
    """Standard cache key generators."""
    
    @staticmethod
    def document(doc_id: int, org_id: int) -> str:
        return f"doc:{org_id}:{doc_id}"
    
    @staticmethod
    def document_list(org_id: int, skip: int = 0, limit: int = 100) -> str:
        return f"docs:list:{org_id}:{skip}:{limit}"
    
    @staticmethod
    def ai_analysis(content_hash: str, doc_type: str) -> str:
        return f"ai:analysis:{doc_type}:{content_hash}"
    
    @staticmethod
    def chat_session(session_id: str) -> str:
        return f"chat:session:{session_id}"
    
    @staticmethod
    def chat_history(session_id: str) -> str:
        return f"chat:history:{session_id}"
    
    @staticmethod
    def user_sessions(user_id: int) -> str:
        return f"user:sessions:{user_id}"
    
    @staticmethod
    def org_stats(org_id: int) -> str:
        return f"org:stats:{org_id}"


# Specialized cache managers
class DocumentCache:
    """Document-specific caching operations."""
    
    @staticmethod
    def get_document(doc_id: int, org_id: int) -> Optional[dict]:
        """Get cached document."""
        key = CacheKeys.document(doc_id, org_id)
        return cache.get(key)
    
    @staticmethod
    def set_document(doc_id: int, org_id: int, doc_data: dict, ttl: int = 3600):
        """Cache document data."""
        key = CacheKeys.document(doc_id, org_id)
        cache.set(key, doc_data, ttl)
    
    @staticmethod
    def invalidate_document(doc_id: int, org_id: int):
        """Invalidate document cache."""
        # Clear specific document
        cache.delete(CacheKeys.document(doc_id, org_id))
        # Clear document lists for this org
        cache.clear_pattern(f"docs:list:{org_id}:*")
    
    @staticmethod
    def get_document_list(org_id: int, skip: int = 0, limit: int = 100) -> Optional[list]:
        """Get cached document list."""
        key = CacheKeys.document_list(org_id, skip, limit)
        return cache.get(key)
    
    @staticmethod
    def set_document_list(org_id: int, docs: list, skip: int = 0, limit: int = 100, ttl: int = 300):
        """Cache document list (shorter TTL)."""
        key = CacheKeys.document_list(org_id, skip, limit)
        cache.set(key, docs, ttl)


class AIResponseCache:
    """AI response caching with content-based keys."""
    
    @staticmethod
    def _content_hash(content: str) -> str:
        """Generate hash of content for cache key."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def get_analysis(content: str, doc_type: str) -> Optional[dict]:
        """Get cached AI analysis."""
        content_hash = AIResponseCache._content_hash(content)
        key = CacheKeys.ai_analysis(content_hash, doc_type)
        return cache.get(key)
    
    @staticmethod
    def set_analysis(content: str, doc_type: str, analysis: dict, ttl: int = 86400):
        """Cache AI analysis (24 hour TTL)."""
        content_hash = AIResponseCache._content_hash(content)
        key = CacheKeys.ai_analysis(content_hash, doc_type)
        cache.set(key, analysis, ttl)
    
    @staticmethod
    def should_cache_response(response: Union[str, dict]) -> bool:
        """Determine if AI response should be cached."""
        # Don't cache error responses
        if isinstance(response, dict) and response.get("error"):
            return False
        if isinstance(response, str) and "error" in response.lower():
            return False
        return True


class SessionCache:
    """User session caching."""
    
    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """Get cached session data."""
        key = CacheKeys.chat_session(session_id)
        return cache.get(key)
    
    @staticmethod
    def set_session(session_id: str, session_data: dict, ttl: int = 1800):
        """Cache session data (30 min TTL)."""
        key = CacheKeys.chat_session(session_id)
        cache.set(key, session_data, ttl)
    
    @staticmethod
    def get_chat_history(session_id: str) -> Optional[list]:
        """Get cached chat history."""
        key = CacheKeys.chat_history(session_id)
        return cache.get(key)
    
    @staticmethod
    def set_chat_history(session_id: str, messages: list, ttl: int = 1800):
        """Cache chat history."""
        key = CacheKeys.chat_history(session_id)
        cache.set(key, messages, ttl)
    
    @staticmethod
    def invalidate_session(session_id: str):
        """Invalidate all session-related caches."""
        cache.delete(CacheKeys.chat_session(session_id))
        cache.delete(CacheKeys.chat_history(session_id))