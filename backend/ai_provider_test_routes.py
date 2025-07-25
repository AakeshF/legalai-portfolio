"""
AI Provider Authentication Testing Routes
Provides endpoints to test API keys, billing status, and service limits for AI providers
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, Literal
import asyncio
import aiohttp
import time
import os
from datetime import datetime

router = APIRouter(prefix="/api/ai", tags=["ai-testing"])


class AITestRequest(BaseModel):
    provider: Literal["openai", "anthropic", "google", "azure", "ollama"]
    test_type: Literal["authentication", "connectivity", "rate_limit", "billing"]


class AuthTestResponse(BaseModel):
    authenticated: bool
    healthy: bool
    error: Optional[str] = None
    billing_info: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None


class ConnectivityTestResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    response_time_ms: Optional[int] = None


class RateLimitTestResponse(BaseModel):
    rate_limit_ok: bool
    error: Optional[str] = None
    current_limit: Optional[int] = None
    remaining_requests: Optional[int] = None


# Provider configuration mapping
PROVIDER_CONFIGS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "test_endpoint": "/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "test_endpoint": "/messages",
        "auth_header": "x-api-key",
        "auth_prefix": "",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1",
        "test_endpoint": "/models",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "env_key": "GOOGLE_API_KEY",
    },
    "azure": {
        "base_url": None,  # Custom endpoint
        "test_endpoint": "/openai/deployments",
        "auth_header": "api-key",
        "auth_prefix": "",
        "env_key": "AZURE_OPENAI_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "test_endpoint": "/api/tags",
        "auth_header": None,
        "auth_prefix": "",
        "env_key": None,
    },
}


async def test_provider_connectivity(provider: str) -> ConnectivityTestResponse:
    """Test basic connectivity to the AI provider"""
    start_time = time.time()
    config = PROVIDER_CONFIGS.get(provider)

    if not config:
        return ConnectivityTestResponse(
            success=False, error=f"Unknown provider: {provider}", response_time_ms=0
        )

    # Special case for Azure - needs custom endpoint
    if provider == "azure":
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not azure_endpoint:
            return ConnectivityTestResponse(
                success=False,
                error="Azure OpenAI endpoint not configured",
                response_time_ms=0,
            )
        base_url = azure_endpoint.rstrip("/")
    else:
        base_url = config["base_url"]

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Simple HEAD request to test connectivity
            test_url = f"{base_url}{config['test_endpoint']}"
            async with session.head(test_url) as response:
                response_time = int((time.time() - start_time) * 1000)

                # Any response (even 401/403) means connectivity is working
                return ConnectivityTestResponse(
                    success=True, response_time_ms=response_time
                )

    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return ConnectivityTestResponse(
            success=False, error=str(e), response_time_ms=response_time
        )


async def test_provider_authentication(provider: str) -> AuthTestResponse:
    """Test API key authentication for the AI provider"""
    start_time = time.time()
    config = PROVIDER_CONFIGS.get(provider)

    if not config:
        return AuthTestResponse(
            authenticated=False,
            healthy=False,
            error=f"Unknown provider: {provider}",
            response_time_ms=0,
        )

    # Get API key from environment
    if config["env_key"]:
        api_key = os.getenv(config["env_key"])
        if not api_key:
            return AuthTestResponse(
                authenticated=False,
                healthy=False,
                error=f"API key not found in environment variable {config['env_key']}",
                response_time_ms=0,
            )
    else:
        api_key = None  # For Ollama (local)

    # Special case for Azure
    if provider == "azure":
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not azure_endpoint:
            return AuthTestResponse(
                authenticated=False,
                healthy=False,
                error="Azure OpenAI endpoint not configured",
                response_time_ms=0,
            )
        base_url = azure_endpoint.rstrip("/")
    else:
        base_url = config["base_url"]

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {}

        # Set authentication header if needed
        if api_key and config["auth_header"]:
            if config["auth_prefix"]:
                headers[config["auth_header"]] = f"{config['auth_prefix']} {api_key}"
            else:
                headers[config["auth_header"]] = api_key

        async with aiohttp.ClientSession(timeout=timeout) as session:
            test_url = f"{base_url}{config['test_endpoint']}"

            # Provider-specific test requests
            if provider == "openai":
                async with session.get(test_url, headers=headers) as response:
                    response_time = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        # Parse billing information if available
                        billing_info = None
                        if "x-ratelimit-remaining-requests" in response.headers:
                            billing_info = {
                                "quotaRemaining": int(
                                    response.headers.get(
                                        "x-ratelimit-remaining-requests", 0
                                    )
                                ),
                                "quotaLimit": int(
                                    response.headers.get(
                                        "x-ratelimit-limit-requests", 0
                                    )
                                ),
                            }

                        return AuthTestResponse(
                            authenticated=True,
                            healthy=True,
                            billing_info=billing_info,
                            response_time_ms=response_time,
                        )
                    elif response.status == 401:
                        return AuthTestResponse(
                            authenticated=False,
                            healthy=True,
                            error="Invalid API key",
                            response_time_ms=response_time,
                        )
                    elif response.status == 403:
                        error_text = await response.text()
                        if (
                            "quota" in error_text.lower()
                            or "billing" in error_text.lower()
                        ):
                            return AuthTestResponse(
                                authenticated=True,
                                healthy=False,
                                error="Billing quota exceeded",
                                response_time_ms=response_time,
                            )
                        else:
                            return AuthTestResponse(
                                authenticated=False,
                                healthy=True,
                                error="API key lacks required permissions",
                                response_time_ms=response_time,
                            )
                    elif response.status == 429:
                        return AuthTestResponse(
                            authenticated=True,
                            healthy=False,
                            error="Rate limit exceeded",
                            response_time_ms=response_time,
                        )
                    else:
                        return AuthTestResponse(
                            authenticated=False,
                            healthy=False,
                            error=f"HTTP {response.status}: {response.reason}",
                            response_time_ms=response_time,
                        )

            elif provider == "anthropic":
                # Test with a minimal message request
                test_payload = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "Hi"}],
                }
                headers["content-type"] = "application/json"
                headers["anthropic-version"] = "2023-06-01"

                async with session.post(
                    f"{base_url}/messages", headers=headers, json=test_payload
                ) as response:
                    response_time = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        return AuthTestResponse(
                            authenticated=True,
                            healthy=True,
                            response_time_ms=response_time,
                        )
                    elif response.status == 401:
                        return AuthTestResponse(
                            authenticated=False,
                            healthy=True,
                            error="Invalid API key",
                            response_time_ms=response_time,
                        )
                    elif response.status == 403:
                        error_text = await response.text()
                        return AuthTestResponse(
                            authenticated=True,
                            healthy=False,
                            error="Billing or quota issue",
                            response_time_ms=response_time,
                        )
                    elif response.status == 429:
                        return AuthTestResponse(
                            authenticated=True,
                            healthy=False,
                            error="Rate limit exceeded",
                            response_time_ms=response_time,
                        )
                    else:
                        return AuthTestResponse(
                            authenticated=False,
                            healthy=False,
                            error=f"HTTP {response.status}: {response.reason}",
                            response_time_ms=response_time,
                        )

            elif provider == "ollama":
                # Ollama doesn't require authentication
                async with session.get(test_url) as response:
                    response_time = int((time.time() - start_time) * 1000)

                    if response.status == 200:
                        return AuthTestResponse(
                            authenticated=True,
                            healthy=True,
                            response_time_ms=response_time,
                        )
                    else:
                        return AuthTestResponse(
                            authenticated=False,
                            healthy=False,
                            error=f"Ollama service not available: HTTP {response.status}",
                            response_time_ms=response_time,
                        )

            else:
                # Generic test for other providers
                async with session.get(test_url, headers=headers) as response:
                    response_time = int((time.time() - start_time) * 1000)

                    if response.status in [200, 201]:
                        return AuthTestResponse(
                            authenticated=True,
                            healthy=True,
                            response_time_ms=response_time,
                        )
                    elif response.status == 401:
                        return AuthTestResponse(
                            authenticated=False,
                            healthy=True,
                            error="Invalid API key",
                            response_time_ms=response_time,
                        )
                    elif response.status == 403:
                        return AuthTestResponse(
                            authenticated=True,
                            healthy=False,
                            error="Access forbidden - check billing or permissions",
                            response_time_ms=response_time,
                        )
                    elif response.status == 429:
                        return AuthTestResponse(
                            authenticated=True,
                            healthy=False,
                            error="Rate limit exceeded",
                            response_time_ms=response_time,
                        )
                    else:
                        return AuthTestResponse(
                            authenticated=False,
                            healthy=False,
                            error=f"HTTP {response.status}: {response.reason}",
                            response_time_ms=response_time,
                        )

    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return AuthTestResponse(
            authenticated=False,
            healthy=False,
            error=str(e),
            response_time_ms=response_time,
        )


async def test_provider_rate_limits(provider: str) -> RateLimitTestResponse:
    """Test rate limit status for the AI provider"""
    try:
        # For now, this is a simplified check
        # In a full implementation, you'd make multiple rapid requests to test limits
        auth_result = await test_provider_authentication(provider)

        if not auth_result.authenticated:
            return RateLimitTestResponse(
                rate_limit_ok=False,
                error="Cannot test rate limits - authentication failed",
            )

        # If authentication passed, assume rate limits are OK for now
        return RateLimitTestResponse(rate_limit_ok=True)

    except Exception as e:
        return RateLimitTestResponse(rate_limit_ok=False, error=str(e))


@router.post("/test-auth")
async def test_ai_provider(request: AITestRequest):
    """Test AI provider authentication, connectivity, or rate limits"""

    try:
        if request.test_type == "connectivity":
            result = await test_provider_connectivity(request.provider)
            return result.dict()

        elif request.test_type == "authentication":
            result = await test_provider_authentication(request.provider)
            return result.dict()

        elif request.test_type == "rate_limit":
            result = await test_provider_rate_limits(request.provider)
            return result.dict()

        elif request.test_type == "billing":
            # Billing info is included in the authentication test
            auth_result = await test_provider_authentication(request.provider)
            return {
                "billing_ok": auth_result.authenticated and auth_result.healthy,
                "billing_info": auth_result.billing_info,
                "error": auth_result.error if not auth_result.healthy else None,
            }

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown test type: {request.test_type}"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.get("/provider-status")
async def get_all_provider_status():
    """Get authentication status for all configured AI providers"""

    results = {}
    providers = ["openai", "anthropic", "google", "azure", "ollama"]

    # Test all providers concurrently
    tasks = [test_provider_authentication(provider) for provider in providers]
    auth_results = await asyncio.gather(*tasks, return_exceptions=True)

    for provider, result in zip(providers, auth_results):
        if isinstance(result, Exception):
            results[provider] = {
                "authenticated": False,
                "healthy": False,
                "error": str(result),
                "lastChecked": datetime.now().isoformat(),
            }
        else:
            results[provider] = {
                "authenticated": result.authenticated,
                "healthy": result.healthy,
                "error": result.error,
                "billing_info": result.billing_info,
                "response_time_ms": result.response_time_ms,
                "lastChecked": datetime.now().isoformat(),
            }

    return results


@router.get("/health")
async def ai_providers_health():
    """Health check endpoint for AI providers"""
    status = await get_all_provider_status()

    healthy_providers = [
        provider
        for provider, info in status.items()
        if info.get("authenticated") and info.get("healthy")
    ]

    return {
        "healthy_providers": healthy_providers,
        "total_providers": len(status),
        "overall_health": len(healthy_providers) > 0,
        "details": status,
    }
