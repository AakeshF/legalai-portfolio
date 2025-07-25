# services/hybrid_ai_service.py - Hybrid AI service supporting cloud and local LLMs
import os
import httpx
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import logging

from services.ollama_service import (
    OllamaService as AIService,
    LegalDocumentType,
    RiskLevel,
)

logger = logging.getLogger(__name__)


class AIBackend(str, Enum):
    """Available AI backends"""

    CLOUD = "cloud"  # Cloud AI API
    LOCAL = "local"  # Local LLM (Ollama, LocalAI, etc.)
    AUTO = "auto"  # Automatic selection with fallback


class LocalLLMClient:
    """
    Client for OpenAI-compatible local LLM APIs (Ollama, LocalAI, etc.)
    Supports the same legal analysis capabilities as cloud API
    """

    def __init__(
        self, endpoint: str = None, model: str = None, api_key: Optional[str] = None
    ):
        self.endpoint = endpoint or os.getenv(
            "LOCAL_LLM_ENDPOINT", "http://localhost:11434"
        )
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "llama2")
        self.api_key = api_key  # Some local deployments may require auth

        # For Ollama compatibility
        if "11434" in self.endpoint:
            self.api_path = "/api/chat"
            self.is_ollama = True
        else:
            # OpenAI-compatible endpoint
            self.api_path = "/v1/chat/completions"
            self.is_ollama = False

        self.timeout = httpx.Timeout(120.0, connect=10.0)
        logger.info(
            f"LocalLLMClient initialized - Endpoint: {self.endpoint}, Model: {self.model}"
        )

    async def check_health(self) -> Tuple[bool, Optional[str]]:
        """Check if local LLM is available"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                if self.is_ollama:
                    # Ollama health check
                    response = await client.get(f"{self.endpoint}/api/tags")
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        model_names = [m.get("name", "").split(":")[0] for m in models]
                        if self.model in model_names:
                            return True, None
                        else:
                            return (
                                False,
                                f"Model {self.model} not found. Available: {model_names}",
                            )
                else:
                    # OpenAI-compatible health check
                    response = await client.get(f"{self.endpoint}/models")
                    if response.status_code == 200:
                        return True, None

                return False, f"Health check failed: {response.status_code}"

        except Exception as e:
            return False, f"Connection error: {str(e)}"

    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4000,
    ) -> str:
        """Generate completion from local LLM"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if self.is_ollama:
            # Ollama format
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
        else:
            # OpenAI-compatible format
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.endpoint}{self.api_path}", json=payload, headers=headers
            )

            if response.status_code != 200:
                raise Exception(
                    f"Local LLM error: {response.status_code} - {response.text}"
                )

            result = response.json()

            if self.is_ollama:
                return result.get("message", {}).get("content", "")
            else:
                # OpenAI format
                return (
                    result.get("choices", [{}])[0].get("message", {}).get("content", "")
                )


class HybridAIService(AIService):
    """
    Enhanced AI service supporting both cloud and local LLM backends
    Maintains all existing legal domain expertise while adding flexibility
    """

    def __init__(self):
        # Initialize parent AI service
        super().__init__()

        # Local LLM client (lazy initialized)
        self._local_client = None

        # Backend health status cache
        self._backend_health = {
            AIBackend.CLOUD: {"healthy": True, "last_check": None, "error": None},
            AIBackend.LOCAL: {"healthy": False, "last_check": None, "error": None},
        }

        # Performance metrics by backend
        self._backend_metrics = {
            AIBackend.CLOUD: {"requests": 0, "errors": 0, "avg_latency": 0},
            AIBackend.LOCAL: {"requests": 0, "errors": 0, "avg_latency": 0},
        }

    def _get_local_client(self, organization) -> LocalLLMClient:
        """Get or create local LLM client for organization"""
        if not self._local_client and organization.local_llm_endpoint:
            self._local_client = LocalLLMClient(
                endpoint=organization.local_llm_endpoint,
                model=organization.local_llm_model or "llama2",
            )
        elif not self._local_client:
            # Use default local LLM settings
            self._local_client = LocalLLMClient()

        return self._local_client

    async def process_chat_message(
        self,
        message: str,
        documents: List[Any],
        chat_history: List[Dict[str, str]] = None,
        analysis_type: str = "general",
        organization: Any = None,  # Organization object for backend selection
    ) -> Dict[str, Any]:
        """
        Process chat message with hybrid backend support
        Maintains all existing legal analysis capabilities
        """
        # Determine which backend to use
        backend = self._select_backend(organization)

        logger.info(f"Processing with backend: {backend}")

        # Start timing
        start_time = time.time()

        try:
            # Use existing query classification and metadata optimization
            query_type = self._classify_query(message)

            # Check for metadata-based instant response (works with any backend)
            if (
                query_type in ["parties", "dates", "amounts", "obligations"]
                and documents
            ):
                metadata_response = await self._search_metadata(
                    query_type, message, documents
                )
                if metadata_response:
                    return self._add_performance_metrics(
                        metadata_response, start_time, backend
                    )

            # Route to appropriate backend
            if backend == AIBackend.LOCAL:
                response = await self._process_with_local_llm(
                    message, documents, chat_history, analysis_type, organization
                )
            else:  # CLOUD or AUTO with cloud selection
                response = await self._process_with_cloud(
                    message, documents, chat_history, analysis_type
                )

            # Add backend info to response
            response["backend_used"] = backend
            return self._add_performance_metrics(response, start_time, backend)

        except Exception as e:
            logger.error(f"Error with {backend} backend: {e}")

            # Try fallback if enabled
            if (
                backend == AIBackend.LOCAL
                and organization
                and organization.ai_fallback_enabled
            ):
                logger.info("Attempting cloud fallback...")
                try:
                    response = await self._process_with_cloud(
                        message, documents, chat_history, analysis_type
                    )
                    response["backend_used"] = AIBackend.CLOUD
                    response["fallback_used"] = True
                    return self._add_performance_metrics(
                        response, start_time, AIBackend.CLOUD
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")

            # If all fails, return error response
            return {
                "answer": "I apologize, but I'm currently unable to process your request. Please try again later.",
                "sources": [],
                "error": str(e),
                "backend_used": backend,
            }

    def _select_backend(self, organization) -> AIBackend:
        """Select appropriate backend based on organization settings"""
        if not organization:
            return AIBackend.CLOUD

        backend_pref = organization.ai_backend or AIBackend.CLOUD

        if backend_pref == AIBackend.AUTO:
            # Auto mode: prefer local if available, fallback to cloud
            if self._is_backend_healthy(AIBackend.LOCAL):
                return AIBackend.LOCAL
            else:
                return AIBackend.CLOUD

        return backend_pref

    async def _process_with_local_llm(
        self,
        message: str,
        documents: List[Any],
        chat_history: List[Dict[str, str]],
        analysis_type: str,
        organization: Any,
    ) -> Dict[str, Any]:
        """Process request with local LLM"""
        # Get local client
        local_client = self._get_local_client(organization)

        # Check health
        healthy, error = await local_client.check_health()
        if not healthy:
            raise Exception(f"Local LLM unavailable: {error}")

        # Build context using existing methods
        document_context = self._build_enhanced_document_context(
            documents, self._classify_query(message)
        )

        # Use same system prompts as cloud
        messages = self._build_conversation_context(
            message,
            document_context,
            chat_history,
            self._detect_analysis_type(documents),
        )

        # Get completion from local LLM
        answer = await local_client.generate_completion(messages)

        # Extract sources from answer (local LLMs may format differently)
        sources = self._extract_sources_from_text(answer, documents)

        return {
            "answer": answer,
            "sources": sources,
            "model": f"local/{local_client.model}",
            "analysis_type": analysis_type,
        }

    async def _process_with_cloud(
        self,
        message: str,
        documents: List[Any],
        chat_history: List[Dict[str, str]],
        analysis_type: str,
    ) -> Dict[str, Any]:
        """Process with Cloud AI API (existing functionality)"""
        # Use parent class implementation
        return await super().process_chat_message(
            message, documents, chat_history, analysis_type
        )

    def _is_backend_healthy(self, backend: AIBackend) -> bool:
        """Check if backend is healthy (with caching)"""
        health_info = self._backend_health[backend]

        # Check cache (5 minute TTL)
        if health_info["last_check"]:
            age = (datetime.utcnow() - health_info["last_check"]).total_seconds()
            if age < 300:  # 5 minutes
                return health_info["healthy"]

        # Perform health check asynchronously in background
        asyncio.create_task(self._update_backend_health(backend))

        # Return last known status
        return health_info["healthy"]

    async def _update_backend_health(self, backend: AIBackend):
        """Update backend health status"""
        try:
            if backend == AIBackend.LOCAL:
                if self._local_client:
                    healthy, error = await self._local_client.check_health()
                    self._backend_health[backend] = {
                        "healthy": healthy,
                        "last_check": datetime.utcnow(),
                        "error": error,
                    }
            elif backend == AIBackend.CLOUD:
                # Simple check for Cloud API
                self._backend_health[backend] = {
                    "healthy": not self.demo_mode,
                    "last_check": datetime.utcnow(),
                    "error": "No API key" if self.demo_mode else None,
                }
        except Exception as e:
            self._backend_health[backend] = {
                "healthy": False,
                "last_check": datetime.utcnow(),
                "error": str(e),
            }

    def _add_performance_metrics(
        self, response: Dict[str, Any], start_time: float, backend: AIBackend
    ) -> Dict[str, Any]:
        """Add performance metrics to response"""
        latency = (time.time() - start_time) * 1000

        # Update backend metrics
        metrics = self._backend_metrics[backend]
        metrics["requests"] += 1
        metrics["avg_latency"] = (
            metrics["avg_latency"] * (metrics["requests"] - 1) + latency
        ) / metrics["requests"]

        # Add to response
        if "performance_metrics" not in response:
            response["performance_metrics"] = {}

        response["performance_metrics"].update(
            {
                "backend": backend,
                "latency_ms": latency,
                "backend_health": self._backend_health[backend]["healthy"],
            }
        )

        return response

    def _extract_sources_from_text(
        self, answer: str, documents: List[Any]
    ) -> List[str]:
        """Extract document references from answer text"""
        sources = []

        # Look for document references in the answer
        for doc in documents:
            if doc.filename in answer or doc.id in answer:
                sources.append(f"{doc.filename} (ID: {doc.id})")

        return sources

    def _detect_analysis_type(self, documents: List[Any]) -> str:
        """Detect document type for analysis (reuse parent logic)"""
        if not documents:
            return "general"

        # Use first document's type if available
        first_doc = documents[0]
        if hasattr(first_doc, "legal_metadata") and first_doc.legal_metadata:
            try:
                metadata = json.loads(first_doc.legal_metadata)
                return metadata.get("document_type", "general")
            except:
                pass

        return "general"

    async def get_backend_status(self) -> Dict[str, Any]:
        """Get status of all backends"""
        # Update health checks
        await self._update_backend_health(AIBackend.CLOUD)
        if self._local_client:
            await self._update_backend_health(AIBackend.LOCAL)

        return {
            "backends": {
                "cloud": {
                    "available": self._backend_health[AIBackend.CLOUD]["healthy"],
                    "provider": "Cloud AI",
                    "model": self.model,
                    **self._backend_metrics[AIBackend.CLOUD],
                },
                "local": {
                    "available": self._backend_health[AIBackend.LOCAL]["healthy"],
                    "endpoint": (
                        self._local_client.endpoint if self._local_client else None
                    ),
                    "model": self._local_client.model if self._local_client else None,
                    **self._backend_metrics[AIBackend.LOCAL],
                },
            },
            "default_backend": AIBackend.CLOUD,
        }


# Global instance
hybrid_ai_service = HybridAIService()
