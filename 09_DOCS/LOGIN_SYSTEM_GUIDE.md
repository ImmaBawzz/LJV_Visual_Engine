# LJV Visual Engine - Login System & Vercel Deployment Guide

## Overview

The LJV Visual Engine now includes a **production-ready authentication system** with:
- Email/password login and signup
- Password strength meter
- Remember me functionality
- Password reset flow
- Google OAuth scaffolding
- Rate limiting and audit logging
- Full Vercel deployment support

## Quick Start

### Local Development

```bash
# 1. Set up environment
export LJV_DEBUG=true
export LJV_SECRET_KEY=dev-secret-key
export LJV_DEVELOPER_EMAIL=admin@ljv.local

# 2. Start dashboard
cd 05_SCRIPTS/dashboard
python app.py

# 3. Open in browser
# http://127.0.0.1:8787/login.html
```

### First Login

1. Click **"Sign Up"** tab
2. Enter your admin email: `admin@ljv.local`
3. Create a password (8+ characters)
4. Click **"Create Account"**
5. You're now logged in!

## File Structure

```
05_SCRIPTS/dashboard/
├── static/
│   ├── login.html           # Professional login page
│   ├── auth-api.js          # API handler library
│   ├── index.html           # Main dashboard
│   └── app.js               # Dashboard logic
├── app.py                   # Backend server
└── ...

09_DOCS/
├── AUTH_DEPLOYMENT.md       # Auth system docs
├── VERCEL_DEPLOYMENT.md     # Vercel setup guide
└── ...

Root files:
├── .env.example             # Environment template
├── vercel.json              # Vercel configuration
└── ...
```

## Login Page Features

### Authentication
- **Email/Password** - Secure bcrypt hashing
- **Sign Up** - Create admin accounts
- **Remember Me** - Store email locally
- **Password Reset** - Email-based recovery

### Security
- **Password Strength Meter** - Shows password quality (weak/fair/strong)
- **Rate Limiting** - 5 attempts per 5 minutes
- **Session Security** - HttpOnly cookies, SameSite=Lax
- **CORS Protection** - Origin-scoped requests

### User Experience
- **Responsive Design** - Works on desktop, tablet, mobile
- **Loading States** - Visual feedback during operations
- **Error Messages** - Clear, actionable error communication
- **Tab Navigation** - Easy switching between Login/SignUp

## Architecture

### Frontend (login.html)
```
┌─────────────────────────────────┐
│   login.html                    │
│  ┌─────────────────────────────┐│
│  │ Login Form / Signup Form    ││
│  │ Password Strength Meter      ││
│  │ Forgot Password Modal        ││
│  └─────────────────────────────┘│
│  ┌─────────────────────────────┐│
│  │ auth-api.js                 ││
│  │ API Handler & Auth Manager  ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
```

### Backend (app.py)
```
┌─────────────────────────────────┐
│   FastAPI Server                │
│  ┌─────────────────────────────┐│
│  │ /auth/* endpoints            ││
│  │ - /login (POST)              ││
│  │ - /signup (POST)             ││
│  │ - /logout (POST)             ││
│  │ - /status (GET)              ││
│  └─────────────────────────────┘│
│  ┌─────────────────────────────┐│
│  │ / API Control Endpoints      ││
│  │ - /api/control/* (protected) ││
│  │ - /api/state (GET)           ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
```

## Deploying to Vercel

### Step 1: Prepare Repository

```bash
# Ensure all files are committed
git add -A
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### Step 2: Copy Environment Template

```bash
# Copy template and fill in values
cp .env.example .env
# Edit .env with your values
```

### Step 3: Deploy Using CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

### Step 4: Set Environment Variables

```bash
# Via CLI
vercel env add LJV_SECRET_KEY
vercel env add LJV_DEVELOPER_EMAIL
vercel env add LJV_ALLOWED_ORIGINS

# Or via Dashboard:
# 1. Go to Vercel Dashboard
# 2. Select your project
# 3. Settings → Environment Variables
# 4. Add each variable
```

**Critical Variables:**
- `LJV_SECRET_KEY` - Random 32+ character string
- `LJV_DEVELOPER_EMAIL` - Your admin email
- `LJV_ALLOWED_ORIGINS` - Your Vercel domain
- `LJV_SESSION_COOKIE_SECURE` - `true` for HTTPS
- `LJV_AUTH_DB_PATH` - `/tmp/ljv_auth.db` (ephemeral)

### Step 5: Test Your Deployment

1. Open your Vercel domain: `https://your-app.vercel.app/login.html`
2. Click "Sign Up"
3. Enter your admin email
4. Create a password
5. Test login

See [09_DOCS/VERCEL_DEPLOYMENT.md](../09_DOCS/VERCEL_DEPLOYMENT.md) for complete deployment guide.

## API Reference

### Auth API (auth-api.js)

```javascript
// Initialize (done automatically)
const auth = new AuthAPI();

// Login
await authAPI.login(email, password);

// Sign Up
await authAPI.signup(email, password);

// Check Status
const user = await authAPI.checkStatus();

// Logout
await authAPI.logout();

// Get Current User
const user = authAPI.getCurrentUser();
// Returns: { email: "...", isAuthenticated: true/false }

// Check Authentication
if (authAPI.isAuthenticated()) {
    // User is authenticated
}

// Request Password Reset
await authAPI.requestPasswordReset(email);

// Reset Password (with token)
await authAPI.resetPassword(token, newPassword);

// Re-authenticate for sensitive operations
await authAPI.reauthenticate(password);
```

### Backend Endpoints

**Public Endpoints:**
- `POST /auth/login` - Email/password login
- `POST /auth/signup` - Create account
- `GET /auth/status` - Check session
- `POST /auth/logout` - Invalidate session
- `POST /auth/request-password-reset` - Start reset flow
- `POST /auth/reset-password` - Complete reset

**Protected Endpoints (require Bearer token):**
- `POST /auth/reauth` - Step-up authentication
- `POST /api/control/start` - Start pipeline
- `POST /api/control/resume` - Resume pipeline
- `POST /api/control/retry` - Retry step
- `POST /api/control/force` - Force restart
- `POST /api/control/stop` - Stop pipeline

## Environment Variables

See `.env.example` for complete list. Key variables:

```
# Required
LJV_SECRET_KEY=your-secure-key-32-chars-min
LJV_DEVELOPER_EMAIL=admin@example.com

# Session (optional - shown with defaults)
LJV_SESSION_LIFETIME_MINUTES=480
LJV_DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC=300

# CORS
LJV_ALLOWED_ORIGINS=https://your-domain.com

# Database (Vercel)
LJV_AUTH_DB_PATH=/tmp/ljv_auth.db

# Security
LJV_DEBUG=false (production)
LJV_SESSION_COOKIE_SECURE=true (production)
```

## Troubleshooting

### Login Page Shows 404
```bash
# Clear Vercel cache
vercel --prod --force
```

### Authentication Fails
1. Check `LJV_SECRET_KEY` is 32+ characters
2. Verify `LJV_DEVELOPER_EMAIL` is correct
3. Ensure `LJV_ALLOWED_ORIGINS` includes your domain
4. Check logs: `vercel logs`

### Password Reset Not Working
- Ensure `LJV_SESSION_COOKIE_SECURE=true`
- Check email configuration in backend
- Verify email provider isn't blocking

### Database Errors
- Use `/tmp/ljv_auth.db` for Vercel (ephemeral)
- Don't rely on persistent SQLite in serverless
- Consider PostgreSQL or Firebase for production

## Security Best Practices

1. ✅ Strong `LJV_SECRET_KEY` (32+ random chars)
2. ✅ `LJV_SESSION_COOKIE_SECURE=true` in production
3. ✅ HTTPS only (Vercel provides SSL automatically)
4. ✅ CORS restricted to your domain
5. ✅ Rate limiting on auth endpoints
6. ✅ Audit logging on control operations
7. ✅ Session timeout (8 hours default)
8. ✅ Never commit `.env` files
9. ✅ Rotate secrets periodically
10. ✅ Monitor failed login attempts

## Performance

Expected response times:
- **Login page load**: < 500ms
- **Authentication**: < 200ms (local) / < 500ms (Vercel)
- **Dashboard load**: < 1s
- **Control operations**: < 2s

## Next Steps

1. **Customize**: Update company branding in login.html
2. **Google OAuth**: Optional OAuth integration (Phase A)
3. **2FA**: Add TOTP support (Phase B)
4. **Monitoring**: Set up error tracking (Sentry, LogRocket)
5. **Database**: Consider persistent DB for production
6. **Custom Domain**: Add your own domain in Vercel

## Support

- **Vercel Docs**: https://vercel.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Auth Guide**: [09_DOCS/AUTH_DEPLOYMENT.md](../09_DOCS/AUTH_DEPLOYMENT.md)
- **Vercel Guide**: [09_DOCS/VERCEL_DEPLOYMENT.md](../09_DOCS/VERCEL_DEPLOYMENT.md)
