"""
FastAPI dependencies for authentication and authorization.
"""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session

from .jwt_utils import decode_access_token
from src.config.db import get_database_connection
from src.config.db.models import User

logger = logging.getLogger(__name__)

# Security scheme for JWT token
security = HTTPBearer()


def get_db():
    """Get database session as FastAPI dependency."""
    db = get_database_connection()
    with db.get_session() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials containing JWT token
        db: Database session

    Returns:
        User object if authentication is successful

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    
    # Validate token is not empty
    if not token or not token.strip():
        logger.warning("Empty token provided")
        raise credentials_exception
    
    payload = decode_access_token(token)

    if payload is None:
        # Token is invalid, expired, or cannot be decoded
        # This could be due to:
        # 1. Token expired
        # 2. Invalid signature (JWT_SECRET_KEY mismatch)
        # 3. Invalid token format
        # 4. Token was created with different secret key
        logger.warning(f"Token validation failed for token: {token[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    # Convert user_id to int (JWT 'sub' is stored as string)
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.error(f"Invalid user ID format in token: {user_id_str}")
        raise credentials_exception

    # Query user from database
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (must be active to access).

    Args:
        current_user: Current authenticated user

    Returns:
        User object if user is active

    Raises:
        HTTPException: If user account is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require admin role for access.

    Args:
        current_user: Current authenticated user

    Returns:
        User object if user is admin

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin access required."
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for endpoints that work with or without authentication.

    Args:
        credentials: Optional HTTP authorization credentials
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        return None

    # Convert user_id to int (JWT 'sub' is stored as string)
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user
