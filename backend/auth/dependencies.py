"""
Authentication dependencies - re-exports for convenient imports.
"""
from auth.permissions import (
    get_current_user,
    get_current_active_user,
    require_security_officer,
    require_admin,
    get_current_user_optional,
    get_current_user_from_token,
    CurrentUser,
    UserRole,
    TokenData,
    create_access_token,
    decode_token,
    verify_password,
    get_password_hash,
    get_user_by_email,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
)

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "require_security_officer",
    "require_admin",
    "get_current_user_optional",
    "get_current_user_from_token",
    "CurrentUser",
    "UserRole",
    "TokenData",
    "create_access_token",
    "decode_token",
    "verify_password",
    "get_password_hash",
    "get_user_by_email",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_MINUTES",
]
