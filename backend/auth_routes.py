# auth_routes.py - Authentication endpoints for user registration and login
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict, Union
import uuid
from datetime import datetime, timezone

from database import get_db
from models import User, Organization
from schemas import (
    UserLogin, Token, UserResponse, OrganizationResponse,
    RegisterRequest, RegisterResponse, TokenData
)
from auth_utils import (
    hash_password, verify_password, create_user_tokens, decode_access_token,
    validate_email, validate_password, create_password_reset_token,
    decode_password_reset_token, decode_refresh_token, send_password_reset_email,
    send_welcome_email, generate_temp_password
)
from frontend_auth_adapter import (
    FrontendRegisterRequest, FrontendLoginResponse, FrontendRefreshRequest
)
from logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()

# Frontend-compatible register endpoint
@router.post("/register")
async def register_frontend(
    request: Union[FrontendRegisterRequest, RegisterRequest],
    db: Session = Depends(get_db)
):
    """Register a new organization and admin user (supports both frontend and backend formats)"""
    try:
        # Check if this is a frontend request
        if isinstance(request, FrontendRegisterRequest) or hasattr(request, 'full_name'):
            # Convert frontend format to backend format
            frontend_req = FrontendRegisterRequest(**request.dict())
            backend_data = frontend_req.to_backend_format()
            request = RegisterRequest(**backend_data)
        
        # Original registration logic continues...
        return await register_backend(request, db)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise

async def register_backend(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new organization and admin user"""
    try:
        # Log the incoming request for debugging
        logger.info(f"Registration request received: {request.dict()}")
        # Validate email formats
        if not validate_email(request.billing_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid billing email format"
            )
        
        if not validate_email(request.admin_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid admin email format"
            )
        
        # Validate password
        is_valid, message = validate_password(request.admin_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Check if organization name already exists
        existing_org = db.query(Organization).filter(
            Organization.name == request.organization_name
        ).first()
        
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name already exists"
            )
        
        # Check if admin email already exists
        existing_user = db.query(User).filter(
            User.email == request.admin_email
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create organization
        organization = Organization(
            id=str(uuid.uuid4()),
            name=request.organization_name,
            billing_email=request.billing_email,
            subscription_tier="basic",
            created_at=datetime.now(timezone.utc),
            is_active=True
        )
        db.add(organization)
        
        # Create admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            email=request.admin_email,
            password_hash=hash_password(request.admin_password),
            first_name=request.admin_first_name,
            last_name=request.admin_last_name,
            role="admin",
            organization_id=organization.id,
            created_at=datetime.now(timezone.utc),
            is_active=True
        )
        db.add(admin_user)
        
        # Commit both together
        db.commit()
        db.refresh(organization)
        db.refresh(admin_user)
        
        # Create access and refresh tokens
        tokens = create_user_tokens(
            admin_user.id,
            admin_user.email,
            admin_user.organization_id,
            admin_user.role
        )
        
        # Send welcome email
        await send_welcome_email(
            admin_user.email,
            admin_user.full_name,
            organization.name
        )
        
        logger.info(
            f"New organization registered: {organization.name} with admin: {admin_user.email}"
        )
        
        return {
            "organization": OrganizationResponse.model_validate(organization),
            "user": UserResponse.model_validate(admin_user),
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": tokens["token_type"],
            "expires_in": tokens["expires_in"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login")
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Login with email and password (returns user data for frontend compatibility)"""
    try:
        # Log the login attempt for debugging
        logger.info(f"Login attempt for email: {credentials.email}")
        # Find user by email
        user = db.query(User).filter(
            User.email == credentials.email
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Check if organization is active
        organization = db.query(Organization).filter(
            Organization.id == user.organization_id
        ).first()
        
        if not organization or not organization.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization is not active"
            )
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        # Create access and refresh tokens
        tokens = create_user_tokens(
            user.id,
            user.email,
            user.organization_id,
            user.role
        )
        
        logger.info(f"User logged in: {user.email}")
        
        # Return tokens with user data for frontend compatibility
        return FrontendLoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
            user=UserResponse.model_validate(user).dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        # Return more specific error for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user info from token"""
    try:
        # Decode token
        token_data = decode_access_token(credentials.credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Get user from database
        user = db.query(User).filter(
            User.id == token_data.get("sub")
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user info"
        )

# Dependency to get current user from token
async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user"""
    try:
        # Decode token
        token_data = decode_access_token(credentials.credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = db.query(User).filter(
            User.id == token_data.get("sub")
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Check organization is active
        if not user.organization.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization is not active"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

# Optional: Admin-only dependency
async def get_admin_user(
    current_user: User = Depends(get_current_user_dependency)
) -> User:
    """Dependency to ensure user is an admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.post("/refresh")
async def refresh_token(
    body: Union[FrontendRefreshRequest, Dict] = Body(...),
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Handle both frontend format (JSON body) and direct string
        if isinstance(body, dict):
            refresh_token = body.get("refresh_token")
        elif isinstance(body, FrontendRefreshRequest):
            refresh_token = body.refresh_token
        else:
            refresh_token = str(body)
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required"
            )
        # Decode refresh token
        payload = decode_refresh_token(refresh_token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user from database
        user = db.query(User).filter(
            User.id == payload.get("sub"),
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check organization is active
        if not user.organization or not user.organization.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization is not active"
            )
        
        # Create new tokens
        tokens = create_user_tokens(
            user.id,
            user.email,
            user.organization_id,
            user.role
        )
        
        logger.info(f"Tokens refreshed for user: {user.email}")
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: Session = Depends(get_db)
):
    """Request password reset email"""
    try:
        # Find user by email
        user = db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()
        
        # Always return success to prevent email enumeration
        if not user:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return {"message": "If the email exists, a password reset link has been sent."}
        
        # Create reset token
        reset_token = create_password_reset_token(user.id, user.email)
        
        # Send reset email
        await send_password_reset_email(
            user.email,
            reset_token,
            user.full_name
        )
        
        logger.info(f"Password reset email sent to: {user.email}")
        
        return {"message": "If the email exists, a password reset link has been sent."}
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}", exc_info=True)
        # Still return success to prevent information leakage
        return {"message": "If the email exists, a password reset link has been sent."}

@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Reset password using reset token"""
    try:
        # Decode reset token
        payload = decode_password_reset_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Validate new password
        is_valid, message = validate_password(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Get user
        user = db.query(User).filter(
            User.id == payload.get("sub"),
            User.email == payload.get("email")
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        user.password_hash = hash_password(new_password)
        db.commit()
        
        logger.info(f"Password reset successful for user: {user.email}")
        
        return {"message": "Password reset successful. You can now login with your new password."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

@router.put("/profile")
async def update_profile(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    current_password: Optional[str] = None,
    new_password: Optional[str] = None,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    try:
        # Update name if provided
        if first_name:
            current_user.first_name = first_name
        if last_name:
            current_user.last_name = last_name
        
        # Update password if provided
        if current_password and new_password:
            # Verify current password
            if not verify_password(current_password, current_user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Validate new password
            is_valid, message = validate_password(new_password)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
            
            # Update password
            current_user.password_hash = hash_password(new_password)
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Profile updated for user: {current_user.email}")
        
        return UserResponse.model_validate(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )