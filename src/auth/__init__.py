"""
Authentication module for Google OAuth 2.0 and JWT token management.
"""

from .models import Token, TokenData, GoogleTokenRequest, UserResponse, RoleUpdate
from .jwt_utils import create_access_token, verify_token, get_token_expiration
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_admin,
    optional_current_user
)
from .google_oauth import verify_google_token, get_google_user_info

__all__ = [
    'Token',
    'TokenData',
    'GoogleTokenRequest',
    'UserResponse',
    'RoleUpdate',
    'create_access_token',
    'verify_token',
    'get_token_expiration',
    'get_current_user',
    'get_current_active_user',
    'require_admin',
    'optional_current_user',
    'verify_google_token',
    'get_google_user_info',
]

