# Authentication Quick Start Guide

## 🚀 Quick Setup (5 Minutes)

### 1. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project
3. Enable "Google+ API"
4. Go to "Credentials" > "Create Credentials" > "OAuth 2.0 Client ID"
5. Add authorized origins:
   - `http://localhost:5173`
   - `http://localhost:8000`
6. Copy your **Client ID**

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

1. Open: `http://localhost:5173`
2. Click "Sign in with Google"
3. Select your Google account
4. Done! ✅

## 🔐 Admin Access

Your first login with the email matching `DEFAULT_ADMIN_EMAIL` will automatically get admin role.

Admin can access: `http://localhost:5173/admin`

## 📚 Full Documentation

See [AUTHENTICATION.md](docs/AUTHENTICATION.md) for complete documentation.

## 🐛 Troubleshooting

**Login fails?**
- Check Google Client ID matches in both `.env` files
- Verify authorized origins in Google Cloud Console

**Not admin?**
- Check `DEFAULT_ADMIN_EMAIL` matches your Google email exactly
- Manually update: `UPDATE users SET role = 'admin' WHERE email = 'your@email.com';`

**CORS errors?**
- Update `allow_origins` in `src/main.py` if using different ports
