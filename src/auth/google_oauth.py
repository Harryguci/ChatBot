"""
Google OAuth 2.0 verification and user info retrieval.
"""

from google.oauth2 import id_token
from google.auth.transport import requests
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


def verify_google_token(token: str) -> Optional[Dict]:
    """
    Verify Google OAuth token and extract user information.
    
    Args:
        token: Google OAuth token from frontend
        
    Returns:
        Dictionary with user info or None if invalid
        
    Raises:
        ValueError: If token is invalid
    """
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Token is valid, return user info
        return {
            'google_id': idinfo['sub'],
            'email': idinfo['email'],
            'email_verified': idinfo.get('email_verified', False),
            'name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'given_name': idinfo.get('given_name', ''),
            'family_name': idinfo.get('family_name', ''),
        }
    except ValueError as e:
        # Invalid token
        raise ValueError(f"Invalid Google token: {str(e)}")


def get_google_user_info(google_id: str, email: str, name: str) -> Dict:
    """
    Format Google user info for database storage.
    
    Args:
        google_id: Google unique user ID
        email: User email
        name: User full name
        
    Returns:
        Formatted user info dictionary
    """
    # Create username from email (before @ symbol)
    username = email.split('@')[0]
    
    return {
        'google_id': google_id,
        'email': email,
        'username': username,
        'full_name': name,
    }

