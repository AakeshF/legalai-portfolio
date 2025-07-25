# services/ai_rate_limiter.py - Provider-specific rate limiting
import time
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class AIProviderRateLimiter:
    """Rate limiter for AI providers with different limits"""

    def __init__(self):
        # Provider-specific rate limits (requests per minute)
        self.provider_limits = {
            "openai": {
                "requests_per_minute": 60,
                "tokens_per_minute": 90000,
                "requests_per_day": 10000,
            },
            "claude": {
                "requests_per_minute": 50,
                "tokens_per_minute": 50000,
                "requests_per_hour": 1000,
                "max_concurrent": 5,
            },
            "gemini": {
                "requests_per_minute": 60,
                "tokens_per_minute": 60000,
                "requests_per_hour": 1500,
            },
            "local": {
                "requests_per_minute": 100,  # Higher for local
                "tokens_per_minute": 200000,
                "max_concurrent": 10,
            },
        }

        # Track request history per provider per organization
        self._request_history = defaultdict(lambda: defaultdict(lambda: deque()))
        self._token_usage = defaultdict(lambda: defaultdict(lambda: deque()))
        self._concurrent_requests = defaultdict(lambda: defaultdict(int))

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self, provider: str, organization_id: str, tokens_requested: int = 0
    ) -> Dict[str, Any]:
        """Check if request is within rate limits"""

        async with self._lock:
            now = time.time()
            limits = self.provider_limits.get(provider, self.provider_limits["openai"])

            # Clean old entries
            self._clean_old_entries(provider, organization_id, now)

            # Check various rate limits
            checks = {"allowed": True, "reason": None, "retry_after": 0}

            # Check requests per minute
            if "requests_per_minute" in limits:
                rpm_check = self._check_requests_per_minute(
                    provider, organization_id, limits["requests_per_minute"], now
                )
                if not rpm_check["allowed"]:
                    return rpm_check

            # Check tokens per minute
            if "tokens_per_minute" in limits and tokens_requested > 0:
                tpm_check = self._check_tokens_per_minute(
                    provider,
                    organization_id,
                    limits["tokens_per_minute"],
                    tokens_requested,
                    now,
                )
                if not tpm_check["allowed"]:
                    return tpm_check

            # Check concurrent requests
            if "max_concurrent" in limits:
                concurrent_check = self._check_concurrent_requests(
                    provider, organization_id, limits["max_concurrent"]
                )
                if not concurrent_check["allowed"]:
                    return concurrent_check

            # Check hourly limits
            if "requests_per_hour" in limits:
                rph_check = self._check_requests_per_hour(
                    provider, organization_id, limits["requests_per_hour"], now
                )
                if not rph_check["allowed"]:
                    return rph_check

            # All checks passed
            return {
                "allowed": True,
                "reason": None,
                "retry_after": 0,
                "current_usage": self._get_current_usage(
                    provider, organization_id, now
                ),
            }

    async def record_request(
        self,
        provider: str,
        organization_id: str,
        tokens_used: int = 0,
        request_id: Optional[str] = None,
    ):
        """Record a completed request"""

        async with self._lock:
            now = time.time()

            # Record request
            self._request_history[provider][organization_id].append(
                {"timestamp": now, "request_id": request_id}
            )

            # Record token usage
            if tokens_used > 0:
                self._token_usage[provider][organization_id].append(
                    {"timestamp": now, "tokens": tokens_used}
                )

            logger.debug(
                f"Recorded request for {provider}/{organization_id}: "
                f"{tokens_used} tokens"
            )

    async def start_request(self, provider: str, organization_id: str):
        """Mark start of concurrent request"""
        async with self._lock:
            self._concurrent_requests[provider][organization_id] += 1

    async def end_request(self, provider: str, organization_id: str):
        """Mark end of concurrent request"""
        async with self._lock:
            count = self._concurrent_requests[provider][organization_id]
            if count > 0:
                self._concurrent_requests[provider][organization_id] = count - 1

    def _clean_old_entries(self, provider: str, organization_id: str, now: float):
        """Remove entries older than tracking window"""

        # Clean requests older than 1 hour
        cutoff_hour = now - 3600
        requests = self._request_history[provider][organization_id]
        while requests and requests[0]["timestamp"] < cutoff_hour:
            requests.popleft()

        # Clean token usage older than 1 minute
        cutoff_minute = now - 60
        tokens = self._token_usage[provider][organization_id]
        while tokens and tokens[0]["timestamp"] < cutoff_minute:
            tokens.popleft()

    def _check_requests_per_minute(
        self, provider: str, organization_id: str, limit: int, now: float
    ) -> Dict[str, Any]:
        """Check requests per minute limit"""

        minute_ago = now - 60
        requests = self._request_history[provider][organization_id]
        recent_requests = sum(1 for r in requests if r["timestamp"] > minute_ago)

        if recent_requests >= limit:
            oldest_in_window = min(
                r["timestamp"] for r in requests if r["timestamp"] > minute_ago
            )
            retry_after = int(60 - (now - oldest_in_window)) + 1

            return {
                "allowed": False,
                "reason": f"Rate limit exceeded: {recent_requests}/{limit} requests per minute",
                "retry_after": retry_after,
                "limit_type": "requests_per_minute",
            }

        return {"allowed": True}

    def _check_tokens_per_minute(
        self,
        provider: str,
        organization_id: str,
        limit: int,
        tokens_requested: int,
        now: float,
    ) -> Dict[str, Any]:
        """Check tokens per minute limit"""

        minute_ago = now - 60
        token_history = self._token_usage[provider][organization_id]
        recent_tokens = sum(
            t["tokens"] for t in token_history if t["timestamp"] > minute_ago
        )

        if recent_tokens + tokens_requested > limit:
            retry_after = 60  # Wait a full minute for token bucket to refill

            return {
                "allowed": False,
                "reason": f"Token limit exceeded: {recent_tokens + tokens_requested}/{limit} tokens per minute",
                "retry_after": retry_after,
                "limit_type": "tokens_per_minute",
            }

        return {"allowed": True}

    def _check_concurrent_requests(
        self, provider: str, organization_id: str, limit: int
    ) -> Dict[str, Any]:
        """Check concurrent requests limit"""

        current = self._concurrent_requests[provider][organization_id]

        if current >= limit:
            return {
                "allowed": False,
                "reason": f"Concurrent request limit exceeded: {current}/{limit}",
                "retry_after": 5,  # Check again in 5 seconds
                "limit_type": "concurrent_requests",
            }

        return {"allowed": True}

    def _check_requests_per_hour(
        self, provider: str, organization_id: str, limit: int, now: float
    ) -> Dict[str, Any]:
        """Check requests per hour limit"""

        hour_ago = now - 3600
        requests = self._request_history[provider][organization_id]
        recent_requests = sum(1 for r in requests if r["timestamp"] > hour_ago)

        if recent_requests >= limit:
            oldest_in_window = min(
                r["timestamp"] for r in requests if r["timestamp"] > hour_ago
            )
            retry_after = int(3600 - (now - oldest_in_window)) + 1

            return {
                "allowed": False,
                "reason": f"Hourly limit exceeded: {recent_requests}/{limit} requests per hour",
                "retry_after": retry_after,
                "limit_type": "requests_per_hour",
            }

        return {"allowed": True}

    def _get_current_usage(
        self, provider: str, organization_id: str, now: float
    ) -> Dict[str, Any]:
        """Get current usage statistics"""

        minute_ago = now - 60
        hour_ago = now - 3600

        requests = self._request_history[provider][organization_id]
        tokens = self._token_usage[provider][organization_id]

        return {
            "requests_last_minute": sum(
                1 for r in requests if r["timestamp"] > minute_ago
            ),
            "requests_last_hour": sum(1 for r in requests if r["timestamp"] > hour_ago),
            "tokens_last_minute": sum(
                t["tokens"] for t in tokens if t["timestamp"] > minute_ago
            ),
            "concurrent_requests": self._concurrent_requests[provider][organization_id],
        }

    def get_provider_limits(self, provider: str) -> Dict[str, Any]:
        """Get rate limits for a provider"""
        return self.provider_limits.get(provider, {})

    def set_custom_limits(
        self, provider: str, organization_id: str, custom_limits: Dict[str, int]
    ):
        """Set custom rate limits for an organization"""
        # This could be stored in database for persistence
        # For now, we'll store in memory
        if provider not in self.provider_limits:
            self.provider_limits[provider] = {}

        # Create org-specific limits
        org_key = f"{provider}:{organization_id}"
        self.provider_limits[org_key] = {
            **self.provider_limits[provider],
            **custom_limits,
        }


# Global rate limiter instance
ai_rate_limiter = AIProviderRateLimiter()
