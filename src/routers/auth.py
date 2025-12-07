"""
Authentication router for Google OAuth 2.0 and user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

from ..config.db import get_database_connection
from ..config.db.models import User
from ..auth.models import (
    GoogleTokenRequest,
    GoogleAuthResponse,
    UserResponse,
    RoleUpdate,
    Token
)
from ..auth.jwt_utils import create_access_token
from ..auth.google_oauth import verify_google_token
from ..auth.dependencies import (
    get_current_active_user,
    require_admin
)
from ..config.logging_config import get_auth_logger

load_dotenv()

# Get loggers
logger = logging.getLogger(__name__)
auth_logger = get_auth_logger()

# Get default admin email from environment
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "")

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/google", response_model=GoogleAuthResponse)
async def google_auth(request: GoogleTokenRequest):
    """
    Authenticate with Google OAuth token.
    
    - Verifies Google token
    - Creates or updates user in database
    - Returns JWT access token and user info
    """
    try:
        auth_logger.info(f"Google authentication attempt - token length: {len(request.token)}")
        
        # Verify Google token and get user info
        google_user_info = verify_google_token(request.token)
        auth_logger.info(f"Google token verified for user: {google_user_info.get('email')}")
        
        if not google_user_info:
            auth_logger.warning("Invalid Google token received")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
        
        # Get database connection and session
        db_connection = get_database_connection()
        
        with db_connection.get_session() as db:
            # Check if user exists by google_id
            user = db.query(User).filter(User.google_id == google_user_info['google_id']).first()
            
            if user:
                # Update existing user
                auth_logger.info(f"Updating existing user: {user.email}")
                user.full_name = google_user_info['name']
                user.picture_url = google_user_info['picture']
                user.is_verified = google_user_info['email_verified']
                user.last_login = datetime.utcnow()
            else:
                # Check if user exists by email (for migration)
                user = db.query(User).filter(User.email == google_user_info['email']).first()
                
                if user:
                    # Link Google account to existing user
                    auth_logger.info(f"Linking Google account to existing user: {user.email}")
                    user.google_id = google_user_info['google_id']
                    user.picture_url = google_user_info['picture']
                    user.is_verified = google_user_info['email_verified']
                    user.last_login = datetime.utcnow()
                else:
                    # Create new user
                    username = google_user_info['email'].split('@')[0]
                    
                    # Ensure username is unique
                    base_username = username
                    counter = 1
                    while db.query(User).filter(User.username == username).first():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    # Assign role (admin if matches DEFAULT_ADMIN_EMAIL)
                    role = 'admin' if google_user_info['email'] == DEFAULT_ADMIN_EMAIL else 'user'
                    
                    auth_logger.info(f"Creating new user: {google_user_info['email']} with role: {role}")
                    
                    user = User(
                        username=username,
                        email=google_user_info['email'],
                        full_name=google_user_info['name'],
                        google_id=google_user_info['google_id'],
                        picture_url=google_user_info['picture'],
                        role=role,
                        is_active=True,
                        is_verified=google_user_info['email_verified'],
                        last_login=datetime.utcnow()
                    )
                    db.add(user)
            
            # Make sure we have the latest user data
            db.flush()
            db.refresh(user)
            
            # Create JWT access token
            access_token = create_access_token(
                data={"sub": user.email, "username": user.username}
            )
            
            auth_logger.info(f"Authentication successful for user: {user.email}, role: {user.role}")
            
            # Return token and user info
            return GoogleAuthResponse(
                access_token=access_token,
                token_type="bearer",
                user=UserResponse.from_orm(user)
            )
        
    except ValueError as e:
        auth_logger.error(f"ValueError during authentication: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        auth_logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
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
    
    Requires valid JWT token in Authorization header.
    """
    return UserResponse.from_orm(current_user)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout current user.
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token from storage.
    """
    return {"message": "Logged out successfully"}


@router.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    admin_user: User = Depends(require_admin)
):
    """
    List all users (admin only).
    """
    db_connection = get_database_connection()
    with db_connection.get_session() as db:
        users = db.query(User).all()
        return [UserResponse.from_orm(user) for user in users]


@router.put("/admin/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_update: RoleUpdate,
    admin_user: User = Depends(require_admin)
):
    """
    Update user role (admin only).
    
    Valid roles: 'user', 'admin'
    """
    if role_update.role not in ['user', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'user' or 'admin'"
        )
    
    db_connection = get_database_connection()
    with db_connection.get_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.role = role_update.role
        user.updated_at = datetime.utcnow()
        db.flush()
        db.refresh(user)
        
        return UserResponse.from_orm(user)


@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin_user: User = Depends(require_admin)
):
    """
    Delete a user (admin only).
    
    Cannot delete yourself.
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    db_connection = get_database_connection()
    with db_connection.get_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        username = user.username
        db.delete(user)
        # Commit happens automatically when exiting context
        
        return {"message": f"User {username} deleted successfully"}

