# middleware.py - Request/Response monitoring middleware
import time
import uuid
import json
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import logging
from datetime import datetime

from logger import get_logger, log_event, log_metric

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses with detailed metrics
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.excluded_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Skip logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Extract request details
        request_details = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length", 0),
        }

        # Log request
        log_event(
            logger,
            "http_request_received",
            f"Received {request.method} {request.url.path}",
            **request_details,
        )

        # Process request
        response = None
        error_details = None

        try:
            response = await call_next(request)
        except Exception as e:
            error_details = {"error": str(e), "error_type": type(e).__name__}
            logger.error(
                f"Request {request_id} failed with unhandled exception",
                extra={**request_details, **error_details},
                exc_info=True,
            )
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Log response
            response_details = {
                "request_id": request_id,
                "duration_seconds": duration,
                "status_code": response.status_code if response else 500,
                "method": request.method,
                "path": request.url.path,
            }

            if error_details:
                response_details.update(error_details)

            # Log completion
            log_event(
                logger,
                "http_request_completed",
                f"Completed {request.method} {request.url.path} - {response.status_code if response else 500}",
                **response_details,
            )

            # Log metrics
            log_metric(
                logger,
                "http_request_duration",
                duration,
                unit="seconds",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code if response else 500,
            )

            # Add response headers
            if response:
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response


class ErrorHandlingMiddleware:
    """
    Middleware for consistent error handling and logging
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self.logger = get_logger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)

                # Log errors
                if status_code >= 400:
                    request = Request(scope, receive)
                    request_id = getattr(request.state, "request_id", "unknown")

                    self.logger.warning(
                        f"Error response: {status_code}",
                        extra={
                            "request_id": request_id,
                            "status_code": status_code,
                            "method": scope["method"],
                            "path": scope["path"],
                        },
                    )

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            self.logger.error(
                "Unhandled exception in application",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "method": scope["method"],
                    "path": scope["path"],
                },
                exc_info=True,
            )

            # Send error response
            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": json.dumps(
                        {
                            "error": "Internal server error",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ).encode(),
                }
            )


class MetricsMiddleware:
    """
    Middleware for collecting application metrics
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self.logger = get_logger(__name__)
        self.request_count = 0
        self.error_count = 0
        self.response_times = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        status_code = 200

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            self.request_count += 1
            await self.app(scope, receive, send_wrapper)
        except Exception:
            self.error_count += 1
            raise
        finally:
            duration = time.time() - start_time
            self.response_times.append(duration)

            # Keep only last 1000 response times
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]

            # Log metrics periodically (every 100 requests)
            if self.request_count % 100 == 0:
                avg_response_time = sum(self.response_times) / len(self.response_times)

                log_metric(
                    self.logger,
                    "application_metrics",
                    self.request_count,
                    unit="requests",
                    error_count=self.error_count,
                    avg_response_time=avg_response_time,
                    active_response_samples=len(self.response_times),
                )


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])

                # Add security headers
                security_headers = [
                    (b"X-Content-Type-Options", b"nosniff"),
                    (b"X-Frame-Options", b"DENY"),
                    (b"X-XSS-Protection", b"1; mode=block"),
                    (
                        b"Strict-Transport-Security",
                        b"max-age=31536000; includeSubDomains",
                    ),
                    (b"Referrer-Policy", b"strict-origin-when-cross-origin"),
                    (
                        b"Permissions-Policy",
                        b"geolocation=(), microphone=(), camera=()",
                    ),
                ]

                headers.extend(security_headers)
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)


# Rate limiting storage (in production, use Redis)
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}
        self.logger = get_logger(__name__)

    def is_allowed(self, client_ip: str) -> bool:
        current_time = time.time()
        minute_ago = current_time - 60

        # Clean old entries
        if client_ip in self.requests:
            self.requests[client_ip] = [
                timestamp
                for timestamp in self.requests[client_ip]
                if timestamp > minute_ago
            ]

        # Check rate limit
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        if len(self.requests[client_ip]) >= self.requests_per_minute:
            self.logger.warning(
                f"Rate limit exceeded for {client_ip}",
                extra={
                    "client_ip": client_ip,
                    "requests_count": len(self.requests[client_ip]),
                    "limit": self.requests_per_minute,
                },
            )
            return False

        self.requests[client_ip].append(current_time)
        return True


class RateLimitingMiddleware:
    """
    Simple rate limiting middleware
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        self.app = app
        self.rate_limiter = RateLimiter(requests_per_minute)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get client IP
        client_host = None
        for key, value in scope.get("headers", []):
            if key == b"x-forwarded-for":
                client_host = value.decode().split(",")[0].strip()
                break

        if not client_host and scope.get("client"):
            client_host = scope["client"][0]

        # Check rate limit
        if client_host and not self.rate_limiter.is_allowed(client_host):
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"retry-after", b"60"],
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": json.dumps(
                        {"error": "Rate limit exceeded", "retry_after": 60}
                    ).encode(),
                }
            )
            return

        await self.app(scope, receive, send)
