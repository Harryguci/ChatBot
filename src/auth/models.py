"""
Pydantic models for authentication.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    """JWT Token response model."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    username: Optional[str] = None
    email: Optional[str] = None


class GoogleTokenRequest(BaseModel):
    """Request model for Google OAuth token."""
    token: str


class UserResponse(BaseModel):
    """User response model (without sensitive data)."""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    picture_url: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class GoogleAuthResponse(BaseModel):
    """Response model for Google OAuth authentication."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RoleUpdate(BaseModel):
    """Request model for updating user role."""
    role: str

