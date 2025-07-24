# security_middleware.py - Enterprise security middleware for legal compliance
import hashlib
import hmac
import secrets
import ipaddress
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import geoip2.database
import logging
from dataclasses import dataclass
import re

from audit_logger import AuditLogger, AuditEvent, AuditEventType

logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Security configuration for middleware"""
    # Security headers
    enable_security_headers: bool = True
    enable_csrf_protection: bool = True
    enable_clickjacking_protection: bool = True
    enable_xss_protection: bool = True
    enable_content_type_sniffing_protection: bool = True
    
    # IP whitelisting
    enable_ip_whitelist: bool = False
    ip_whitelist: List[str] = None
    ip_blacklist: List[str] = None
    
    # Geographic restrictions
    enable_geo_blocking: bool = False
    allowed_countries: List[str] = None
    blocked_countries: List[str] = None
    
    # CSRF settings
    csrf_token_length: int = 32
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "X-CSRF-Token"
    csrf_safe_methods: Set[str] = None
    
    # Content Security Policy
    csp_directives: Dict[str, str] = None
    
    def __post_init__(self):
        if self.ip_whitelist is None:
            self.ip_whitelist = []
        if self.ip_blacklist is None:
            self.ip_blacklist = []
        if self.allowed_countries is None:
            self.allowed_countries = []
        if self.blocked_countries is None:
            self.blocked_countries = []
        if self.csrf_safe_methods is None:
            self.csrf_safe_methods = {"GET", "HEAD", "OPTIONS"}
        if self.csp_directives is None:
            self.csp_directives = {
                "default-src": "'self'",
                "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src": "'self' 'unsafe-inline'",
                "img-src": "'self' data: https:",
                "font-src": "'self'",
                "connect-src": "'self'",
                "frame-ancestors": "'none'",
                "base-uri": "'self'",
                "form-action": "'self'"
            }

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security headers middleware for legal compliance
    Implements OWASP security best practices
    """
    
    def __init__(self, app, config: SecurityConfig = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.audit_logger = None  # Set by main app
        
    async def dispatch(self, request: Request, call_next):
        # Process request
        response = await call_next(request)
        
        # Add security headers
        if self.config.enable_security_headers:
            self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response):
        """Add comprehensive security headers"""
        
        # Strict Transport Security (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy
        csp_header = "; ".join([f"{k} {v}" for k, v in self.config.csp_directives.items()])
        response.headers["Content-Security-Policy"] = csp_header
        
        # XSS Protection (legacy but still useful)
        if self.config.enable_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Clickjacking Protection
        if self.config.enable_clickjacking_protection:
            response.headers["X-Frame-Options"] = "DENY"
            
        # Content Type Sniffing Protection
        if self.config.enable_content_type_sniffing_protection:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "magnetometer=(), gyroscope=(), payment=()"
        )
        
        # Cache Control for sensitive data
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Remove server header
        response.headers.pop("Server", None)
        
        # Add custom security header
        response.headers["X-Legal-Security"] = "Enterprise"

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""
    
    def __init__(self, app, config: SecurityConfig = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.csrf_tokens: Dict[str, datetime] = {}  # In production, use Redis
        
    async def dispatch(self, request: Request, call_next):
        if not self.config.enable_csrf_protection:
            return await call_next(request)
        
        # Skip CSRF for safe methods
        if request.method in self.config.csrf_safe_methods:
            return await call_next(request)
        
        # Skip for API endpoints with Bearer auth
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)
        
        # Validate CSRF token
        csrf_token = request.headers.get(self.config.csrf_header_name)
        if not csrf_token:
            csrf_token = request.cookies.get(self.config.csrf_cookie_name)
        
        if not self._validate_csrf_token(csrf_token):
            logger.warning(f"CSRF validation failed", extra={
                "ip": request.client.host if request.client else "unknown",
                "path": request.url.path
            })
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed"
            )
        
        response = await call_next(request)
        
        # Set new CSRF token in cookie
        new_token = self._generate_csrf_token()
        response.set_cookie(
            key=self.config.csrf_cookie_name,
            value=new_token,
            secure=True,
            httponly=True,
            samesite="strict",
            max_age=3600  # 1 hour
        )
        
        return response
    
    def _generate_csrf_token(self) -> str:
        """Generate secure CSRF token"""
        token = secrets.token_urlsafe(self.config.csrf_token_length)
        self.csrf_tokens[token] = datetime.utcnow()
        
        # Clean old tokens (older than 1 hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self.csrf_tokens = {
            k: v for k, v in self.csrf_tokens.items()
            if v > cutoff
        }
        
        return token
    
    def _validate_csrf_token(self, token: Optional[str]) -> bool:
        """Validate CSRF token"""
        if not token:
            return False
        
        token_time = self.csrf_tokens.get(token)
        if not token_time:
            return False
        
        # Check if token is not expired (1 hour)
        if datetime.utcnow() - token_time > timedelta(hours=1):
            del self.csrf_tokens[token]
            return False
        
        return True

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP whitelisting and geographic access control"""
    
    def __init__(self, app, config: SecurityConfig = None, geoip_db_path: Optional[str] = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.audit_logger = None
        
        # Load GeoIP database if path provided
        self.geoip_reader = None
        if geoip_db_path and self.config.enable_geo_blocking:
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
                logger.info("GeoIP database loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load GeoIP database: {e}")
        
        # Compile IP networks for efficient checking
        self.whitelist_networks = self._compile_ip_list(self.config.ip_whitelist)
        self.blacklist_networks = self._compile_ip_list(self.config.ip_blacklist)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else None
        
        if not client_ip:
            logger.warning("Request without client IP")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client IP required"
            )
        
        # Check IP blacklist first
        if self._is_ip_blacklisted(client_ip):
            self._log_blocked_access(request, client_ip, "ip_blacklisted")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check IP whitelist if enabled
        if self.config.enable_ip_whitelist and self.config.ip_whitelist:
            if not self._is_ip_whitelisted(client_ip):
                self._log_blocked_access(request, client_ip, "not_whitelisted")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied - IP not whitelisted"
                )
        
        # Check geographic restrictions
        if self.config.enable_geo_blocking and self.geoip_reader:
            country = self._get_country_code(client_ip)
            
            if country:
                # Check blocked countries
                if country in self.config.blocked_countries:
                    self._log_blocked_access(request, client_ip, f"country_blocked:{country}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied - Geographic restriction"
                    )
                
                # Check allowed countries (if list is not empty)
                if self.config.allowed_countries and country not in self.config.allowed_countries:
                    self._log_blocked_access(request, client_ip, f"country_not_allowed:{country}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied - Geographic restriction"
                    )
        
        # Add client info to request state
        request.state.client_ip = client_ip
        request.state.client_country = self._get_country_code(client_ip) if self.geoip_reader else None
        
        return await call_next(request)
    
    def _compile_ip_list(self, ip_list: List[str]) -> List[ipaddress.IPv4Network]:
        """Compile IP list into network objects"""
        networks = []
        
        for ip in ip_list:
            try:
                # Handle both individual IPs and CIDR notation
                if '/' in ip:
                    networks.append(ipaddress.ip_network(ip))
                else:
                    networks.append(ipaddress.ip_network(f"{ip}/32"))
            except ValueError as e:
                logger.error(f"Invalid IP address/network: {ip} - {e}")
        
        return networks
    
    def _is_ip_whitelisted(self, ip: str) -> bool:
        """Check if IP is in whitelist"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            return any(ip_addr in network for network in self.whitelist_networks)
        except ValueError:
            return False
    
    def _is_ip_blacklisted(self, ip: str) -> bool:
        """Check if IP is in blacklist"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            return any(ip_addr in network for network in self.blacklist_networks)
        except ValueError:
            return False
    
    def _get_country_code(self, ip: str) -> Optional[str]:
        """Get country code for IP address"""
        if not self.geoip_reader:
            return None
        
        try:
            response = self.geoip_reader.country(ip)
            return response.country.iso_code
        except Exception:
            return None
    
    def _log_blocked_access(self, request: Request, ip: str, reason: str):
        """Log blocked access attempt"""
        if self.audit_logger:
            self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.ACCESS_DENIED,
                ip_address=ip,
                resource_type="endpoint",
                resource_id=request.url.path,
                result="blocked",
                details={
                    "reason": reason,
                    "method": request.method,
                    "user_agent": request.headers.get("user-agent")
                }
            ))

class ContentValidationMiddleware(BaseHTTPMiddleware):
    """Validate request content for security threats"""
    
    def __init__(self, app):
        super().__init__(app)
        self.sql_injection_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            r"(--|;|\/\*|\*\/|xp_|sp_)",
            r"(\b(and|or)\b\s*\d+\s*=\s*\d+)"
        ]
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe",
            r"<object",
            r"<embed"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Only validate for methods with body
        if request.method in ["POST", "PUT", "PATCH"]:
            # Read body
            body = await request.body()
            
            if body:
                body_str = body.decode('utf-8', errors='ignore')
                
                # Check for SQL injection patterns
                for pattern in self.sql_injection_patterns:
                    if re.search(pattern, body_str, re.IGNORECASE):
                        logger.warning(f"Potential SQL injection detected", extra={
                            "ip": request.client.host if request.client else "unknown",
                            "path": request.url.path,
                            "pattern": pattern
                        })
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid request content"
                        )
                
                # Check for XSS patterns
                for pattern in self.xss_patterns:
                    if re.search(pattern, body_str, re.IGNORECASE):
                        logger.warning(f"Potential XSS detected", extra={
                            "ip": request.client.host if request.client else "unknown",
                            "path": request.url.path,
                            "pattern": pattern
                        })
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid request content"
                        )
        
        return await call_next(request)