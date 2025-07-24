# auth_middleware.py - Authentication middleware for JWT validation and request context
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional, Callable
from datetime import datetime
import logging

from auth_utils import decode_access_token
from database import SessionLocal
from models import User, Organization
from config import settings

logger = logging.getLogger(__name__)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/",
    "/health",
    "/health/detailed",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    # Temporarily add RAG endpoints for testing
    "/api/documents/semantic-search",
    "/api/chat/rag",
    # Test endpoints without auth
    "/api/test/semantic-search",
    "/api/test/rag-chat",
    "/api/test/simple-ollama"
}

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate JWT tokens and add user/organization context to requests
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check if authentication is disabled globally
        if settings.disable_auth:
            return await call_next(request)
        
        # Skip authentication for public endpoints
        if request.url.path in PUBLIC_ENDPOINTS:
            return await call_next(request)
        
        # Skip authentication for static files and favicon
        if request.url.path.startswith("/static") or request.url.path == "/favicon.ico":
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authorization header missing"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate Bearer token format
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Decode and validate token
        payload = decode_access_token(token)
        
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Check token type
        if payload.get("type") != "access":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token type"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Get user and organization from database
        db = SessionLocal()
        try:
            user = db.query(User).filter(
                User.id == payload.get("sub"),
                User.is_active == True
            ).first()
            
            if not user:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "User not found or inactive"}
                )
            
            # Check if organization is active
            if not user.organization or not user.organization.is_active:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Organization is not active"}
                )
            
            # Add user and organization to request state
            request.state.user = user
            request.state.organization = user.organization
            request.state.user_id = user.id
            request.state.organization_id = user.organization_id
            request.state.user_role = user.role
            
            # Log access
            logger.debug(
                f"Authenticated request: {request.method} {request.url.path} "
                f"by user {user.email} from org {user.organization.name}"
            )
            
        finally:
            db.close()
        
        # Continue processing request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware for authentication endpoints
    """
    
    def __init__(self, app, requests_per_minute: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # IP -> [(timestamp, count)]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Only rate limit auth endpoints
        if not request.url.path.startswith("/api/auth"):
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Clean old entries (older than 1 minute)
        current_time = datetime.utcnow()
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                (ts, count) for ts, count in self.request_counts[client_ip]
                if (current_time - ts).total_seconds() < 60
            ]
        
        # Count requests in the last minute
        request_count = sum(count for _, count in self.request_counts.get(client_ip, []))
        
        # Check rate limit
        if request_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record this request
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        self.request_counts[client_ip].append((current_time, 1))
        
        # Continue processing
        return await call_next(request)

def get_current_user(request: Request) -> User:
    """
    Dependency to get the current authenticated user from request state
    """
    # Check if authentication is disabled
    if settings.disable_auth:
        # Return a dummy user for development
        dummy_user = User()
        dummy_user.id = "dev-user-id"
        dummy_user.email = "[email@example.com]"
        dummy_user.organization_id = "dev-org-id"
        dummy_user.is_active = True
        dummy_user.role = "admin"
        return dummy_user
    
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return request.state.user

def get_current_organization(request: Request) -> Organization:
    """
    Dependency to get the current organization from request state
    """
    # Check if authentication is disabled
    if settings.disable_auth:
        # Return a dummy organization for development
        dummy_org = Organization()
        dummy_org.id = "dev-org-id"
        dummy_org.name = "Development Organization"
        dummy_org.is_active = True
        return dummy_org
    
    if not hasattr(request.state, "organization"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return request.state.organization

def require_role(allowed_roles: list):
    """
    Dependency factory to require specific user roles
    """
    def role_checker(request: Request):
        user = get_current_user(request)
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker

# Convenience dependencies
require_admin = require_role(["admin"])
require_attorney_or_admin = require_role(["attorney", "admin"])
