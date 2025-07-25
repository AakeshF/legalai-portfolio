"""
Enhanced error handling with graceful responses and proper status codes
"""

from typing import Dict, Any, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import uuid

from structured_logging import StructuredLogger, error_tracker


logger = StructuredLogger(__name__)


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppError):
    """Validation error."""

    def __init__(self, message: str, field: str, value: Any = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field": field, "value": value},
        )


class AuthenticationError(AppError):
    """Authentication error."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(AppError):
    """Authorization error."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ResourceNotFoundError(AppError):
    """Resource not found error."""

    def __init__(self, resource: str, id: Union[str, int]):
        super().__init__(
            message=f"{resource} not found",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "id": str(id)},
        )


class BusinessLogicError(AppError):
    """Business logic error."""

    def __init__(
        self, message: str, code: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class RateLimitError(AppError):
    """Rate limit exceeded error."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Please retry after {retry_after} seconds",
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after},
        )


class ExternalServiceError(AppError):
    """External service error."""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service},
        )


def create_error_response(
    error: Exception, request_id: Optional[str] = None
) -> JSONResponse:
    """Create standardized error response."""

    # Generate error ID for tracking
    error_id = str(uuid.uuid4())

    # Default error response
    response = {
        "error": {
            "message": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
            "error_id": error_id,
            "request_id": request_id,
        }
    }

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Handle different error types
    if isinstance(error, AppError):
        response["error"]["message"] = error.message
        response["error"]["code"] = error.code
        if error.details:
            response["error"]["details"] = error.details
        status_code = error.status_code

    elif isinstance(error, HTTPException):
        response["error"]["message"] = error.detail
        response["error"]["code"] = f"HTTP_{error.status_code}"
        status_code = error.status_code

    elif isinstance(error, RequestValidationError):
        response["error"]["message"] = "Validation error"
        response["error"]["code"] = "VALIDATION_ERROR"
        response["error"]["details"] = {
            "errors": [
                {
                    "field": ".".join(str(x) for x in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"],
                }
                for err in error.errors()
            ]
        }
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    # Track error
    error_tracker.track_error(
        error,
        context={
            "error_id": error_id,
            "request_id": request_id,
            "status_code": status_code,
        },
    )

    return JSONResponse(
        content=response,
        status_code=status_code,
        headers={"X-Error-ID": error_id, "X-Request-ID": request_id or ""},
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for all unhandled exceptions."""

    # Get request ID from headers or context
    request_id = request.headers.get("X-Request-ID")

    # Log the error
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        error=exc,
        path=request.url.path,
        method=request.method,
    )

    return create_error_response(exc, request_id)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors."""
    request_id = request.headers.get("X-Request-ID")

    # Log validation errors
    for error in exc.errors():
        error_tracker.track_validation_error(
            field=".".join(str(x) for x in error["loc"]),
            message=error["msg"],
            value=error.get("input"),
        )

    return create_error_response(exc, request_id)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    request_id = request.headers.get("X-Request-ID")

    # Log HTTP errors (except 404s to reduce noise)
    if exc.status_code != status.HTTP_404_NOT_FOUND:
        logger.warning(
            f"HTTP exception: {exc.status_code}",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )

    return create_error_response(exc, request_id)


# Error handling decorators
def handle_errors(operation: str):
    """Decorator to handle errors in service methods."""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AppError:
                raise  # Re-raise app errors
            except Exception as e:
                logger.error(
                    f"Error in {operation}",
                    error=e,
                    operation=operation,
                    function=func.__name__,
                )
                raise AppError(
                    message=f"Failed to {operation}",
                    code="OPERATION_FAILED",
                    details={"operation": operation},
                )

        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppError:
                raise  # Re-raise app errors
            except Exception as e:
                logger.error(
                    f"Error in {operation}",
                    error=e,
                    operation=operation,
                    function=func.__name__,
                )
                raise AppError(
                    message=f"Failed to {operation}",
                    code="OPERATION_FAILED",
                    details={"operation": operation},
                )

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Validation helpers
def validate_required(value: Any, field: str) -> Any:
    """Validate required field."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field} is required", field)
    return value


def validate_email(email: str) -> str:
    """Validate email format."""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, email):
        raise ValidationError("Invalid email format", "email", email)

    return email.lower()


def validate_file_type(file_type: str, allowed_types: list) -> str:
    """Validate file type."""
    if file_type not in allowed_types:
        raise ValidationError(
            f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
            "file_type",
            file_type,
        )
    return file_type


def validate_pagination(skip: int = 0, limit: int = 100) -> tuple:
    """Validate pagination parameters."""
    if skip < 0:
        raise ValidationError("Skip must be non-negative", "skip", skip)

    if limit < 1:
        raise ValidationError("Limit must be positive", "limit", limit)

    if limit > 1000:
        raise ValidationError("Limit cannot exceed 1000", "limit", limit)

    return skip, limit


# Business logic validators
def validate_document_access(document_org_id: int, user_org_id: int):
    """Validate user has access to document."""
    if document_org_id != user_org_id:
        raise AuthorizationError("You don't have access to this document")


def validate_user_active(is_active: bool, user_email: str):
    """Validate user is active."""
    if not is_active:
        error_tracker.track_business_error(
            code="INACTIVE_USER_ACCESS",
            message="Inactive user attempted access",
            user_email=user_email,
        )
        raise AuthorizationError("Your account has been deactivated")


def validate_organization_active(is_active: bool, org_name: str):
    """Validate organization is active."""
    if not is_active:
        error_tracker.track_business_error(
            code="INACTIVE_ORG_ACCESS",
            message="Inactive organization access attempt",
            organization=org_name,
        )
        raise AuthorizationError("Your organization account is inactive")
