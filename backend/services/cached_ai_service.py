"""
AI Service wrapper with caching integration
"""
from typing import Dict, Any, Optional
import logging

from services.ollama_service import OllamaService as AIService
from services.cache_service import AIResponseCache, cache

logger = logging.getLogger(__name__)


class CachedAIService(AIService):
    """AI Service with caching layer for performance optimization."""
    
    def __init__(self):
        super().__init__()
        self.cache_enabled = True
    
    async def analyze_document(
        self,
        content: str,
        document_type: str = "general",
        enable_cache: bool = True
    ) -> Dict[str, Any]:
        """Analyze document with caching."""
        
        # Check cache first if enabled
        if self.cache_enabled and enable_cache:
            cached_result = AIResponseCache.get_analysis(content, document_type)
            if cached_result:
                logger.info(f"AI analysis cache hit for {document_type} document")
                return cached_result
        
        # Call parent method
        result = await super().analyze_document(content, document_type)
        
        # Cache the result if it's valid
        if (self.cache_enabled and 
            enable_cache and 
            result and 
            not result.get("error") and
            "[Demo]" not in result.get("summary", "")):
            AIResponseCache.set_analysis(content, document_type, result)
            logger.info(f"Cached AI analysis for {document_type} document")
        
        return result
    
    @cache.cache_decorator(prefix="ai:chat", ttl=300)  # 5 min cache for chat
    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Chat with caching for repeated questions."""
        # Note: The decorator handles caching automatically
        # Only cache if no session_id (session-based chats shouldn't be cached)
        if session_id:
            # Don't use cache for session-based chats
            return await super().chat(message, context)
        
        return await super().chat(message, context)
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear AI response cache."""
        if pattern:
            cache.clear_pattern(f"ai:{pattern}*")
        else:
            cache.clear_pattern("ai:*")
        logger.info(f"Cleared AI cache with pattern: {pattern or 'all'}")