# logger.py - Structured JSON logging configuration for production
import logging
import sys
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger
import traceback
from functools import wraps
import time

# Custom JSON formatter with additional fields
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add module and function info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add process and thread info
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
            log_record['exception_type'] = record.exc_info[0].__name__
        
        # Add environment info
        log_record['environment'] = os.environ.get('ENVIRONMENT', 'development')
        log_record['service'] = 'legal-ai-backend'

# Configure root logger
def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """
    Setup structured logging for production
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' for production, 'simple' for development)
    """
    # Remove existing handlers
    logging.root.handlers = []
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Set format based on environment
    if log_format == "json":
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'msg': 'message'}
        )
    else:
        # Simple format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    
    # Configure root logger
    logging.root.setLevel(getattr(logging, log_level.upper()))
    logging.root.addHandler(handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Suppress noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

# Create logger factory
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)

# Logging context manager for operations
class LoggingContext:
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"{self.operation} started", extra=self.context)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                f"{self.operation} failed",
                extra={
                    **self.context,
                    "duration_seconds": duration,
                    "error": str(exc_val),
                    "error_type": exc_type.__name__
                },
                exc_info=True
            )
        else:
            self.logger.info(
                f"{self.operation} completed",
                extra={
                    **self.context,
                    "duration_seconds": duration
                }
            )

# Decorator for logging function calls
def log_function_call(logger: logging.Logger):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            logger.debug(
                f"Function {func_name} called",
                extra={
                    "function": func_name,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
            )
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.debug(
                    f"Function {func_name} succeeded",
                    extra={
                        "function": func_name,
                        "duration_seconds": duration
                    }
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Function {func_name} failed",
                    extra={
                        "function": func_name,
                        "duration_seconds": duration,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            logger.debug(
                f"Function {func_name} called",
                extra={
                    "function": func_name,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
            )
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.debug(
                    f"Function {func_name} succeeded",
                    extra={
                        "function": func_name,
                        "duration_seconds": duration
                    }
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Function {func_name} failed",
                    extra={
                        "function": func_name,
                        "duration_seconds": duration,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Log structured events
def log_event(logger: logging.Logger, event_type: str, message: str, **data):
    """Log a structured event with additional data"""
    logger.info(
        message,
        extra={
            "event_type": event_type,
            "event_data": data
        }
    )

# Log metrics
def log_metric(logger: logging.Logger, metric_name: str, value: float, unit: str = "count", **tags):
    """Log a metric with value and tags"""
    logger.info(
        f"Metric: {metric_name}",
        extra={
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
            "metric_tags": tags
        }
    )

import os

# Initialize logging on module import
setup_logging(
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_format=os.environ.get("LOG_FORMAT", "json" if os.environ.get("ENVIRONMENT") == "production" else "simple")
)