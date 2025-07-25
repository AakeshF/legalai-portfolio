# services/multi_provider_ai_service.py - Multi-provider AI service with support for multiple APIs and local models
import os
import httpx
import json
import re
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Import rate limiter
from services.ai_rate_limiter import ai_rate_limiter


class AIProvider(Enum):
    """Supported AI providers"""

    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    LOCAL = "local"


class BaseAIProvider(ABC):
    """Base class for AI providers"""

    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response from the AI provider"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass

    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        pass


# Note: Removed [AI Provider] provider - can be replaced with any OpenAI-compatible provider


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude AI provider implementation"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com/v1"
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-ant-"))

    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.is_available():
            raise Exception("Claude API key not configured")

        # Convert messages to Claude format
        system_message = ""
        claude_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message += msg["content"] + "\n"
            else:
                claude_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": self.model,
            "messages": claude_messages,
            "system": system_message.strip(),
            "max_tokens": kwargs.get("max_tokens", 4000),
            "temperature": kwargs.get("temperature", 0.1),
        }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/messages", json=payload, headers=headers
            )

            if response.status_code != 200:
                raise Exception(
                    f"Claude API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            return result["content"][0]["text"]

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "name": "Claude",
            "model": self.model,
            "available": self.is_available(),
            "features": [
                "legal_analysis",
                "document_review",
                "chat",
                "advanced_reasoning",
            ],
        }


class OpenAIProvider(BaseAIProvider):
    """OpenAI ChatGPT provider implementation"""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-"))

    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.is_available():
            raise Exception("OpenAI API key not configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4000),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )

            if response.status_code != 200:
                raise Exception(
                    f"OpenAI API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            return result["choices"][0]["message"]["content"]

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "name": "OpenAI",
            "model": self.model,
            "available": self.is_available(),
            "features": ["legal_analysis", "document_review", "chat"],
        }


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider implementation"""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.is_available():
            raise Exception("Google API key not configured")

        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg["role"] == "system":
                # Prepend system message to first user message
                continue
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Add system message to first user message if exists
        system_messages = [
            msg["content"] for msg in messages if msg["role"] == "system"
        ]
        if system_messages and contents:
            contents[0]["parts"][0]["text"] = (
                "\n".join(system_messages) + "\n\n" + contents[0]["parts"][0]["text"]
            )

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.1),
                "maxOutputTokens": kwargs.get("max_tokens", 4000),
            },
        }

        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                raise Exception(
                    f"Gemini API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "name": "Gemini",
            "model": self.model,
            "available": self.is_available(),
            "features": ["legal_analysis", "document_review", "chat", "multimodal"],
        }


class LocalLLMProvider(BaseAIProvider):
    """Local LLM provider using MCP framework"""

    def __init__(self):
        self.mcp_available = self._check_mcp_availability()
        self.model_path = os.getenv("LOCAL_MODEL_PATH", "/models/legal-llama-7b")
        self.model_type = os.getenv("LOCAL_MODEL_TYPE", "llama")

    def _check_mcp_availability(self) -> bool:
        """Check if MCP local model server is available"""
        try:
            # Check if MCP manager is available
            from services.mcp_manager import MCPManager

            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        """Check if local model is available"""
        if not self.mcp_available:
            return False

        # Check if model file exists
        if os.path.exists(self.model_path):
            return True

        # Check if MCP local server is running
        try:
            from services.mcp_manager import MCPManager

            manager = MCPManager()
            servers = manager.list_servers()
            return any(server.get("name") == "local_llm" for server in servers)
        except:
            return False

    async def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.is_available():
            raise Exception(
                "Local LLM not available. Please ensure model is downloaded and MCP server is running."
            )

        try:
            from services.mcp_manager import MCPManager

            manager = MCPManager()

            # Format messages for local model
            prompt = self._format_messages_for_local(messages)

            # Call local model through MCP
            response = await manager.query_tool(
                "local_llm",
                "generate",
                {
                    "prompt": prompt,
                    "max_tokens": kwargs.get("max_tokens", 4000),
                    "temperature": kwargs.get("temperature", 0.1),
                },
            )

            return response.get("text", "")

        except Exception as e:
            logger.error(f"Local LLM error: {e}")
            raise Exception(f"Local LLM generation failed: {str(e)}")

    def _format_messages_for_local(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for local model prompt"""
        prompt = ""

        # Add system messages first
        system_msgs = [msg["content"] for msg in messages if msg["role"] == "system"]
        if system_msgs:
            prompt += "System: " + "\n".join(system_msgs) + "\n\n"

        # Add conversation
        for msg in messages:
            if msg["role"] != "system":
                role = "Human" if msg["role"] == "user" else "Assistant"
                prompt += f"{role}: {msg['content']}\n\n"

        prompt += "Assistant: "
        return prompt

    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "name": "Local LLM",
            "model": self.model_type,
            "available": self.is_available(),
            "features": [
                "legal_analysis",
                "document_review",
                "chat",
                "privacy",
                "offline",
            ],
            "model_path": self.model_path,
        }


class MultiProviderAIService:
    """Enhanced AI service with multi-provider support and fallback capabilities"""

    def __init__(self):
        # Initialize providers
        self.providers = {
            AIProvider.OPENAI: OpenAIProvider(),
            AIProvider.CLAUDE: ClaudeProvider(),
            AIProvider.GEMINI: GeminiProvider(),
            AIProvider.LOCAL: LocalLLMProvider(),
        }

        # Load preferences from config
        self.default_provider = self._get_default_provider()
        self.fallback_order = self._get_fallback_order()

        # Copy legal patterns and prompts from original service
        self.legal_patterns = {
            "dates": r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            "money": r"\$[\d,]+(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)\b",
            "case_citations": r"\b\d+\s+[A-Z][a-z]+\.?\s*(?:2d|3d|4th)?\s*\d+\b",
            "statutes": r"\b\d+\s+U\.?S\.?C\.?\s*§?\s*\d+|§\s*\d+(?:\.\d+)?",
            "parties": r"(?:Plaintiff|Defendant|Petitioner|Respondent|Appellant|Appellee):\s*([A-Z][a-zA-Z\s,]+?)(?:\n|;|,\s*(?:Plaintiff|Defendant))",
        }

        self.system_prompts = {
            "legal_assistant": """You are a professional legal AI assistant designed to help attorneys analyze documents and provide legal insights. 

Your responsibilities:
- Analyze legal documents with precision and attention to detail
- Identify key legal issues, dates, parties, and obligations
- Provide clear, actionable insights for legal professionals
- Cite specific sections of documents when making points
- Flag potential legal risks or compliance issues
- Extract critical information in structured formats
- Identify missing elements or clauses
- Maintain attorney-client privilege and confidentiality

Always provide thorough, professional responses that would be valuable to an experienced attorney."""
        }

        logger.info(
            f"Multi-provider AI service initialized. Default: {self.default_provider.value}"
        )
        logger.info(
            f"Available providers: {[p.value for p, prov in self.providers.items() if prov.is_available()]}"
        )

    def _get_default_provider(self) -> AIProvider:
        """Get default provider from environment or config"""
        provider_name = os.getenv("DEFAULT_AI_PROVIDER", "openai").lower()

        provider_map = {
            "claude": AIProvider.CLAUDE,
            "openai": AIProvider.OPENAI,
            "chatgpt": AIProvider.OPENAI,
            "gemini": AIProvider.GEMINI,
            "local": AIProvider.LOCAL,
        }

        return provider_map.get(provider_name, AIProvider.OPENAI)

    def _get_fallback_order(self) -> List[AIProvider]:
        """Get fallback order from config or use defaults"""
        fallback_str = os.getenv("AI_FALLBACK_ORDER", "claude,openai,gemini,local")

        provider_map = {
            "claude": AIProvider.CLAUDE,
            "openai": AIProvider.OPENAI,
            "chatgpt": AIProvider.OPENAI,
            "gemini": AIProvider.GEMINI,
            "local": AIProvider.LOCAL,
        }

        fallback_order = []
        for name in fallback_str.split(","):
            provider = provider_map.get(name.strip().lower())
            if provider:
                fallback_order.append(provider)

        # Ensure all providers are in the list
        for provider in AIProvider:
            if provider not in fallback_order:
                fallback_order.append(provider)

        return fallback_order

    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available providers with their info"""
        available = []
        for provider_type, provider in self.providers.items():
            info = provider.get_provider_info()
            info["type"] = provider_type.value
            available.append(info)
        return available

    async def process_with_provider(
        self,
        provider: AIProvider,
        messages: List[Dict[str, str]],
        organization_id: Optional[str] = None,
        **kwargs,
    ) -> Tuple[str, AIProvider]:
        """Process request with specific provider"""

        provider_impl = self.providers.get(provider)
        if not provider_impl:
            raise Exception(f"Provider {provider.value} not found")

        if not provider_impl.is_available():
            raise Exception(f"Provider {provider.value} is not available")

        # Check rate limits if organization ID provided
        if organization_id:
            # Estimate tokens (rough: 4 chars per token)
            estimated_tokens = sum(len(msg["content"]) for msg in messages) // 4

            rate_check = await ai_rate_limiter.check_rate_limit(
                provider.value, organization_id, estimated_tokens
            )

            if not rate_check["allowed"]:
                raise Exception(
                    f"Rate limit exceeded: {rate_check['reason']}. "
                    f"Retry after {rate_check['retry_after']} seconds."
                )

            # Mark request start for concurrent tracking
            await ai_rate_limiter.start_request(provider.value, organization_id)

        try:
            response = await provider_impl.generate_response(messages, **kwargs)

            # Record successful request
            if organization_id:
                # Estimate response tokens
                response_tokens = len(response) // 4
                total_tokens = estimated_tokens + response_tokens

                await ai_rate_limiter.record_request(
                    provider.value, organization_id, total_tokens
                )

            return response, provider

        except Exception as e:
            logger.error(f"Provider {provider.value} failed: {e}")
            raise
        finally:
            # End concurrent request tracking
            if organization_id:
                await ai_rate_limiter.end_request(provider.value, organization_id)

    async def process_with_fallback(
        self,
        messages: List[Dict[str, str]],
        preferred_provider: Optional[AIProvider] = None,
        organization_id: Optional[str] = None,
        **kwargs,
    ) -> Tuple[str, AIProvider]:
        """Process request with fallback to other providers if needed"""

        # Start with preferred provider or default
        providers_to_try = []

        if preferred_provider and preferred_provider in self.providers:
            providers_to_try.append(preferred_provider)
        else:
            providers_to_try.append(self.default_provider)

        # Add fallback providers
        for provider in self.fallback_order:
            if provider not in providers_to_try:
                providers_to_try.append(provider)

        last_error = None
        for provider in providers_to_try:
            try:
                if self.providers[provider].is_available():
                    logger.info(f"Trying provider: {provider.value}")
                    response, used_provider = await self.process_with_provider(
                        provider, messages, organization_id=organization_id, **kwargs
                    )
                    logger.info(f"Successfully used provider: {used_provider.value}")
                    return response, used_provider
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider.value} failed: {e}")

                # If rate limited, don't try other providers immediately
                if "rate limit" in str(e).lower():
                    raise e

                continue

        # All providers failed
        raise Exception(f"All AI providers failed. Last error: {last_error}")

    async def process_chat_message(
        self,
        message: str,
        documents: List[Any],
        chat_history: List[Dict[str, str]] = None,
        analysis_type: str = "general",
        preferred_provider: Optional[str] = None,
        org_settings: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process chat message with multi-provider support and user preferences"""

        start_time = time.time()

        # Determine provider to use with hierarchy:
        # 1. Per-request preference
        # 2. User preference
        # 3. Organization preference
        # 4. System default
        provider_enum = None

        # Check per-request preference
        if preferred_provider:
            provider_map = {p.value: p for p in AIProvider}
            provider_enum = provider_map.get(preferred_provider.lower())

        # Check user preferences
        if not provider_enum and user_preferences:
            user_provider = user_preferences.get("ai_provider_preference")
            if user_provider:
                provider_map = {p.value: p for p in AIProvider}
                provider_enum = provider_map.get(user_provider.lower())

        # Check organization settings for provider preferences
        if not provider_enum and org_settings:
            org_provider = org_settings.get("preferred_ai_provider")
            if org_provider:
                provider_map = {p.value: p for p in AIProvider}
                provider_enum = provider_map.get(org_provider.lower())

        # Build messages
        document_context = self._build_document_context(documents)
        messages = self._build_conversation_messages(
            message, document_context, chat_history, analysis_type
        )

        try:
            # Extract organization ID from settings
            org_id = None
            if org_settings and "organization_id" in org_settings:
                org_id = org_settings["organization_id"]
            elif org_settings and "id" in org_settings:
                org_id = org_settings["id"]

            # Process with fallback
            response, used_provider = await self.process_with_fallback(
                messages, preferred_provider=provider_enum, organization_id=org_id
            )

            # Extract structured data
            structured_data = self._extract_structured_data(response, documents)

            # Calculate metrics
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)

            return {
                "answer": response,
                "sources": self._extract_sources(response, documents),
                "timestamp": datetime.utcnow(),
                "provider_used": used_provider.value,
                "model": self.providers[used_provider].get_provider_info()["model"],
                "analysis_type": analysis_type,
                "structured_data": structured_data,
                "response_metrics": {
                    "response_time_ms": response_time_ms,
                    "provider": used_provider.value,
                    "fallback_used": used_provider
                    != (provider_enum or self.default_provider),
                },
            }

        except Exception as e:
            logger.error(f"Multi-provider AI service error: {e}")

            # Provide helpful error messages based on error type
            error_message, user_action = self._get_user_friendly_error(e, provider_enum)

            # Return error response
            return {
                "answer": error_message,
                "sources": [],
                "timestamp": datetime.utcnow(),
                "provider_used": "none",
                "error": str(e),
                "error_type": type(e).__name__,
                "user_action": user_action,
                "available_providers": [
                    p["name"] for p in self.get_available_providers() if p["available"]
                ],
                "fallback_attempted": True,
            }

    def _get_user_friendly_error(
        self, error: Exception, attempted_provider: Optional[AIProvider] = None
    ) -> Tuple[str, str]:
        """Convert technical errors to user-friendly messages"""

        error_str = str(error).lower()
        error_type = type(error).__name__

        # API Key errors
        if "api key" in error_str or "unauthorized" in error_str or "401" in error_str:
            return (
                "API authentication failed. Please verify your API keys are correctly configured.",
                "Check your API keys in Settings > AI Providers",
            )

        # Rate limit errors
        elif "rate limit" in error_str or "429" in error_str:
            return (
                "AI provider rate limit exceeded. Please try again in a few moments or switch providers.",
                "Wait a moment or select a different AI provider",
            )

        # Quota/billing errors
        elif "quota" in error_str or "billing" in error_str or "payment" in error_str:
            return (
                "AI provider quota exceeded or billing issue. Please check your provider account.",
                "Verify your provider subscription and billing status",
            )

        # Network errors
        elif (
            "timeout" in error_str
            or "connection" in error_str
            or error_type == "ConnectTimeout"
        ):
            return (
                "Network connection issue. The AI provider may be temporarily unavailable.",
                "Check your internet connection or try a different provider",
            )

        # Model errors
        elif "model" in error_str and "not found" in error_str:
            return (
                "The requested AI model is not available. Please select a different model.",
                "Choose a different model in your preferences",
            )

        # Token limit errors
        elif "token" in error_str and ("limit" in error_str or "maximum" in error_str):
            return (
                "Document too large for AI processing. Try with a smaller document or split it into sections.",
                "Reduce document size or process in smaller chunks",
            )

        # Provider-specific errors
        elif attempted_provider:
            provider_name = attempted_provider.value.title()
            return (
                f"{provider_name} service is currently unavailable. Trying alternative providers...",
                "Wait for automatic fallback or manually select a different provider",
            )

        # Generic fallback
        else:
            return (
                "An error occurred while processing your request. Our team has been notified.",
                "Try again or select a different AI provider",
            )

    def _build_document_context(self, documents: List[Any]) -> str:
        """Build context from documents"""
        if not documents:
            return "No documents provided for context."

        context = "Documents provided for analysis:\n\n"

        for i, doc in enumerate(documents, 1):
            context += f"Document {i}: {doc.filename}\n"

            if hasattr(doc, "extracted_content") and doc.extracted_content:
                # Limit content to prevent token overflow
                content = doc.extracted_content[:3000]
                context += f"Content:\n{content}\n"

                if len(doc.extracted_content) > 3000:
                    context += f"\n[... {len(doc.extracted_content) - 3000} characters truncated ...]\n"

            context += "\n" + "=" * 60 + "\n\n"

        return context

    def _build_conversation_messages(
        self,
        current_message: str,
        document_context: str,
        chat_history: List[Dict[str, str]] = None,
        analysis_type: str = "general",
    ) -> List[Dict[str, str]]:
        """Build message array for AI providers"""

        messages = [
            {"role": "system", "content": self.system_prompts["legal_assistant"]},
            {"role": "system", "content": document_context},
        ]

        # Add chat history
        if chat_history:
            for msg in chat_history[-6:]:  # Last 6 messages
                messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages

    def _extract_structured_data(
        self, response: str, documents: List[Any]
    ) -> Dict[str, Any]:
        """Extract structured data from response"""
        return {
            "summary": self._extract_summary(response),
            "action_items": self._extract_action_items(response),
            "key_findings": self._extract_key_findings(response),
        }

    def _extract_summary(self, response: str) -> str:
        """Extract summary from response"""
        lines = response.split("\n")
        for line in lines:
            if len(line.strip()) > 50:
                return line.strip()
        return "See full analysis above."

    def _extract_action_items(self, response: str) -> List[str]:
        """Extract action items from response"""
        action_items = []
        lines = response.split("\n")

        for line in lines:
            if re.match(r"^[\d•\-\*]\s*\w", line.strip()):
                action_items.append(line.strip())

        return action_items[:5]

    def _extract_key_findings(self, response: str) -> List[str]:
        """Extract key findings from response"""
        findings = []
        lines = response.split("\n")

        for line in lines:
            line_lower = line.strip().lower()
            if any(
                indicator in line_lower
                for indicator in ["found", "identified", "discovered"]
            ):
                findings.append(line.strip())

        return findings[:5]

    def _extract_sources(
        self, response: str, documents: List[Any]
    ) -> List[Dict[str, Any]]:
        """Extract document sources referenced in response"""
        sources = []
        response_lower = response.lower()

        for doc in documents:
            if doc.filename.lower() in response_lower:
                sources.append(
                    {
                        "document_id": doc.id,
                        "document_name": doc.filename,
                        "relevance": "referenced",
                    }
                )

        return sources
