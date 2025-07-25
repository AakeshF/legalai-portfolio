# security_headers.py - Production security headers and SSL configuration
from fastapi import Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List, Dict, Optional
import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""

    def __init__(self, app, config: Optional[Dict] = None):
        super().__init__(app)
        self.config = config or {}

        # Default security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-DNS-Prefetch-Control": "off",
            "X-Download-Options": "noopen",
        }

        # HSTS header for HTTPS
        if self.config.get("ssl_enabled", True):
            self.security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # CSP nonce for inline scripts
        self.csp_nonce = None

    async def dispatch(self, request: Request, call_next):
        # Generate CSP nonce for this request
        self.csp_nonce = secrets.token_urlsafe(16)

        # Add nonce to request state for use in templates
        request.state.csp_nonce = self.csp_nonce

        # Process request
        response = await call_next(request)

        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value

        # Add Content-Security-Policy with nonce
        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{self.csp_nonce}' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' https://api.openai.com wss:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests",
        ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Add security info header (custom)
        response.headers["X-Security-Policy"] = "Legal-AI-Security-v1"

        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security checks"""

    def __init__(
        self, app, allowed_origins: List[str], allowed_methods: List[str] = None
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins
        self.allowed_methods = allowed_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
        ]

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")

        # Check if origin is allowed
        if origin and origin not in self.allowed_origins:
            logger.warning(f"Blocked CORS request from unauthorized origin: {origin}")
            return Response(content="CORS policy violation", status_code=403)

        response = await call_next(request)

        # Add CORS headers for allowed origins
        if origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                self.allowed_methods
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-Requested-With"
            )
            response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours

        return response


class SSLRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to redirect HTTP to HTTPS in production"""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):
        # Skip for health checks
        if request.url.path in ["/health", "/health/live"]:
            return await call_next(request)

        # Check if request is not HTTPS
        if self.enabled and request.url.scheme == "http":
            # Don't redirect for localhost
            if request.url.hostname not in ["localhost", "127.0.0.1"]:
                https_url = request.url.replace(scheme="https")
                return Response(
                    content="", status_code=301, headers={"Location": str(https_url)}
                )

        return await call_next(request)


class RequestIntegrityMiddleware(BaseHTTPMiddleware):
    """Middleware to verify request integrity for sensitive operations"""

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key
        self.protected_endpoints = [
            "/api/documents/upload",
            "/api/organization/users",
            "/api/auth/password",
            "/api/billing",
        ]

    async def dispatch(self, request: Request, call_next):
        # Check if endpoint needs integrity verification
        if any(request.url.path.startswith(ep) for ep in self.protected_endpoints):
            # Verify request signature if present
            signature = request.headers.get("X-Request-Signature")
            if signature and request.method in ["POST", "PUT", "DELETE"]:
                # Read body for verification (be careful with large files)
                body = await request.body()
                expected_signature = self._calculate_signature(
                    request.method, str(request.url), body
                )

                if signature != expected_signature:
                    logger.warning(f"Invalid request signature for {request.url.path}")
                    return Response(
                        content="Invalid request signature", status_code=403
                    )

        return await call_next(request)

    def _calculate_signature(self, method: str, url: str, body: bytes) -> str:
        """Calculate HMAC signature for request"""
        message = f"{method}:{url}:{body.decode('utf-8', errors='ignore')}"
        return hashlib.sha256(f"{self.secret_key}:{message}".encode()).hexdigest()


# Nginx configuration for SSL/TLS
def generate_nginx_ssl_config() -> str:
    """Generate Nginx SSL configuration for production"""
    return """
# SSL Configuration for Legal AI Backend
server {
    listen 80;
    server_name app.legalai.com www.legalai.com;
    
    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.legalai.com www.legalai.com;
    
    # SSL Certificate Configuration
    ssl_certificate /etc/nginx/ssl/legalai.crt;
    ssl_certificate_key /etc/nginx/ssl/legalai.key;
    
    # SSL Security Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/nginx/ssl/legalai-chain.crt;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=20r/m;
    
    # Proxy to Backend
    location / {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts for long-running AI requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Rate limit specific endpoints
    location /api/auth {
        limit_req zone=auth burst=5 nodelay;
        proxy_pass http://backend:8000;
    }
    
    location /api/documents/upload {
        limit_req zone=upload burst=10 nodelay;
        client_max_body_size 50M;
        proxy_pass http://backend:8000;
    }
    
    # Health check endpoint (no rate limit)
    location /health {
        proxy_pass http://backend:8000;
        access_log off;
    }
    
    # Static files caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
"""
