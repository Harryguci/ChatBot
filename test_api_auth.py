"""
Test script to verify API authentication
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.auth.jwt_utils import decode_access_token, create_access_token, SECRET_KEY
from datetime import timedelta

def test_token_creation_and_validation():
    """Test creating and validating a token"""
    print("=" * 60)
    print("Testing JWT Token Creation and Validation")
    print("=" * 60)
    
    # Test data (sub must be a string per JWT spec)
    test_data = {
        "sub": "1",
        "email": "test@example.com",
        "role": "admin"
    }
    
    # Create a token
    print("\n1. Creating token...")
    token = create_access_token(test_data)
    print(f"   Token created: {token[:50]}...")
    
    # Validate the token
    print("\n2. Validating token...")
    payload = decode_access_token(token)
    
    if payload:
        print(f"   ✓ Token is valid")
        print(f"   User ID: {payload.get('sub')}")
        print(f"   Email: {payload.get('email')}")
        print(f"   Role: {payload.get('role')}")
    else:
        print(f"   ✗ Token validation failed")
    
    # Test with the actual token from the user
    print("\n3. Testing user's token...")
    user_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEsImVtYWlsIjoiaHV5cXVhbmcwMDI4QGdtYWlsLmNvbSIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2MzI3ODQ5MiwiaWF0IjoxNzYyNjczNjkyfQ.YtgRx3yjdmLXZ-fJHTHoMfrSApEhzTEEy8ZAJ9Fw4LE"
    user_payload = decode_access_token(user_token)
    
    if user_payload:
        print(f"   ✓ User's token is valid")
        print(f"   User ID: {user_payload.get('sub')}")
        print(f"   Email: {user_payload.get('email')}")
    else:
        print(f"   ✗ User's token validation failed")
        print(f"   This means the token was created with a different JWT_SECRET_KEY")
        print(f"   Solution: User needs to login again to get a new token")
    
    print("\n" + "=" * 60)
    print(f"Current JWT_SECRET_KEY: {SECRET_KEY[:20]}... (first 20 chars)")
    print("=" * 60)

if __name__ == "__main__":
    test_token_creation_and_validation()

