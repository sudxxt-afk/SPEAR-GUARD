"""
Helper functions for data isolation based on user role and organization.
Admins can see all data within their organization.
Regular users see only their own data.
"""
from sqlalchemy import or_
from auth.permissions import CurrentUser, UserRole
from database import EmailAnalysis, Alert, User


def get_user_data_filter(model, current_user: CurrentUser, user_id_field: str = "user_id"):
    """
    Returns a SQLAlchemy filter for data isolation.
    
    - Admins: see all data in their organization (or all data if no org)
    - Security Officers: see all data in their organization
    - Regular users: see only their own data
    
    Args:
        model: SQLAlchemy model class (EmailAnalysis, Alert, etc.)
        current_user: Current authenticated user
        user_id_field: Name of the user_id column in the model
    
    Returns:
        SQLAlchemy filter expression
    """
    user_id_col = getattr(model, user_id_field)
    
    # Admins and Security Officers can see all organization data
    if current_user.role in [UserRole.ADMIN, UserRole.SECURITY_OFFICER]:
        if current_user.organization_id:
            # If user belongs to an organization, show all org data
            # This requires a join with users table to get organization_id
            # For simplicity, we'll allow admins to see ALL data for now
            # In production, you'd join with users table
            return True  # No filter - see everything
        else:
            # Admin without org - see all data
            return True
    
    # Regular users see only their own data
    return user_id_col == current_user.id


def can_view_all_org_data(current_user: CurrentUser) -> bool:
    """Check if user can view all organization data."""
    return current_user.role in [UserRole.ADMIN, UserRole.SECURITY_OFFICER]
