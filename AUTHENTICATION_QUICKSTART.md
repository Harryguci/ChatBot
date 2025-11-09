# Authentication Quick Start Guide

## 🚀 Quick Setup (5 Minutes)

### 1. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project
3. Enable "Google+ API" or "Google Identity Services API"
4. Go to "Credentials" > "Create Credentials" > "OAuth 2.0 Client ID"
5. Select "Web application" as the application type
6. **IMPORTANT**: Add authorized JavaScript origins:
   - `http://localhost:3000` (Frontend dev server)
   - `http://localhost:8000` (Backend API - if needed)
7. Copy your **Client ID**

### 2. Configure Environment Variables

**Backend** - Edit `.env` in project root:

```env
JWT_SECRET_KEY=your-secret-key-change-this
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
DEFAULT_ADMIN_EMAIL=your-email@gmail.com
```

**Frontend** - Edit `frontend/app/.env`:

```env
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

⚠️ **Use the same Google Client ID in both files!**

### 3. Install Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend/app
npm install
```

### 4. Run Database Migration

```bash
python src/migrations/add_auth_fields.py
```

### 5. Start Application

**Terminal 1 - Backend:**

```bash
python src/main.py
```

**Terminal 2 - Frontend:**

```bash
cd frontend/app
npm run dev
```

### 6. Login

1. Open: `http://localhost:3000`
2. Click "Sign in with Google"
3. Select your Google account
4. Done! ✅

## 🔐 Admin Access

Your first login with the email matching `DEFAULT_ADMIN_EMAIL` will automatically get admin role.

Admin can access: `http://localhost:3000/admin`

## 📚 Full Documentation

See [AUTHENTICATION.md](docs/AUTHENTICATION.md) for complete documentation.

## 🐛 Troubleshooting

**Error 401: invalid_client / "no registered origin"?**

- ⚠️ **MOST COMMON ISSUE**: Go to [Google Cloud Console](https://console.cloud.google.com/)
- Navigate to: APIs & Services > Credentials
- Click on your OAuth 2.0 Client ID
- Under "Authorized JavaScript origins", add:
  - `http://localhost:3000` (make sure this exact URL is listed)
  - Do NOT include trailing slashes
- Click "Save"
- **Wait 5-10 minutes** for changes to propagate
- Restart your frontend dev server

**Login fails with other errors?**

- Check Google Client ID matches in both `.env` files
- Verify the Client ID is correct: `783465623567-9hrummrr1o1c5min7cpl80lf6p5rlg61.apps.googleusercontent.com`
- Make sure `.env` file is in `frontend/app/` directory
- Restart dev server after changing `.env` file
- Check browser console for detailed error messages

**Not admin?**

- Check `DEFAULT_ADMIN_EMAIL` matches your Google email exactly
- Manually update: `UPDATE users SET role = 'admin' WHERE email = 'your@email.com';`

**CORS errors?**

- Update `allow_origins` in `src/main.py` if using different ports
