# rate_limiter.py - Advanced rate limiting and abuse prevention
import time
import json
from typing import Dict, Optional, Tuple, List, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import hashlib
import logging
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


class RateLimitType(str, Enum):
    """Types of rate limits"""

    GLOBAL = "global"  # Overall API rate limit
    USER = "user"  # Per-user rate limit
    ORGANIZATION = "organization"  # Per-organization rate limit
    ENDPOINT = "endpoint"  # Per-endpoint rate limit
    IP = "ip"  # Per-IP rate limit
    RESOURCE = "resource"  # Specific resource access


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""

    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int = 10  # Allow short bursts
    penalty_duration: int = 300  # Penalty duration in seconds (5 minutes)


class RateLimiter:
    """Advanced rate limiter with multiple strategies"""

    def __init__(self):
        # Track requests by key
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())

        # Track penalties (temporary bans)
        self.penalties: Dict[str, datetime] = {}

        # Audit logger (set by main app)
        self.audit_logger = None

        # Default limits by type
        self.default_limits = {
            RateLimitType.GLOBAL: RateLimitConfig(1000, 30000, 500000),
            RateLimitType.USER: RateLimitConfig(60, 1800, 30000),
            RateLimitType.ORGANIZATION: RateLimitConfig(200, 6000, 100000),
            RateLimitType.ENDPOINT: RateLimitConfig(30, 900, 15000),
            RateLimitType.IP: RateLimitConfig(30, 600, 10000),
        }

        # Custom limits by organization tier
        self.tier_limits = {
            "basic": RateLimitConfig(30, 900, 15000),
            "pro": RateLimitConfig(100, 3000, 50000),
            "enterprise": RateLimitConfig(500, 15000, 250000),
        }

        # Track suspicious activity
        self.suspicious_activity: Dict[str, List[Dict]] = defaultdict(list)

    def _get_key(self, limit_type: RateLimitType, identifier: str) -> str:
        """Generate unique key for tracking"""
        return f"{limit_type}:{identifier}"

    def _clean_old_requests(self, requests: deque, window_seconds: int):
        """Remove requests older than the window"""
        cutoff = time.time() - window_seconds
        while requests and requests[0] < cutoff:
            requests.popleft()

    def check_rate_limit(
        self,
        limit_type: RateLimitType,
        identifier: str,
        config: Optional[RateLimitConfig] = None,
    ) -> Tuple[bool, Optional[int], Dict[str, Any]]:
        """
        Check if request is within rate limits

        Returns:
            - allowed: Whether the request is allowed
            - retry_after: Seconds until next request allowed (if blocked)
            - details: Rate limit details
        """
        key = self._get_key(limit_type, identifier)

        # Check if identifier is currently penalized
        if key in self.penalties:
            penalty_end = self.penalties[key]
            if datetime.utcnow() < penalty_end:
                retry_after = int((penalty_end - datetime.utcnow()).total_seconds())
                return (
                    False,
                    retry_after,
                    {"reason": "penalty", "penalty_ends": penalty_end.isoformat()},
                )
            else:
                # Penalty expired
                del self.penalties[key]

        # Use provided config or default
        if not config:
            config = self.default_limits.get(limit_type)

        current_time = time.time()
        request_times = self.requests[key]

        # Check minute limit
        self._clean_old_requests(request_times, 60)
        minute_count = len(request_times)

        if minute_count >= config.requests_per_minute:
            # Check for burst allowance
            if minute_count < config.requests_per_minute + config.burst_size:
                logger.warning(f"Burst allowance used for {key}")
            else:
                # Apply penalty for repeated violations
                self._apply_penalty(key, config.penalty_duration)
                return (
                    False,
                    60,
                    {
                        "reason": "minute_limit_exceeded",
                        "limit": config.requests_per_minute,
                        "current": minute_count,
                    },
                )

        # Check hour limit
        hour_requests = [t for t in request_times if t > current_time - 3600]
        if len(hour_requests) >= config.requests_per_hour:
            return (
                False,
                3600,
                {
                    "reason": "hour_limit_exceeded",
                    "limit": config.requests_per_hour,
                    "current": len(hour_requests),
                },
            )

        # Check day limit
        day_requests = [t for t in request_times if t > current_time - 86400]
        if len(day_requests) >= config.requests_per_day:
            return (
                False,
                86400,
                {
                    "reason": "day_limit_exceeded",
                    "limit": config.requests_per_day,
                    "current": len(day_requests),
                },
            )

        # Request allowed - record it
        request_times.append(current_time)

        # Calculate remaining limits
        details = {
            "allowed": True,
            "limits": {
                "minute": {
                    "limit": config.requests_per_minute,
                    "remaining": config.requests_per_minute - minute_count - 1,
                    "reset": int(current_time + 60),
                },
                "hour": {
                    "limit": config.requests_per_hour,
                    "remaining": config.requests_per_hour - len(hour_requests) - 1,
                    "reset": int(current_time + 3600),
                },
                "day": {
                    "limit": config.requests_per_day,
                    "remaining": config.requests_per_day - len(day_requests) - 1,
                    "reset": int(current_time + 86400),
                },
            },
        }

        return True, None, details

    def _apply_penalty(self, key: str, duration: int):
        """Apply temporary ban as penalty"""
        self.penalties[key] = datetime.utcnow() + timedelta(seconds=duration)
        logger.warning(f"Penalty applied to {key} for {duration} seconds")

    def check_suspicious_activity(
        self, request: Request, user_id: Optional[str] = None
    ) -> bool:
        """
        Detect suspicious patterns

        Returns True if suspicious activity detected
        """
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        # Pattern 1: Rapid endpoint scanning
        endpoint_key = f"endpoints:{ip_address}"
        endpoint_history = self.suspicious_activity[endpoint_key]

        # Clean old entries (keep last 5 minutes)
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        endpoint_history[:] = [
            e
            for e in endpoint_history
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]

        # Record this access
        endpoint_history.append(
            {"endpoint": request.url.path, "timestamp": datetime.utcnow().isoformat()}
        )

        # Check for scanning pattern (>20 different endpoints in 5 minutes)
        unique_endpoints = set(e["endpoint"] for e in endpoint_history)
        if len(unique_endpoints) > 20:
            logger.warning(f"Endpoint scanning detected from {ip_address}")
            return True

        # Pattern 2: Repeated failed auth attempts
        if request.url.path == "/api/auth/login" and user_id is None:
            auth_key = f"failed_auth:{ip_address}"
            auth_history = self.suspicious_activity[auth_key]

            # Clean old entries
            auth_history[:] = [
                e
                for e in auth_history
                if datetime.fromisoformat(e["timestamp"]) > cutoff
            ]

            if len(auth_history) > 5:  # More than 5 failed attempts in 5 minutes
                logger.warning(f"Brute force attempt detected from {ip_address}")
                return True

        # Pattern 3: Unusual access patterns (e.g., automated tools)
        if self._is_automated_tool(user_agent):
            tool_key = f"automated:{ip_address}"
            if tool_key not in self.suspicious_activity:
                logger.warning(
                    f"Automated tool detected: {user_agent} from {ip_address}"
                )
                self.suspicious_activity[tool_key] = [
                    {"timestamp": datetime.utcnow().isoformat()}
                ]
            return True

        return False

    def _is_automated_tool(self, user_agent: str) -> bool:
        """Detect common automated tools"""
        # Skip check in development mode
        import os

        if os.getenv("ENVIRONMENT", "development") == "development":
            return False

        suspicious_patterns = [
            "bot",
            "crawler",
            "spider",
            "scraper",
            "curl",
            "wget",
            "python-requests",
            "postman",
            "insomnia",
            "scanner",
        ]

        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)

    def get_rate_limit_headers(self, details: Dict[str, Any]) -> Dict[str, str]:
        """Generate standard rate limit headers"""
        if not details.get("allowed"):
            return {}

        minute_limits = details["limits"]["minute"]

        return {
            "X-RateLimit-Limit": str(minute_limits["limit"]),
            "X-RateLimit-Remaining": str(minute_limits["remaining"]),
            "X-RateLimit-Reset": str(minute_limits["reset"]),
            "X-RateLimit-Policy": "sliding-window",
        }


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get identifiers
        ip_address = request.client.host if request.client else "unknown"

        # Extract user info from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        organization_id = getattr(request.state, "organization_id", None)
        organization_tier = getattr(request.state, "organization_tier", "basic")

        # Check for suspicious activity first
        if self.rate_limiter.check_suspicious_activity(request, user_id):
            # Log security event
            if self.rate_limiter.audit_logger:
                from audit_logger import AuditEvent, AuditEventType

                self.rate_limiter.audit_logger.log_event(
                    AuditEvent(
                        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                        user_id=user_id,
                        ip_address=ip_address,
                        details={
                            "endpoint": request.url.path,
                            "user_agent": request.headers.get("user-agent"),
                        },
                    )
                )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Suspicious activity detected. Access temporarily blocked.",
            )

        # Apply rate limits in order of precedence
        checks = []

        # 1. IP-based limit (strictest for unknown users)
        if not user_id:
            allowed, retry_after, details = self.rate_limiter.check_rate_limit(
                RateLimitType.IP, ip_address
            )
            if not allowed:
                checks.append((allowed, retry_after, details, "IP"))

        # 2. User-based limit
        if user_id:
            allowed, retry_after, details = self.rate_limiter.check_rate_limit(
                RateLimitType.USER, user_id
            )
            if not allowed:
                checks.append((allowed, retry_after, details, "User"))

        # 3. Organization-based limit (use tier-specific limits)
        if organization_id:
            org_config = self.rate_limiter.tier_limits.get(organization_tier)
            allowed, retry_after, details = self.rate_limiter.check_rate_limit(
                RateLimitType.ORGANIZATION, organization_id, org_config
            )
            if not allowed:
                checks.append((allowed, retry_after, details, "Organization"))

        # 4. Endpoint-specific limit
        endpoint_key = f"{request.method}:{request.url.path}"
        allowed, retry_after, details = self.rate_limiter.check_rate_limit(
            RateLimitType.ENDPOINT, endpoint_key
        )
        if not allowed:
            checks.append((allowed, retry_after, details, "Endpoint"))

        # If any check failed, return rate limit error
        for allowed, retry_after, details, limit_type in checks:
            if not allowed:
                # Log rate limit event
                if self.rate_limiter.audit_logger:
                    from audit_logger import AuditEvent, AuditEventType

                    self.rate_limiter.audit_logger.log_event(
                        AuditEvent(
                            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                            user_id=user_id,
                            organization_id=organization_id,
                            ip_address=ip_address,
                            details={
                                "limit_type": limit_type,
                                "reason": details.get("reason"),
                                "endpoint": request.url.path,
                            },
                        )
                    )

                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "limit_type": limit_type,
                        "retry_after": retry_after,
                        "details": details,
                    },
                )
                response.headers["Retry-After"] = str(retry_after)
                return response

        # Request allowed - process it
        response = await call_next(request)

        # Add rate limit headers to successful responses
        if user_id and details:
            headers = self.rate_limiter.get_rate_limit_headers(details)
            for header, value in headers.items():
                response.headers[header] = value

        return response


# Global rate limiter instance
rate_limiter = RateLimiter()
