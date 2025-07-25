# services/local_only_ai_service.py - Local-only AI service (no external APIs)
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


class LocalOnlyAIService:
    """AI service that only uses local models - no external API calls"""

    def __init__(self):
        self.ollama_service = OllamaService()
        self.provider = "local"
        logger.info(
            "LocalOnlyAIService initialized - all AI processing happens locally"
        )

    async def process_chat_message(self, *args, **kwargs):
        """Process chat message using local Ollama"""
        return await self.ollama_service.process_chat_message(*args, **kwargs)

    async def analyze_document(self, *args, **kwargs):
        """Analyze document using local Ollama"""
        return await self.ollama_service.analyze_document(*args, **kwargs)

    async def compare_documents(self, *args, **kwargs):
        """Compare documents using local Ollama"""
        return await self.ollama_service.compare_documents(*args, **kwargs)

    async def extract_key_terms(self, *args, **kwargs):
        """Extract key terms using local Ollama"""
        return await self.ollama_service.extract_key_terms(*args, **kwargs)

    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": "local",
            "model": self.ollama_service.model,
            "base_url": self.ollama_service.base_url,
            "is_available": self.ollama_service.is_available,
            "privacy": "100% local - no data leaves this machine",
        }


# Create global instance
local_only_ai_service = LocalOnlyAIService()
