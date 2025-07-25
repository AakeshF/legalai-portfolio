# organization_routes.py - Organization management endpoints
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import secrets
import string

from database import get_db
from models import User, Organization
from auth_middleware import get_current_user, get_current_organization
from auth_utils import hash_password as get_password_hash
from organization_middleware import OrganizationSecurityLogger
from schemas import (
    OrganizationResponse,
    OrganizationUpdate,
    UserInvite,
    UserResponse,
    OrganizationUsersResponse,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organization", tags=["organization"])


def generate_temp_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(chars) for _ in range(length))


@router.get("", response_model=OrganizationResponse)
async def get_organization_details(
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
):
    """Get current organization details"""
    logger.info(
        f"Organization details requested",
        extra={"organization_id": current_org.id, "user_id": current_user.id},
    )

    return OrganizationResponse(
        id=current_org.id,
        name=current_org.name,
        subscription_tier=current_org.subscription_tier,
        billing_email=current_org.billing_email,
        created_at=current_org.created_at,
        is_active=current_org.is_active,
        user_count=len(current_org.users),
        document_count=len(current_org.documents),
        storage_used_mb=sum(doc.file_size for doc in current_org.documents)
        / (1024 * 1024),
    )


@router.put("", response_model=OrganizationResponse)
async def update_organization(
    org_update: OrganizationUpdate,
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update organization settings - admin only"""
    # Check if user is admin
    if current_user.role != "admin":
        OrganizationSecurityLogger.log_access_attempt(
            user_id=current_user.id,
            organization_id=current_org.id,
            resource_type="organization",
            resource_id=current_org.id,
            action="update",
            success=False,
            reason="Insufficient permissions - admin required",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update organization settings",
        )

    # Update organization fields
    update_data = org_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_org, field, value)

    db.commit()
    db.refresh(current_org)

    logger.info(
        f"Organization updated",
        extra={
            "organization_id": current_org.id,
            "updated_by": current_user.id,
            "fields_updated": list(update_data.keys()),
        },
    )

    return OrganizationResponse(
        id=current_org.id,
        name=current_org.name,
        subscription_tier=current_org.subscription_tier,
        billing_email=current_org.billing_email,
        created_at=current_org.created_at,
        is_active=current_org.is_active,
        user_count=len(current_org.users),
        document_count=len(current_org.documents),
        storage_used_mb=sum(doc.file_size for doc in current_org.documents)
        / (1024 * 1024),
    )


@router.get("/users", response_model=OrganizationUsersResponse)
async def list_organization_users(
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all users in the organization - admin only"""
    # Check if user is admin
    if current_user.role != "admin":
        OrganizationSecurityLogger.log_access_attempt(
            user_id=current_user.id,
            organization_id=current_org.id,
            resource_type="organization_users",
            resource_id=current_org.id,
            action="list",
            success=False,
            reason="Insufficient permissions - admin required",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view organization users",
        )

    users = (
        db.query(User)
        .filter(User.organization_id == current_org.id, User.is_active == True)
        .all()
    )

    user_responses = [
        UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            organization_id=user.organization_id,
        )
        for user in users
    ]

    return OrganizationUsersResponse(
        users=user_responses,
        total_count=len(users),
        active_count=len([u for u in users if u.is_active]),
        admin_count=len([u for u in users if u.role == "admin"]),
        attorney_count=len([u for u in users if u.role == "attorney"]),
        paralegal_count=len([u for u in users if u.role == "paralegal"]),
    )


@router.post("/invite", response_model=dict)
async def invite_user(
    invite: UserInvite,
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite a new user to the organization - admin only"""
    # Check if user is admin
    if current_user.role != "admin":
        OrganizationSecurityLogger.log_access_attempt(
            user_id=current_user.id,
            organization_id=current_org.id,
            resource_type="user_invite",
            resource_id=invite.email,
            action="create",
            success=False,
            reason="Insufficient permissions - admin required",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can invite new users",
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == invite.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    # Generate temporary password
    temp_password = generate_temp_password()

    # Create new user
    new_user = User(
        id=str(uuid.uuid4()),
        email=invite.email,
        password_hash=get_password_hash(temp_password),
        first_name=invite.first_name,
        last_name=invite.last_name,
        role=invite.role,
        organization_id=current_org.id,
        created_at=datetime.utcnow(),
        is_active=True,
    )

    db.add(new_user)
    db.commit()

    # TODO: Send invitation email functionality needs to be implemented
    # For now, log the temporary password
    logger.info(
        f"New user invited - Email: {invite.email}, Temp Password: {temp_password}"
    )

    logger.info(
        f"User invited to organization",
        extra={
            "organization_id": current_org.id,
            "invited_by": current_user.id,
            "invited_user": new_user.id,
            "role": invite.role,
            "email_sent": False,
        },
    )

    return {
        "message": f"User invited successfully",
        "user_id": new_user.id,
        "email_sent": False,
        "temporary_password": temp_password,  # Always return password since email is not implemented
    }


@router.delete("/users/{user_id}")
async def remove_user(
    user_id: str,
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a user from the organization - admin only"""
    # Check if user is admin
    if current_user.role != "admin":
        OrganizationSecurityLogger.log_access_attempt(
            user_id=current_user.id,
            organization_id=current_org.id,
            resource_type="user",
            resource_id=user_id,
            action="delete",
            success=False,
            reason="Insufficient permissions - admin required",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can remove users",
        )

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself from the organization",
        )

    # Get the user to remove
    user_to_remove = (
        db.query(User)
        .filter(User.id == user_id, User.organization_id == current_org.id)
        .first()
    )

    if not user_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization",
        )

    # Check if this is the last admin
    if user_to_remove.role == "admin":
        admin_count = (
            db.query(User)
            .filter(
                User.organization_id == current_org.id,
                User.role == "admin",
                User.is_active == True,
                User.id != user_id,
            )
            .count()
        )

        if admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last administrator",
            )

    # Soft delete the user
    user_to_remove.is_active = False
    db.commit()

    logger.info(
        f"User removed from organization",
        extra={
            "organization_id": current_org.id,
            "removed_by": current_user.id,
            "removed_user": user_id,
        },
    )

    return {
        "message": f"User {user_to_remove.email} has been removed from the organization"
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: str,
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a user's role - admin only"""
    # Validate role
    valid_roles = ["attorney", "admin", "paralegal"]
    if new_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    # Check if user is admin
    if current_user.role != "admin":
        OrganizationSecurityLogger.log_access_attempt(
            user_id=current_user.id,
            organization_id=current_org.id,
            resource_type="user_role",
            resource_id=user_id,
            action="update",
            success=False,
            reason="Insufficient permissions - admin required",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can change user roles",
        )

    # Get the user to update
    user_to_update = (
        db.query(User)
        .filter(User.id == user_id, User.organization_id == current_org.id)
        .first()
    )

    if not user_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization",
        )

    # Prevent removing the last admin
    if user_to_update.role == "admin" and new_role != "admin":
        admin_count = (
            db.query(User)
            .filter(
                User.organization_id == current_org.id,
                User.role == "admin",
                User.is_active == True,
                User.id != user_id,
            )
            .count()
        )

        if admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove admin role from the last administrator",
            )

    old_role = user_to_update.role
    user_to_update.role = new_role
    db.commit()

    logger.info(
        f"User role updated",
        extra={
            "organization_id": current_org.id,
            "updated_by": current_user.id,
            "updated_user": user_id,
            "old_role": old_role,
            "new_role": new_role,
        },
    )

    return {
        "message": f"User role updated successfully",
        "user_id": user_id,
        "old_role": old_role,
        "new_role": new_role,
    }
