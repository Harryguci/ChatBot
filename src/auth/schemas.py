"""
Pydantic schemas for authentication requests and responses.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class GoogleAuthRequest(BaseModel):
    """Request model for Google OAuth authentication."""
    token: str  # Google OAuth token from frontend


class UserResponse(BaseModel):
    """Response model for user information."""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    picture_url: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response model for authentication token."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
