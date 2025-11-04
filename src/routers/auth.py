"""
Authentication router for Google OAuth and user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from datetime import datetime
import os
import logging

from src.auth.schemas import GoogleAuthRequest, TokenResponse, UserResponse, MessageResponse
from src.auth.jwt_utils import create_access_token
from src.auth.dependencies import get_db, get_current_active_user, require_admin
from src.config.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")


@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate user with Google OAuth token.

    Flow:
    1. Verify Google OAuth token
    2. Extract user information
    3. Create or update user in database
    4. Generate JWT access token
    5. Return token and user info

    Args:
        body: Google OAuth request containing token
        db: Database session

    Returns:
        TokenResponse with JWT token and user information

    Raises:
        HTTPException: If token verification fails or other errors occur
    """
    try:
        # Verify Google token
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID in environment."
            )

        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            body.token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        # Extract user information from Google token
        google_id = idinfo.get("sub")
        email = idinfo.get("email")
        full_name = idinfo.get("name")
        picture_url = idinfo.get("picture")
        email_verified = idinfo.get("email_verified", False)

        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google token: missing required fields"
            )

        # Check if user already exists
        user = db.query(User).filter(User.google_id == google_id).first()

        if user:
            # Update existing user
            user.full_name = full_name
            user.picture_url = picture_url
            user.last_login = datetime.utcnow()
            user.is_verified = email_verified
        else:
            # Check if email already exists (different OAuth provider or manual registration)
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                # Link Google account to existing user
                existing_user.google_id = google_id
                existing_user.picture_url = picture_url
                existing_user.last_login = datetime.utcnow()
                existing_user.is_verified = email_verified
                user = existing_user
            else:
                # Create new user
                username = email.split("@")[0]
                # Ensure unique username
                base_username = username
                counter = 1
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}{counter}"
                    counter += 1

                # Check if this is the default admin
                role = "admin" if email == DEFAULT_ADMIN_EMAIL else "user"

                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    google_id=google_id,
                    picture_url=picture_url,
                    role=role,
                    is_active=True,
                    is_verified=email_verified,
                    last_login=datetime.utcnow()
                )
                db.add(user)

        db.commit()
        db.refresh(user)

        # Create JWT access token
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        )

        logger.info(f"User {user.email} authenticated successfully (role: {user.role})")

        # Return token and user info
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.from_orm(user)
        )

    except ValueError as e:
        # Token verification failed
        logger.error(f"Google token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        UserResponse with user information
    """
    return UserResponse.from_orm(current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout endpoint (client should discard token).

    Note: JWT tokens are stateless, so actual logout happens on client side
    by removing the token. This endpoint is mainly for logging purposes.

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    logger.info(f"User {current_user.email} logged out")
    return MessageResponse(message="Logged out successfully")


@router.get("/admin/users", response_model=list[UserResponse])
async def list_users(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only).

    Args:
        admin_user: Current authenticated admin user
        db: Database session

    Returns:
        List of all users
    """
    users = db.query(User).all()
    return [UserResponse.from_orm(user) for user in users]


@router.put("/admin/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user role (admin only).

    Args:
        user_id: ID of user to update
        role: New role ('admin' or 'user')
        admin_user: Current authenticated admin user
        db: Database session

    Returns:
        Updated user information

    Raises:
        HTTPException: If user not found or invalid role
    """
    if role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'admin' or 'user'."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.role = role
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    logger.info(f"Admin {admin_user.email} changed role of user {user.email} to {role}")

    return UserResponse.from_orm(user)
