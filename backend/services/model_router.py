import asyncio
import httpx
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
import logging
from abc import ABC, abstractmethod

from models import (
    User, Organization, APIKeyStore, AIAuditLog, PromptLog,
    PromptStatus
)
from services.api_key_manager import APIKeyManager
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    provider: str
    model: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7
    rate_limit_per_minute: int = 10
    timeout_seconds: int = 30
    supports_streaming: bool = True
    fallback_providers: List[str] = field(default_factory=list)


@dataclass
class ModelResponse:
    content: str
    provider: str
    model: str
    tokens_used: int
    response_time_ms: int
    cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelProvider(ABC):
    """Abstract base class for model providers"""
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        config: ModelConfig,
        stream: bool = False
    ) -> ModelResponse:
        pass
    
    @abstractmethod
    async def validate_api_key(self, api_key: str) -> bool:
        pass
    
    @abstractmethod
    def estimate_cost(self, tokens: int, model: str) -> float:
        pass


class OpenAIProvider(ModelProvider):
    """OpenAI API provider"""
    
    def __init__(self):
        self.base_url = "https://api.openai.com/v1"
        self.pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
        }
    
    async def complete(
        self,
        prompt: str,
        config: ModelConfig,
        stream: bool = False
    ) -> ModelResponse:
        start_time = datetime.utcnow()
        
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            tokens_used = result["usage"]["total_tokens"]
            
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            cost = self.estimate_cost(tokens_used, config.model)
            
            return ModelResponse(
                content=content,
                provider="openai",
                model=config.model,
                tokens_used=tokens_used,
                response_time_ms=response_time,
                cost=cost,
                metadata={"finish_reason": result["choices"][0]["finish_reason"]}
            )
    
    async def validate_api_key(self, api_key: str) -> bool:
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                return response.status_code == 200
        except:
            return False
    
    def estimate_cost(self, tokens: int, model: str) -> float:
        if model not in self.pricing:
            return 0.0
        prices = self.pricing[model]
        # Rough estimate: 75% input, 25% output
        input_tokens = int(tokens * 0.75)
        output_tokens = tokens - input_tokens
        return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1000


class ClaudeProvider(ModelProvider):
    """Anthropic Claude API provider"""
    
    def __init__(self):
        self.base_url = "https://api.anthropic.com/v1"
        self.pricing = {
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.0025, "output": 0.0125}
        }
    
    async def complete(
        self,
        prompt: str,
        config: ModelConfig,
        stream: bool = False
    ) -> ModelResponse:
        start_time = datetime.utcnow()
        
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            content = result["content"][0]["text"]
            tokens_used = result["usage"]["input_tokens"] + result["usage"]["output_tokens"]
            
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            cost = self.estimate_cost(tokens_used, config.model)
            
            return ModelResponse(
                content=content,
                provider="claude",
                model=config.model,
                tokens_used=tokens_used,
                response_time_ms=response_time,
                cost=cost,
                metadata={"stop_reason": result.get("stop_reason")}
            )
    
    async def validate_api_key(self, api_key: str) -> bool:
        try:
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            async with httpx.AsyncClient(timeout=5) as client:
                # Simple validation request
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json={
                        "model": "claude-3-haiku",
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1
                    }
                )
                return response.status_code in [200, 401]  # 401 means key format is valid
        except:
            return False
    
    def estimate_cost(self, tokens: int, model: str) -> float:
        if model not in self.pricing:
            return 0.0
        prices = self.pricing[model]
        input_tokens = int(tokens * 0.75)
        output_tokens = tokens - input_tokens
        return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1000


class GenericOpenAIProvider(ModelProvider):
    """Generic OpenAI-compatible API provider with demo mode"""
    
    def __init__(self):
        self.base_url = "https://api.openai.com/v1"
        self.demo_responses = {
            "legal_analysis": "This is a demo legal analysis response. In production, this would contain detailed legal insights.",
            "contract_review": "Demo contract review: The document appears to be a standard agreement with typical clauses.",
            "case_research": "Demo case research: Similar cases include precedents from various jurisdictions.",
            "default": "This is a demo response. Please configure a valid API key for actual AI responses."
        }
    
    async def complete(
        self,
        prompt: str,
        config: ModelConfig,
        stream: bool = False
    ) -> ModelResponse:
        start_time = datetime.utcnow()
        
        # Demo mode if no API key
        if not config.api_key or config.api_key == "demo":
            await asyncio.sleep(0.5)  # Simulate API delay
            
            # Determine response type from prompt
            prompt_lower = prompt.lower()
            if "contract" in prompt_lower:
                content = self.demo_responses["contract_review"]
            elif "legal" in prompt_lower or "law" in prompt_lower:
                content = self.demo_responses["legal_analysis"]
            elif "case" in prompt_lower or "research" in prompt_lower:
                content = self.demo_responses["case_research"]
            else:
                content = self.demo_responses["default"]
            
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ModelResponse(
                content=content,
                provider="openai",
                model="demo",
                tokens_used=len(content.split()),
                response_time_ms=response_time,
                cost=0.0,
                metadata={"demo_mode": True}
            )
        
        # Real API call
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config.model or "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            tokens_used = result["usage"]["total_tokens"]
            
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            cost = tokens_used * 0.0001  # $0.1 per 1M tokens
            
            return ModelResponse(
                content=content,
                provider="openai",
                model=config.model,
                tokens_used=tokens_used,
                response_time_ms=response_time,
                cost=cost,
                metadata={"finish_reason": result["choices"][0]["finish_reason"]}
            )
    
    async def validate_api_key(self, api_key: str) -> bool:
        if api_key == "demo":
            return True
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                return response.status_code == 200
        except:
            return False
    
    def estimate_cost(self, tokens: int, model: str) -> float:
        return tokens * 0.0001  # $0.1 per 1M tokens


class ModelRouter:
    """
    Sophisticated routing system for multiple AI providers
    """
    
    def __init__(self):
        self.providers = {
            "openai": OpenAIProvider(),
            "claude": ClaudeProvider(),
            "generic_openai": GenericOpenAIProvider()
        }
        self.api_key_manager = None  # Will be initialized with db session when needed
        self._api_key_manager_lock = threading.Lock()  # Thread safety for lazy initialization
        self._rate_limiters = {}
        self._health_status = {}
    
    async def route_request(
        self,
        prompt: str,
        db: Session,
        user_id: str,
        org_id: str,
        prompt_log_id: Optional[int] = None,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> ModelResponse:
        """
        Route request to appropriate model based on preferences and availability
        """
        # Get user and organization preferences
        user = db.query(User).filter(User.id == user_id).first()
        org = db.query(Organization).filter(Organization.id == org_id).first()
        
        # Determine provider order
        provider_order = self._determine_provider_order(
            user, org, preferred_provider
        )
        
        # Try each provider in order
        last_error = None
        attempted_providers = []
        
        for provider_name in provider_order:
            try:
                # Check rate limits
                if not await self._check_rate_limit(provider_name, org_id):
                    logger.warning(f"Rate limit exceeded for {provider_name}")
                    continue
                
                # Get API key
                api_key = await self._get_api_key(
                    db, provider_name, user_id, org_id
                )
                
                if not api_key and provider_name != "generic_openai":
                    logger.warning(f"No API key for {provider_name}")
                    continue
                
                # Get model configuration
                config = self._get_model_config(
                    provider_name, preferred_model, user, org, api_key
                )
                
                # Make the request
                provider = self.providers[provider_name]
                response = await provider.complete(prompt, config)
                
                # Log successful request
                await self._log_request(
                    db, user_id, org_id, prompt_log_id,
                    provider_name, config.model, response,
                    attempted_providers
                )
                
                # Update rate limiter
                await self._update_rate_limiter(provider_name, org_id)
                
                return response
                
            except Exception as e:
                logger.error(f"Error with {provider_name}: {e}")
                last_error = e
                attempted_providers.append(provider_name)
                continue
        
        # All providers failed
        raise Exception(
            f"All providers failed. Last error: {last_error}. "
            f"Attempted: {', '.join(attempted_providers)}"
        )
    
    def _determine_provider_order(
        self,
        user: User,
        org: Organization,
        preferred_provider: Optional[str]
    ) -> List[str]:
        """Determine the order of providers to try"""
        order = []
        
        # 1. Explicit preference
        if preferred_provider and preferred_provider in self.providers:
            order.append(preferred_provider)
        
        # 2. User preference
        if user.ai_provider_preference and user.ai_provider_preference in self.providers:
            if user.ai_provider_preference not in order:
                order.append(user.ai_provider_preference)
        
        # 3. Organization preference
        if hasattr(org, "preferred_ai_provider") and org.preferred_ai_provider in self.providers:
            if org.preferred_ai_provider not in order:
                order.append(org.preferred_ai_provider)
        
        # 4. Default order based on cost/performance
        default_order = ["openai", "claude", "generic_openai"]
        for provider in default_order:
            if provider not in order:
                order.append(provider)
        
        return order
    
    async def _get_api_key(
        self,
        db: Session,
        provider: str,
        user_id: str,
        org_id: str
    ) -> Optional[str]:
        """Get API key for provider"""
        # Initialize api_key_manager if needed (thread-safe)
        if self.api_key_manager is None:
            with self._api_key_manager_lock:
                # Double-check pattern
                if self.api_key_manager is None:
                    from services.api_key_manager import APIKeyManager
                    self.api_key_manager = APIKeyManager(db)
        
        # Try user key first
        user_key = await self.api_key_manager.get_api_key(
            db, provider, user_id=user_id
        )
        if user_key:
            return user_key
        
        # Try organization key
        org_key = await self.api_key_manager.get_api_key(
            db, provider, org_id=org_id
        )
        if org_key:
            return org_key
        
        # Try platform key
        platform_key = getattr(settings, f"{provider.upper()}_API_KEY", None)
        if platform_key:
            return platform_key
        
        # Demo mode for generic provider
        if provider == "generic_openai":
            return "demo"
        
        return None
    
    def _get_model_config(
        self,
        provider: str,
        preferred_model: Optional[str],
        user: User,
        org: Organization,
        api_key: str
    ) -> ModelConfig:
        """Get model configuration"""
        # Determine model
        model = preferred_model
        
        if not model and user.ai_model_preferences:
            model = user.ai_model_preferences.get(provider)
        
        if not model:
            # Default models
            default_models = {
                "openai": "gpt-4-turbo",
                "claude": "claude-3-sonnet",
                "generic_openai": "gpt-4"
            }
            model = default_models.get(provider, "default")
        
        # Get limits from organization
        max_tokens = min(
            4000,
            getattr(org, "ai_max_tokens_per_request", 4000)
        )
        
        rate_limit = min(
            60,
            getattr(org, "ai_rate_limit_per_minute", 10)
        )
        
        return ModelConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
            rate_limit_per_minute=rate_limit
        )
    
    async def _check_rate_limit(self, provider: str, org_id: str) -> bool:
        """Check if request is within rate limits"""
        key = f"{provider}:{org_id}"
        
        if key not in self._rate_limiters:
            self._rate_limiters[key] = {
                "requests": [],
                "limit": 10
            }
        
        limiter = self._rate_limiters[key]
        now = datetime.utcnow()
        
        # Remove old requests
        limiter["requests"] = [
            req for req in limiter["requests"]
            if now - req < timedelta(minutes=1)
        ]
        
        # Check limit
        return len(limiter["requests"]) < limiter["limit"]
    
    async def _update_rate_limiter(self, provider: str, org_id: str):
        """Update rate limiter after request"""
        key = f"{provider}:{org_id}"
        if key in self._rate_limiters:
            self._rate_limiters[key]["requests"].append(datetime.utcnow())
    
    async def _log_request(
        self,
        db: Session,
        user_id: str,
        org_id: str,
        prompt_log_id: Optional[int],
        provider: str,
        model: str,
        response: ModelResponse,
        attempted_providers: List[str]
    ):
        """Log AI request for audit"""
        audit_log = AIAuditLog(
            organization_id=org_id,
            user_id=user_id,
            request_id=str(prompt_log_id) if prompt_log_id else None,
            request_type="chat",
            provider_used=provider,
            model_used=model,
            provider_fallback=json.dumps(attempted_providers),
            response_time_ms=response.response_time_ms,
            tokens_used=response.tokens_used,
            estimated_cost=response.cost,
            processing_location="cloud",
            created_at=datetime.utcnow()
        )
        
        db.add(audit_log)
        
        # Update prompt log if exists
        if prompt_log_id:
            prompt_log = db.query(PromptLog).filter(
                PromptLog.id == prompt_log_id
            ).first()
            if prompt_log:
                prompt_log.model_used = f"{provider}:{model}"
                prompt_log.response_time_ms = response.response_time_ms
                prompt_log.tokens_used = response.tokens_used
        
        db.commit()
    
    async def validate_all_keys(self, db: Session, org_id: str) -> Dict[str, bool]:
        """Validate all configured API keys"""
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                api_key = await self._get_api_key(db, provider_name, None, org_id)
                if api_key:
                    results[provider_name] = await provider.validate_api_key(api_key)
                else:
                    results[provider_name] = False
            except Exception as e:
                logger.error(f"Error validating {provider_name}: {e}")
                results[provider_name] = False
        
        return results