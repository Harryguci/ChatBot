# Authentication System Documentation

## Overview

This chatbot application implements Google OAuth 2.0 authentication with role-based access control (RBAC). Users authenticate via Google SSO, and can be assigned either "user" or "admin" roles. A default admin account can be configured via environment variables.

## Features

- **Google OAuth 2.0 SSO**: Secure authentication using Google accounts
- **JWT Tokens**: Stateless session management with JSON Web Tokens
- **Role-Based Access Control**: Support for "admin" and "user" roles
- **Default Admin Account**: Environment-configurable admin user
- **Protected API Endpoints**: All chatbot endpoints require authentication
- **Secure Token Storage**: Frontend stores tokens in localStorage with automatic header injection

## Architecture

### Backend (FastAPI)

```
┌─────────────────────────────────────────────────────┐
│                  Authentication Flow                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. User logs in with Google → Frontend receives    │
│     Google OAuth token                              │
│                                                      │
│  2. Frontend sends token to:                        │
│     POST /api/auth/google                           │
│                                                      │
│  3. Backend verifies token with Google API          │
│                                                      │
│  4. Backend creates/updates user in database        │
│     - Check if google_id exists                     │
│     - Assign role (admin if DEFAULT_ADMIN_EMAIL)    │
│                                                      │
│  5. Backend generates JWT access token              │
│                                                      │
│  6. Return: {access_token, user}                    │
│                                                      │
│  7. Frontend stores token and uses in headers:      │
│     Authorization: Bearer <token>                   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Frontend (React)

```
┌─────────────────────────────────────────────────────┐
│                  React App Structure                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  GoogleOAuthProvider (main.tsx)                     │
│    └─> AuthProvider (AuthContext)                   │
│         └─> Router                                   │
│              ├─> /login (public)                    │
│              ├─> / (protected)                      │
│              ├─> /chat (protected)                  │
│              └─> /admin/* (protected + admin only)  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Setup Guide

### 1. Google OAuth Configuration

#### Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth 2.0 Client ID"
5. Configure OAuth consent screen if prompted
6. Application type: "Web application"
7. Add authorized JavaScript origins:
   - `http://localhost:5173` (Vite dev server)
   - `http://localhost:8000` (FastAPI server)
   - Your production domain
8. Add authorized redirect URIs:
   - `http://localhost:5173`
   - `http://localhost:8000`
   - Your production domain
9. Copy the **Client ID** (format: `xxxxx.apps.googleusercontent.com`)

#### Step 2: Configure Backend Environment

Edit `.env` in the project root:

```env
# Authentication Configuration
JWT_SECRET_KEY=<generate-a-secure-random-string>
GOOGLE_CLIENT_ID=<your-google-client-id>.apps.googleusercontent.com
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
```

**Generate secure JWT secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 3: Configure Frontend Environment

Edit `frontend/app/.env`:

```env
# Google OAuth Configuration
VITE_GOOGLE_CLIENT_ID=<your-google-client-id>.apps.googleusercontent.com
```

**Important**: Use the same Client ID in both backend and frontend.

### 2. Install Dependencies

#### Backend
```bash
pip install -r requirements.txt
```

New authentication dependencies:
- `authlib>=1.3.0` - OAuth client library
- `python-jose[cryptography]>=3.3.0` - JWT token handling
- `passlib[bcrypt]>=1.7.4` - Password hashing (future use)
- `python-multipart>=0.0.9` - Form data parsing

#### Frontend
```bash
cd frontend/app
npm install
```

New authentication dependencies:
- `@react-oauth/google` - Google OAuth React components
- `axios` - HTTP client with interceptors

### 3. Run Database Migration

Apply the authentication fields migration to add new columns to the `users` table:

```bash
python src/migrations/add_auth_fields.py
```

This adds:
- `google_id` - Google OAuth unique identifier
- `picture_url` - User profile picture
- `role` - User role ('admin' or 'user')
- `is_verified` - Email verification status
- `last_login` - Last login timestamp

To rollback (if needed):
```bash
python src/migrations/add_auth_fields.py --rollback
```

### 4. Start the Application

#### Backend (Terminal 1)
```bash
python src/main.py
```
or
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (Terminal 2)
```bash
cd frontend/app
npm run dev
```

### 5. First Login & Admin Setup

1. Open browser: `http://localhost:5173`
2. You'll be redirected to `/login`
3. Click "Sign in with Google"
4. Select your Google account
5. Grant permissions

**For Admin Access:**
- Ensure `DEFAULT_ADMIN_EMAIL` in `.env` matches your Google account email
- The first user to login with that email will automatically receive admin role
- Admin users can access `/admin/*` routes

## API Endpoints

### Authentication Endpoints

#### `POST /api/auth/google`
Authenticate with Google OAuth token.

**Request:**
```json
{
  "token": "google-oauth-token-from-frontend"
}
```

**Response:**
```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "full_name": "John Doe",
    "picture_url": "https://...",
    "role": "user",
    "is_active": true,
    "is_verified": true,
    "created_at": "2025-11-04T10:00:00",
    "last_login": "2025-11-04T10:00:00"
  }
}
```

#### `GET /api/auth/me`
Get current authenticated user.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  ...
}
```

#### `POST /api/auth/logout`
Logout (client-side token removal).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

### Admin Endpoints

#### `GET /api/auth/admin/users`
List all users (admin only).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response:**
```json
[
  {
    "id": 1,
    "username": "john",
    "email": "john@example.com",
    "role": "admin",
    ...
  },
  ...
]
```

#### `PUT /api/auth/admin/users/{user_id}/role`
Update user role (admin only).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request:**
```json
{
  "role": "admin"
}
```

**Response:**
```json
{
  "id": 2,
  "username": "jane",
  "role": "admin",
  ...
}
```

### Protected Chatbot Endpoints

All chatbot endpoints now require authentication:

- `POST /api/chatbot/upload-document` - Upload and process documents
- `POST /api/chatbot/chat` - Chat with documents
- `GET /api/chatbot/memory/status` - Get memory status
- `GET /api/chatbot/memorable-documents` - List documents
- `DELETE /api/chatbot/memorable-documents/{filename}` - Delete document (admin only)

## Frontend Integration

### Using Authentication in Components

```tsx
import { useAuth } from "../contexts/AuthContext";

function MyComponent() {
  const { user, isAuthenticated, isAdmin, logout } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return (
    <div>
      <p>Welcome, {user?.full_name || user?.username}!</p>
      {isAdmin() && <AdminPanel />}
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

### Making Authenticated API Calls

```tsx
import axios from "axios";

// Token is automatically added to headers by AuthContext
const response = await axios.post("/api/chatbot/chat", {
  query: "What is this about?",
  chat_history: [],
});
```

### Protected Routes

```tsx
import { ProtectedRoute } from "./components/ProtectedRoute";

<Route
  path="/admin/dashboard"
  element={
    <ProtectedRoute requireAdmin={true}>
      <DashboardPage />
    </ProtectedRoute>
  }
/>
```

## Security Considerations

### JWT Tokens
- **Expiration**: Tokens expire after 7 days (configurable in `jwt_utils.py`)
- **Secret Key**: Use a strong, randomly generated secret (32+ characters)
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Storage**: Frontend stores in localStorage (consider httpOnly cookies for production)

### Google OAuth
- **Token Verification**: Backend verifies every Google token with Google's API
- **No Password Storage**: Users authenticate via Google, no passwords stored
- **Email Verification**: Uses Google's email_verified field

### Role-Based Access Control
- **Middleware**: `get_current_user`, `get_current_active_user`, `require_admin`
- **Automatic Checks**: FastAPI dependency injection enforces access control
- **Admin Routes**: Protected by `require_admin` dependency

### Best Practices
1. **HTTPS in Production**: Always use HTTPS for token transmission
2. **Environment Variables**: Never commit `.env` files to version control
3. **Token Rotation**: Consider implementing refresh tokens for production
4. **Rate Limiting**: Already implemented with `slowapi` (10/min for uploads, 30/min for chat)
5. **CORS Configuration**: Update `allow_origins` in production to specific domains

## Troubleshooting

### Issue: "Invalid Google token"
**Cause**: Token expired or incorrect Client ID
**Solution**:
- Verify `GOOGLE_CLIENT_ID` matches in both backend and frontend
- Ensure Client ID is correctly configured in Google Cloud Console
- Token expires after 1 hour - user needs to re-authenticate

### Issue: "Could not validate credentials"
**Cause**: Invalid or expired JWT token
**Solution**:
- Check if `JWT_SECRET_KEY` is set in backend `.env`
- Clear localStorage and login again
- Verify token hasn't expired (default: 7 days)

### Issue: Admin role not assigned
**Cause**: Email mismatch with `DEFAULT_ADMIN_EMAIL`
**Solution**:
- Verify `DEFAULT_ADMIN_EMAIL` in `.env` exactly matches Google account email
- Check database: `SELECT * FROM users WHERE email = 'admin@example.com';`
- Manually update: `UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';`

### Issue: "Insufficient permissions" for admin endpoints
**Cause**: User doesn't have admin role
**Solution**:
- Check user role: `GET /api/auth/me`
- Update role via database or admin endpoint (if another admin exists)

### Issue: CORS errors on login
**Cause**: Origin not whitelisted
**Solution**:
- Update `allow_origins` in `src/main.py` to include your frontend domain
- For development: `["http://localhost:5173", "http://localhost:8000"]`

## Testing

### Manual Testing Checklist

- [ ] Can access `/login` without authentication
- [ ] Google login button appears
- [ ] Clicking Google button opens OAuth popup
- [ ] After login, redirected to `/` (chat page)
- [ ] Token stored in localStorage
- [ ] Can access `/chat` with valid token
- [ ] Can upload documents with valid token
- [ ] Cannot access `/admin` without admin role
- [ ] Admin user can access `/admin/dashboard`
- [ ] Logout clears token and redirects to `/login`
- [ ] Expired token returns 401 and redirects to `/login`

### Automated Testing (Future)

Create test cases for:
- Google OAuth token verification
- JWT token generation/validation
- Role-based access control
- Protected endpoint authorization
- Token expiration handling

## Database Schema

### Updated `users` Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),

    -- Google OAuth fields
    google_id VARCHAR(255) UNIQUE,
    picture_url VARCHAR(500),

    -- Role-based access control
    role VARCHAR(50) DEFAULT 'user' NOT NULL,

    -- Account status
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login TIMESTAMP,

    -- Indexes
    INDEX (username),
    INDEX (email),
    INDEX (google_id),
    INDEX (role)
);
```

## Migration Path for Existing Users

If you have existing users in the database before authentication:

1. **Run Migration**: `python src/migrations/add_auth_fields.py`
2. **Link Google Accounts**: When existing user logs in with Google, system will link `google_id` to existing user by email
3. **Assign Roles**: Update existing users' roles:
   ```sql
   UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
   UPDATE users SET role = 'user' WHERE role IS NULL OR role = '';
   ```

## Production Deployment

### Environment Variables (Production)

```env
# Backend (.env)
JWT_SECRET_KEY=<production-secret-key-64-chars>
GOOGLE_CLIENT_ID=<production-client-id>.apps.googleusercontent.com
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
```

```env
# Frontend (.env.production)
VITE_GOOGLE_CLIENT_ID=<production-client-id>.apps.googleusercontent.com
VITE_API_BASE_URL=https://api.yourdomain.com/api
```

### CORS Configuration

Update `src/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://www.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Token Storage Options

**Development**: localStorage (current implementation)
**Production**: Consider httpOnly cookies for enhanced security

### HTTPS

Ensure all communication uses HTTPS in production:
- Backend: Use reverse proxy (nginx, caddy) with SSL certificates
- Frontend: Deploy to platform with automatic SSL (Vercel, Netlify)

---

**Last Updated**: 2025-11-04
**Version**: 1.0.0
**Authors**: AI Development Team
