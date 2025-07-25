"""
Structured logging configuration with context and performance tracking
"""

import logging
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from functools import wraps
import traceback
import uuid

from pythonjsonlogger import jsonlogger


# Context variables for request tracking
request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
org_id_context: ContextVar[Optional[str]] = ContextVar("org_id", default=None)


class StructuredLogger:
    """Enhanced logger with structured output and context."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup JSON formatted handlers."""
        # Remove existing handlers
        self.logger.handlers = []

        # JSON formatter
        formatter = CustomJsonFormatter()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler for errors
        error_handler = logging.FileHandler("logs/errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)

        # Set level
        self.logger.setLevel(logging.INFO)

    def _add_context(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """Add request context to log data."""
        context_data = {
            "request_id": request_id_context.get(),
            "user_id": user_id_context.get(),
            "organization_id": org_id_context.get(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Merge with provided extra data
        return {**context_data, **extra}

    def info(self, message: str, **kwargs):
        """Log info with context."""
        extra = self._add_context(kwargs)
        self.logger.info(message, extra={"structured": extra})

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error with exception details."""
        extra = self._add_context(kwargs)

        if error:
            extra["error_type"] = type(error).__name__
            extra["error_message"] = str(error)
            extra["stacktrace"] = traceback.format_exc()

        self.logger.error(message, extra={"structured": extra})

    def warning(self, message: str, **kwargs):
        """Log warning with context."""
        extra = self._add_context(kwargs)
        self.logger.warning(message, extra={"structured": extra})

    def debug(self, message: str, **kwargs):
        """Log debug with context."""
        extra = self._add_context(kwargs)
        self.logger.debug(message, extra={"structured": extra})

    def performance(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics."""
        extra = self._add_context(
            {
                "operation": operation,
                "duration_ms": duration_ms,
                "performance_metric": True,
                **kwargs,
            }
        )
        self.logger.info(f"Performance: {operation}", extra={"structured": extra})


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with structured data."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # Add level name
        log_record["level"] = record.levelname

        # Add module info
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add structured data if present
        if hasattr(record, "structured"):
            log_record.update(record.structured)


# Performance tracking decorator
def track_performance(operation: str, logger: Optional[StructuredLogger] = None):
    """Decorator to track function performance."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = None
            error = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000

                if logger:
                    logger.performance(
                        operation=operation,
                        duration_ms=duration_ms,
                        success=error is None,
                        function=func.__name__,
                    )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = None
            error = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000

                if logger:
                    logger.performance(
                        operation=operation,
                        duration_ms=duration_ms,
                        success=error is None,
                        function=func.__name__,
                    )

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Request tracking middleware
class RequestTrackingMiddleware:
    """Middleware to track requests with unique IDs."""

    def __init__(self, app):
        self.app = app
        self.logger = StructuredLogger(__name__)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate request ID
            request_id = str(uuid.uuid4())
            request_id_context.set(request_id)

            # Track request start
            start_time = time.time()

            # Add request ID to response headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers[b"x-request-id"] = request_id.encode()
                    message["headers"] = list(headers.items())
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                # Log request completion
                duration_ms = (time.time() - start_time) * 1000

                self.logger.info(
                    "Request completed",
                    method=scope.get("method"),
                    path=scope.get("path"),
                    duration_ms=duration_ms,
                    request_id=request_id,
                )
        else:
            await self.app(scope, receive, send)


# Error tracking
class ErrorTracker:
    """Centralized error tracking and reporting."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)

    def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """Track an error with context."""
        error_id = str(uuid.uuid4())

        self.logger.error(
            f"Error tracked: {type(error).__name__}",
            error=error,
            error_id=error_id,
            context=context or {},
        )

        # Here you could send to Sentry, Datadog, etc.

        return error_id

    def track_validation_error(self, field: str, message: str, value: Any = None):
        """Track validation errors."""
        self.logger.warning(
            "Validation error",
            field=field,
            message=message,
            value=str(value)[:100] if value else None,
            error_type="validation",
        )

    def track_business_error(self, code: str, message: str, **kwargs):
        """Track business logic errors."""
        self.logger.warning(
            "Business rule violation",
            error_code=code,
            message=message,
            error_type="business",
            **kwargs,
        )


# Performance metrics
class PerformanceMetrics:
    """Track and report performance metrics."""

    def __init__(self):
        self.logger = StructuredLogger(__name__)
        self.metrics = {}

    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value."""
        self.logger.info(
            f"Metric: {name}",
            metric_name=name,
            metric_value=value,
            metric_tags=tags or {},
            metric_type="gauge",
        )

    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        self.logger.info(
            f"Counter: {name}",
            metric_name=name,
            metric_value=value,
            metric_tags=tags or {},
            metric_type="counter",
        )

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram value."""
        self.logger.info(
            f"Histogram: {name}",
            metric_name=name,
            metric_value=value,
            metric_tags=tags or {},
            metric_type="histogram",
        )


# Initialize global instances
error_tracker = ErrorTracker()
performance_metrics = PerformanceMetrics()


# Helper function to set request context
def set_request_context(
    request_id: str, user_id: Optional[str] = None, org_id: Optional[str] = None
):
    """Set request context for logging."""
    request_id_context.set(request_id)
    if user_id:
        user_id_context.set(user_id)
    if org_id:
        org_id_context.set(org_id)
