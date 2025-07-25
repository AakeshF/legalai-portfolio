# error_handler.py - Enterprise-grade error handling with retries and user-friendly messages
import logging
import traceback
import asyncio
from typing import Any, Callable, Dict, Optional, Union, Type, List
from functools import wraps
from datetime import datetime
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
import httpx

logger = logging.getLogger(__name__)


class ErrorCategory:
    """Error categories for different types of failures"""

    VALIDATION = "validation_error"
    AUTHENTICATION = "authentication_error"
    AUTHORIZATION = "authorization_error"
    NOT_FOUND = "not_found"
    DATABASE = "database_error"
    EXTERNAL_SERVICE = "external_service_error"
    FILE_PROCESSING = "file_processing_error"
    AI_SERVICE = "ai_service_error"
    RATE_LIMIT = "rate_limit_error"
    INTERNAL = "internal_error"


class UserFriendlyError(HTTPException):
    """Custom exception with user-friendly messages"""

    def __init__(
        self,
        status_code: int,
        user_message: str,
        technical_details: Optional[str] = None,
        error_category: str = ErrorCategory.INTERNAL,
        retry_after: Optional[int] = None,
    ):
        self.user_message = user_message
        self.technical_details = technical_details
        self.error_category = error_category
        self.retry_after = retry_after
        super().__init__(status_code=status_code, detail=user_message)


class ErrorHandler:
    """Centralized error handling with retry logic and user-friendly messages"""

    # User-friendly error messages
    ERROR_MESSAGES = {
        ErrorCategory.VALIDATION: {
            "default": "The provided data is invalid. Please check your input and try again.",
            "file_size": "The file is too large. Maximum allowed size is {max_size}MB.",
            "file_type": "This file type is not supported. Please upload {allowed_types} files.",
            "missing_field": "Required field '{field}' is missing.",
        },
        ErrorCategory.AUTHENTICATION: {
            "default": "Authentication failed. Please log in again.",
            "expired_token": "Your session has expired. Please log in again.",
            "invalid_credentials": "Invalid email or password.",
        },
        ErrorCategory.AUTHORIZATION: {
            "default": "You don't have permission to perform this action.",
            "insufficient_role": "This action requires {required_role} privileges.",
            "organization_mismatch": "You can only access data from your own organization.",
        },
        ErrorCategory.NOT_FOUND: {
            "default": "The requested resource was not found.",
            "document": "Document not found. It may have been deleted or you may not have access.",
            "user": "User not found.",
            "organization": "Organization not found.",
        },
        ErrorCategory.DATABASE: {
            "default": "A database error occurred. Our team has been notified.",
            "connection": "Unable to connect to database. Please try again in a few moments.",
            "integrity": "This operation would violate data integrity rules.",
            "timeout": "Database operation timed out. Please try again.",
        },
        ErrorCategory.EXTERNAL_SERVICE: {
            "default": "An external service is temporarily unavailable. Please try again later.",
            "ai_service": "AI analysis service is temporarily unavailable. Your document has been queued for processing.",
            "email_service": "Email service is unavailable. The operation completed but notifications were not sent.",
        },
        ErrorCategory.FILE_PROCESSING: {
            "default": "Failed to process the file. Please ensure it's not corrupted.",
            "extraction": "Unable to extract text from this document. Please try a different format.",
            "corrupted": "The file appears to be corrupted. Please upload a valid file.",
        },
        ErrorCategory.AI_SERVICE: {
            "default": "AI analysis failed. The document will be retried automatically.",
            "quota_exceeded": "AI service quota exceeded. Please try again tomorrow or contact support.",
            "invalid_response": "Received invalid response from AI service. Retrying with fallback provider.",
        },
        ErrorCategory.RATE_LIMIT: {
            "default": "Too many requests. Please wait {retry_after} seconds before trying again.",
            "organization": "Your organization has exceeded its rate limit. Please upgrade your plan or wait.",
        },
        ErrorCategory.INTERNAL: {
            "default": "An unexpected error occurred. Our team has been notified and is working on it.",
        },
    }

    @staticmethod
    def get_user_message(category: str, error_type: str = "default", **kwargs) -> str:
        """Get user-friendly error message"""
        messages = ErrorHandler.ERROR_MESSAGES.get(
            category, ErrorHandler.ERROR_MESSAGES[ErrorCategory.INTERNAL]
        )
        template = messages.get(error_type, messages["default"])
        return template.format(**kwargs)

    @staticmethod
    def handle_database_error(error: SQLAlchemyError) -> UserFriendlyError:
        """Convert database errors to user-friendly messages"""
        if isinstance(error, OperationalError):
            if "connection" in str(error).lower():
                return UserFriendlyError(
                    status_code=503,
                    user_message=ErrorHandler.get_user_message(
                        ErrorCategory.DATABASE, "connection"
                    ),
                    technical_details=str(error),
                    error_category=ErrorCategory.DATABASE,
                    retry_after=30,
                )
            elif "timeout" in str(error).lower():
                return UserFriendlyError(
                    status_code=504,
                    user_message=ErrorHandler.get_user_message(
                        ErrorCategory.DATABASE, "timeout"
                    ),
                    technical_details=str(error),
                    error_category=ErrorCategory.DATABASE,
                    retry_after=10,
                )
        elif isinstance(error, IntegrityError):
            return UserFriendlyError(
                status_code=409,
                user_message=ErrorHandler.get_user_message(
                    ErrorCategory.DATABASE, "integrity"
                ),
                technical_details=str(error),
                error_category=ErrorCategory.DATABASE,
            )

        return UserFriendlyError(
            status_code=500,
            user_message=ErrorHandler.get_user_message(ErrorCategory.DATABASE),
            technical_details=str(error),
            error_category=ErrorCategory.DATABASE,
        )

    @staticmethod
    def handle_http_error(
        error: httpx.HTTPError, service_name: str = "external"
    ) -> UserFriendlyError:
        """Convert HTTP errors to user-friendly messages"""
        if isinstance(error, httpx.TimeoutException):
            return UserFriendlyError(
                status_code=504,
                user_message=f"{service_name} service timed out. Please try again.",
                technical_details=str(error),
                error_category=ErrorCategory.EXTERNAL_SERVICE,
                retry_after=10,
            )
        elif isinstance(error, httpx.ConnectError):
            return UserFriendlyError(
                status_code=503,
                user_message=f"Cannot connect to {service_name} service. Please try again later.",
                technical_details=str(error),
                error_category=ErrorCategory.EXTERNAL_SERVICE,
                retry_after=60,
            )

        return UserFriendlyError(
            status_code=502,
            user_message=ErrorHandler.get_user_message(ErrorCategory.EXTERNAL_SERVICE),
            technical_details=str(error),
            error_category=ErrorCategory.EXTERNAL_SERVICE,
        )


def with_error_handling(
    category: str = ErrorCategory.INTERNAL,
    user_message: Optional[str] = None,
    log_errors: bool = True,
):
    """Decorator for consistent error handling across endpoints"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except UserFriendlyError:
                raise  # Re-raise user-friendly errors as-is
            except HTTPException:
                raise  # Re-raise HTTP exceptions as-is
            except SQLAlchemyError as e:
                if log_errors:
                    logger.error(
                        f"Database error in {func.__name__}: {str(e)}", exc_info=True
                    )
                raise ErrorHandler.handle_database_error(e)
            except Exception as e:
                if log_errors:
                    logger.error(
                        f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True
                    )
                raise UserFriendlyError(
                    status_code=500,
                    user_message=user_message
                    or ErrorHandler.get_user_message(category),
                    technical_details=str(e),
                    error_category=category,
                )

        return wrapper

    return decorator


class RetryConfig:
    """Configuration for retry logic"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on: Optional[List[Type[Exception]]] = None,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on = retry_on or [
            httpx.TimeoutException,
            httpx.ConnectError,
            OperationalError,
        ]


async def retry_with_backoff(
    func: Callable,
    config: RetryConfig = RetryConfig(),
    on_retry: Optional[Callable] = None,
) -> Any:
    """Execute function with exponential backoff retry"""
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            # Check if we should retry this exception
            should_retry = any(isinstance(e, exc_type) for exc_type in config.retry_on)

            if not should_retry or attempt == config.max_attempts - 1:
                raise

            # Calculate delay with exponential backoff
            delay = min(
                config.initial_delay * (config.exponential_base**attempt),
                config.max_delay,
            )

            logger.warning(
                f"Retry attempt {attempt + 1}/{config.max_attempts} after {delay}s delay. "
                f"Error: {str(e)}"
            )

            if on_retry:
                await on_retry(attempt + 1, delay, e)

            await asyncio.sleep(delay)

    raise last_exception


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for FastAPI"""
    # Log the full exception
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
            "traceback": traceback.format_exc(),
        },
    )

    # Convert to user-friendly error
    if isinstance(exc, UserFriendlyError):
        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.user_message,
                    "category": exc.error_category,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            },
        )
        if exc.retry_after:
            response.headers["Retry-After"] = str(exc.retry_after)
        return response

    # Default error response
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "An unexpected error occurred. Our team has been notified.",
                "category": ErrorCategory.INTERNAL,
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )
