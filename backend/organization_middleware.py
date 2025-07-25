# organization_middleware.py - Organization-scoped query filtering and security
from typing import Optional, Any
from functools import wraps
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_
import logging
from datetime import datetime

from database import get_db
from models import User, Organization, Document, ChatSession
from auth_utils import decode_access_token

logger = logging.getLogger(__name__)


class OrganizationSecurityViolation(Exception):
    """Raised when a cross-organization access attempt is detected"""

    pass


class OrganizationQueryFilter:
    """
    Provides automatic organization-based query filtering for multi-tenant data isolation
    """

    @staticmethod
    def filter_query(query: Query, model: Any, organization_id: str) -> Query:
        """
        Apply organization filter to a SQLAlchemy query

        Args:
            query: Base SQLAlchemy query
            model: The model class being queried
            organization_id: The organization ID to filter by

        Returns:
            Filtered query
        """
        if hasattr(model, "organization_id"):
            return query.filter(model.organization_id == organization_id)
        return query

    @staticmethod
    def verify_ownership(
        item: Any, organization_id: str, item_type: str = "resource"
    ) -> bool:
        """
        Verify that an item belongs to the specified organization

        Args:
            item: The database object to check
            organization_id: The expected organization ID
            item_type: Type of item for logging purposes

        Returns:
            True if item belongs to organization

        Raises:
            OrganizationSecurityViolation: If item doesn't belong to organization
        """
        if not item:
            return False

        if not hasattr(item, "organization_id"):
            logger.warning(f"{item_type} does not have organization_id field")
            return True  # Allow for non-org-scoped models

        if item.organization_id != organization_id:
            logger.error(
                f"Cross-organization access attempt detected! "
                f"Item: {item_type}, Item Org: {item.organization_id}, "
                f"Requested Org: {organization_id}"
            )
            raise OrganizationSecurityViolation(
                f"Access denied: {item_type} belongs to different organization"
            )

        return True


def organization_scope(model_class: Any):
    """
    Decorator that automatically applies organization filtering to endpoint queries

    Usage:
        @app.get("/api/documents")
        @organization_scope(Document)
        async def list_documents(org_query: Query = Depends()):
            documents = org_query.all()
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract organization_id from request state
            request = kwargs.get("request") or kwargs.get("current_org")
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization context not available",
                )

            # Get the query from kwargs if it exists
            if "query" in kwargs and hasattr(kwargs["query"], "filter"):
                org_id = getattr(request, "organization_id", None) or request.id
                kwargs["query"] = OrganizationQueryFilter.filter_query(
                    kwargs["query"], model_class, org_id
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class OrganizationSecurityLogger:
    """
    Logs security-related events for organization data access
    """

    @staticmethod
    def log_access_attempt(
        user_id: str,
        organization_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        success: bool,
        reason: Optional[str] = None,
    ):
        """Log an access attempt with full context"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "organization_id": organization_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "success": success,
            "reason": reason,
        }

        if success:
            logger.info(f"Organization access granted: {log_data}")
        else:
            logger.warning(f"Organization access denied: {log_data}")

    @staticmethod
    def log_cross_org_violation(
        user_id: str,
        user_org_id: str,
        requested_org_id: str,
        resource_type: str,
        resource_id: str,
    ):
        """Log a cross-organization access violation"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "violation_type": "cross_organization_access",
            "user_id": user_id,
            "user_organization_id": user_org_id,
            "requested_organization_id": requested_org_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }

        logger.error(f"SECURITY VIOLATION: {log_data}")


# Helper function for endpoints
def get_org_filtered_query(
    model_class: Any, organization_id: str, db: Session
) -> Query:
    """
    Get a pre-filtered query for a model based on organization

    Args:
        model_class: The SQLAlchemy model class
        organization_id: The organization ID to filter by
        db: Database session

    Returns:
        Filtered SQLAlchemy query
    """
    query = db.query(model_class)
    return OrganizationQueryFilter.filter_query(query, model_class, organization_id)


# Dependency injection helpers
def organization_dependency(model_class: Any, allow_admin_override: bool = False):
    """
    FastAPI dependency that provides organization-filtered queries

    Args:
        model_class: The model to query
        allow_admin_override: Whether to allow admins to access all orgs

    Usage:
        @app.get("/api/documents")
        async def list_documents(
            org_docs: Query = Depends(organization_dependency(Document))
        ):
            return org_docs.all()
    """

    async def get_filtered_query(
        current_org: Organization = Depends(get_current_organization),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Query:
        # Check if admin override is allowed and user is admin
        if allow_admin_override and current_user.role == "admin":
            # Admin can see all organizations' data if needed
            return db.query(model_class)

        # Regular users only see their organization's data
        return get_org_filtered_query(model_class, current_org.id, db)

    return get_filtered_query


# Import get_current_organization from auth_middleware to avoid circular import
from auth_middleware import get_current_organization
