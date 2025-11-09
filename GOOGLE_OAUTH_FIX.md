# Fix: Google OAuth "Error 401: invalid_client" / "no registered origin"

## Problem

You're seeing this error when trying to login:

```
Access blocked: Authorization Error
Error 401: invalid_client
no registered origin
```

## Solution

### Step 1: Update Google Cloud Console Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to: **APIs & Services** > **Credentials**
4. Find and click on your OAuth 2.0 Client ID (the one ending with `.apps.googleusercontent.com`)
5. Scroll down to **"Authorized JavaScript origins"**
6. Click **"+ ADD URI"** and add:
   ```
   http://localhost:3000
   ```
   ⚠️ **Important**:
   - Use exactly `http://localhost:3000` (no trailing slash)
   - Make sure the protocol is `http://` (not `https://`)
   - Make sure the port is `3000` (not 5173 or 8000)
7. Scroll down to **"Authorized redirect URIs"** (optional, but recommended)
   - Add: `http://localhost:3000`
8. Click **"SAVE"** at the bottom

### Step 2: Wait for Changes to Propagate

- Google Cloud Console changes can take **5-10 minutes** to take effect
- Be patient and wait before testing again

### Step 3: Verify Your Frontend Configuration

1. Make sure `.env` file exists in `frontend/app/` directory
2. Verify it contains:
   ```env
   VITE_GOOGLE_CLIENT_ID=783465623567-9hrummrr1o1c5min7cpl80lf6p5rlg61.apps.googleusercontent.com
   ```
3. Make sure there are no spaces around the `=` sign
4. Make sure there are no quotes around the value

### Step 4: Restart Your Development Server

1. Stop your frontend dev server (Ctrl+C)
2. Restart it:
   ```bash
   cd frontend/app
   npm run dev
   ```
3. Open `http://localhost:3000` in your browser
4. Try logging in again

### Step 5: Clear Browser Cache (if still not working)

1. Open browser DevTools (F12)
2. Go to Application/Storage tab
3. Clear site data/cookies for `localhost:3000`
4. Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)

## Verification Checklist

- ✅ `http://localhost:3000` is listed in "Authorized JavaScript origins"
- ✅ `.env` file exists in `frontend/app/` directory
- ✅ `VITE_GOOGLE_CLIENT_ID` is set correctly in `.env`
- ✅ Dev server is running on port 3000
- ✅ Waited 5-10 minutes after saving Google Cloud Console changes
- ✅ Restarted dev server after any `.env` changes
- ✅ Browser cache cleared

## Still Having Issues?

1. Check browser console (F12) for detailed error messages
2. Verify your Client ID matches exactly in both:
   - Google Cloud Console
   - `frontend/app/.env` file
3. Make sure you're using the correct OAuth 2.0 Client ID (Web application type, not Desktop app)
4. Check that "Google Identity Services API" or "Google+ API" is enabled in your Google Cloud project

## Common Mistakes

- ❌ Using `https://localhost:3000` instead of `http://localhost:3000`
- ❌ Adding trailing slash: `http://localhost:3000/` (should be without slash)
- ❌ Using wrong port (e.g., 5173 instead of 3000)
- ❌ Not waiting for Google Cloud changes to propagate
- ❌ Not restarting dev server after `.env` changes
- ❌ Having spaces in `.env` file: `VITE_GOOGLE_CLIENT_ID = ...` (should be `VITE_GOOGLE_CLIENT_ID=...`)
