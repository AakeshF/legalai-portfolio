# frontend_auth_adapter.py - Adapter to match frontend auth expectations
from pydantic import BaseModel, EmailStr, validator
from typing import Optional


class FrontendRegisterRequest(BaseModel):
    """Registration request format expected by frontend"""

    email: EmailStr
    password: str
    full_name: str
    organization_name: str

    @validator("full_name")
    def validate_full_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Full name is required")
        return v.strip()

    def to_backend_format(self):
        """Convert to backend RegisterRequest format"""
        # Split full name into first and last
        name_parts = self.full_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        return {
            "billing_email": self.email,  # Use same email for billing
            "admin_email": self.email,
            "admin_password": self.password,
            "admin_first_name": first_name,
            "admin_last_name": last_name,
            "organization_name": self.organization_name,
        }


class FrontendLoginResponse(BaseModel):
    """Login response format expected by frontend"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict  # UserResponse serialized to dict


class FrontendRefreshRequest(BaseModel):
    """Refresh token request format expected by frontend"""

    refresh_token: str
