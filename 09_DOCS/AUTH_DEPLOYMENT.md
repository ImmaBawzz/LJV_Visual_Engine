# Authentication & Dashboard Deployment Guide

## Overview

The LJV Visual Engine dashboard uses **email/password authentication** with bcrypt hashing and secure session management. The system features:
- **Signup & Login UI** with modern split-tab interface
- **Email/Password login** with bcrypt-hashed passwords
- **Google OAuth** (optional enhancement, disabled by default)
- **Session-based auth** with configurable TTL and step-up re-authentication for destructive actions
- **Vercel deployment** with environment variable management from Vercel secrets

This guide covers local development, Vercel deployment, and production hardening.

## Architecture

```
┌─────────────────────────────────────────┐
│      05_SCRIPTS/dashboard/static/       │
│  ├─ login.html (Signup/Login UI)        │
│  └─ dashboard.html (Control Panel)      │
├─────────────────────────────────────────┤
│      05_SCRIPTS/dashboard/app.py        │
│  (FastAPI + Uvicorn or Vercel Runtime)  │
├─────────────────────────────────────────┤
│      05_SCRIPTS/auth/                   │
│  ├─ routes.py (Auth endpoints)          │
│  ├─ guards.py (Permission checks)       │
│  ├─ middleware.py (Security headers)    │
│  ├─ database.py (SQLite schema)         │
│  └─ config.py (Env validation)          │
├─────────────────────────────────────────┤
│  SQLite Database (auth.db)              │
│  ├─ users (email, password_hash, roles) │
│  └─ sessions (session_id, user_id, exp)│
└─────────────────────────────────────────┘
```

## Quick Start (Local Development)

### 1. Install Dependencies

```bash
pip install -r REQUIREMENTS.md
```

Dependencies include:
- `sqlalchemy` — ORM for SQLite
- `passlib[bcrypt]` — Password hashing
- `python-jose` — JWT/session tokens
- `authlib` — OAuth (optional)
- `python-multipart` — Form data parsing
- `email-validator` — Email validation

### 2. Set Environment Variables (Local Dev)

Create a `.env` file in the project root or set via shell:

```bash
# Debug & Security
export LJV_DEBUG=true
export LJV_SECRET_KEY=dev-secret-change-in-production
export LJV_SESSION_LIFETIME_MINUTES=480
export LJV_SESSION_COOKIE_SECURE=false  # HTTP only for localhost
export LJV_DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC=300

# CORS & Origins
export LJV_ALLOWED_ORIGINS=http://127.0.0.1:8787,http://localhost:8787

# First Admin Account (Signup Only)
export LJV_DEVELOPER_EMAIL=your-email@example.com

# OAuth (Optional)
export LJV_GOOGLE_OAUTH_ENABLED=false

# Database
export LJV_AUTH_DB_PATH=./auth.db
```

### 3. Run Dashboard Locally

```bash
cd 05_SCRIPTS/dashboard
python app.py
```

The app starts on `http://127.0.0.1:8787`

### 4. Create First Admin Account

1. Navigate to `http://127.0.0.1:8787/login.html`
2. Click the **"Sign Up"** tab
3. Enter:
   - **Email:** `your-email@example.com` (must match `LJV_DEVELOPER_EMAIL`)
   - **Password:** 8+ characters, strong recommended
4. Click **"Create Account"**
5. Switch to **"Login"** tab and sign in with your credentials

## Production Deployment

### Option A: Vercel Deployment (Recommended)

Vercel provides the easiest path to production with automatic HTTPS, global CDN, and zero configuration beyond environment secrets.

#### Prerequisites

- Vercel account (free or paid)
- GitHub repository (linked to Vercel project)
- Custom domain (optional, Vercel provides default)

#### Step 1: Push to GitHub

```bash
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

#### Step 2: Import Project to Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**
2. Import your GitHub repository
3. Select project root (the LJV_Visual_Engine directory)
4. Click **Deploy**

Vercel reads `vercel.json` automatically and sets up the build.

#### Step 3: Configure Environment Secrets

In Vercel Dashboard → **Settings** → **Environment Variables**, add each **as a secret**:

| Variable | Value | Type |
|----------|-------|------|
| `LJV_SECRET_KEY` | Strong random string (32+ chars) | Secret |
| `LJV_DEVELOPER_EMAIL` | Your admin email | Secret |
| `LJV_ALLOWED_ORIGINS` | `https://your-domain.vercel.app` | Secret |
| `LJV_DEBUG` | `false` | Plaintext |
| `LJV_SESSION_COOKIE_SECURE` | `true` | Plaintext |
| `LJV_GOOGLE_OAUTH_ENABLED` | `false` | Plaintext |

**Generate a strong secret key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 4: Redeploy with Environment Variables

After setting environment variables, trigger a new deployment:
1. Go to **Deployments** tab
2. Click the three dots on the latest deployment
3. Select **Redeploy**

Or push a new commit to trigger automatic redeployment.

#### Step 5: Verify Deployment

1. Visit `https://your-app.vercel.app/login.html`
2. Sign up with your `LJV_DEVELOPER_EMAIL`
3. If signup fails with "Email not authorized", check Vercel logs:
   ```
   Vercel Dashboard → Deployments → [Latest] → Functions → Logs
   ```
4. Check for environment variable errors

#### Vercel Configuration Details

The `vercel.json` file controls:

```json
{
  "buildCommand": "cd 05_SCRIPTS/dashboard && pip install -r ../../REQUIREMENTS.md",
  "env": {
    "LJV_AUTH_DB_PATH": "/tmp/ljv_auth.db"  // Writable temp directory
  },
  "functions": {
    "05_SCRIPTS/dashboard/app.py": {
      "memory": 3008,  // 3GB max for FastAPI
      "maxDuration": 60  // 60s timeout
    }
  }
}
```

**Important:** On Vercel (serverless), the database is stored in `/tmp/ljv_auth.db`, which is **ephemeral**. Each function restart clears it. For persistent auth:
- Migrate to PostgreSQL or MongoDB (see "Database" section below)
- Or use Vercel KV for session storage

#### Vercel Limitations & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Auth DB lost after redeploy | `/tmp` cleared on restart | Use PostgreSQL or Vercel PostgreSQL |
| Session expires immediately | Session not persisted | Store sessions in Vercel KV or database |
| 502 errors | Memory/timeout exceeded | Increase `memory` in `vercel.json` |
| Slow cold starts | Python runtime initialization | Unavoidable; use Vercel Edge Middleware for static content |

---

### Option B: Traditional Server Deployment (AWS EC2, DigitalOcean, VPS)

For self-hosted deployments with persistent storage.

#### Prerequisites

- Linux server (Ubuntu 22.04+ recommended)
- Python 3.10+
- systemd init system
- Reverse proxy (Nginx or Caddy)
- TLS certificate (Let's Encrypt)

#### Step 1: Prepare Server

```bash
# SSH into server
ssh ubuntu@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3-pip python3-venv nginx certbot python3-certbot-nginx

# Create app directory
sudo mkdir -p /opt/ljv
sudo chown ubuntu:ubuntu /opt/ljv
cd /opt/ljv
```

#### Step 2: Clone & Configure

```bash
git clone https://github.com/your-org/ljv-visual-engine.git .
python3 -m venv venv
source venv/bin/activate
pip install -r REQUIREMENTS.md
```

#### Step 3: Environment Configuration

#### Step 3: Environment Configuration

Create `/etc/ljv/.env`:

```bash
# === Security ===
LJV_DEBUG=false
LJV_SECRET_KEY=your-strong-random-key-min-32-chars
LJV_SESSION_COOKIE_SECURE=true
LJV_SESSION_LIFETIME_MINUTES=480
LJV_DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC=300

# === CORS & Domain ===
LJV_ALLOWED_ORIGINS=https://ljv.example.com

# === Admin ===
LJV_DEVELOPER_EMAIL=admin@example.com

# === Database ===
LJV_AUTH_DB_PATH=/var/lib/ljv/auth.db

# === Rate Limiting ===
LJV_AUTH_RATE_LIMIT_ATTEMPTS=5
LJV_AUTH_RATE_LIMIT_WINDOW_SEC=300
```

Generate a strong secret:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 4: Create systemd Service

Create `/etc/systemd/system/ljv-dashboard.service`:

```ini
[Unit]
Description=LJV Visual Engine Dashboard
After=network.target
Documentation=https://your-org/docs

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/ljv
EnvironmentFile=/etc/ljv/.env
ExecStart=/opt/ljv/venv/bin/python3 -m uvicorn 05_SCRIPTS.dashboard.app:app \
    --host 127.0.0.1 --port 8787 --log-level info
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ljv-dashboard
sudo systemctl start ljv-dashboard

# Verify
systemctl status ljv-dashboard
journalctl -u ljv-dashboard -f
```

#### Step 5: Nginx Reverse Proxy

Create `/etc/nginx/sites-enabled/ljv`:

```nginx
upstream ljv_app {
    server 127.0.0.1:8787 fail_timeout=0;
}

server {
    listen 80;
    server_name ljv.example.com www.ljv.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ljv.example.com www.ljv.example.com;
    
    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/ljv.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ljv.example.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    location / {
        proxy_pass http://ljv_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Session cookie preservation
        proxy_cookie_path / /;
        proxy_cookie_flags ~ secure httponly samesite=lax;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static/ {
        alias /opt/ljv/05_SCRIPTS/dashboard/static/;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
}
```

Test & reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### Step 6: Install SSL Certificate

```bash
sudo certbot certonly --nginx -d ljv.example.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

#### Step 7: Database Initialization

```bash
sudo mkdir -p /var/lib/ljv
sudo chown ubuntu:ubuntu /var/lib/ljv
chmod 700 /var/lib/ljv

# Start service (auto-initializes DB)
sudo systemctl start ljv-dashboard

# Verify
sqlite3 /var/lib/ljv/auth.db ".tables"
```

Expected output: `sessions users`

---

### Database Migration (From SQLite)

For production, migrate from SQLite to PostgreSQL:

#### PostgreSQL Option

```bash
# Install PostgreSQL driver
pip install psycopg2-binary

# Set environment variable
export LJV_AUTH_DB_URL="postgresql://ljv_user:password@localhost/ljv_auth"

# Restart service
sudo systemctl restart ljv-dashboard
```

Update `05_SCRIPTS/auth/database.py` to use PostgreSQL:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Use environment variable or fall back to SQLite
db_url = os.getenv("LJV_AUTH_DB_URL", "sqlite:///auth.db")
engine = create_engine(
    db_url,
    poolclass=QueuePool if "postgresql" in db_url else None,
)
```

## Testing & Verification

### Manual API Tests

#### 1. Signup (Create First Admin)

```bash
curl -X POST http://127.0.0.1:8787/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email":"admin@example.com",
    "password":"SecurePassword123!"
  }'
```

Response:
```json
{
  "message": "User created successfully. Please log in.",
  "email": "admin@example.com"
}
```

#### 2. Login (Get Session Token)

```bash
curl -X POST http://127.0.0.1:8787/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"admin@example.com",
    "password":"SecurePassword123!"
  }' \
  -c cookies.txt  # Save session cookie
```

Response:
```json
{
  "access_token": "your-session-token",
  "token_type": "bearer",
  "user": {
    "email": "admin@example.com",
    "is_admin": true
  }
}
```

#### 3. Check Session Status

```bash
curl -X GET http://127.0.0.1:8787/auth/status \
  -b cookies.txt  # Use session cookie
```

Response:
```json
{
  "authenticated": true,
  "email": "admin@example.com",
  "is_admin": true
}
```

#### 4. Start Pipeline (Requires Admin)

```bash
curl -X POST http://127.0.0.1:8787/api/control/start \
  -b cookies.txt
```

#### 5. Force Restart (Requires Step-Up)

```bash
curl -X POST http://127.0.0.1:8787/api/control/force \
  -b cookies.txt
```

If step-up required (first destructive action > 5 min after login):
```json
{
  "error": "re-authentication required",
  "code": 428,
  "message": "Please log in again before performing this action"
}
```

Re-login to clear the step-up requirement.

### Automated Tests

Run pytest suite:

```bash
cd 05_SCRIPTS/auth
pytest tests/ -v
```

Expected tests:
- ✓ Signup with valid email
- ✓ Signup with invalid email (rejected)
- ✓ Signup with duplicate email (rejected)
- ✓ Login with correct password
- ✓ Login with wrong password (rejected)
- ✓ Session expiry after TTL
- ✓ Admin-only endpoints (require is_admin=1)
- ✓ Destructive action step-up (require re-auth)
- ✓ Rate limiting (5 failures = 5-minute lockout)

### Browser Workflow Test

1. **Signup Phase:**
   - Go to `http://127.0.0.1:8787/login.html`
   - Click "Sign Up" tab
   - Fill email & password
   - Click "Create Account"
   - Expect: "Account created" message

2. **Login Phase:**
   - Click "Login" tab
   - Enter same credentials
   - Click "Login"
   - Redirected to `/dashboard.html`
   - Session cookie created

3. **Control Panel:**
   - Dashboard shows pipeline controls: **Start**, **Pause**, **Force Restart**
   - Click **Start** → pipeline begins
   - Click **Force Restart** → after 5 min idle, shows step-up prompt
   - Re-enter password → destructive action allowed

---

## Troubleshooting

### Signup Email Not Authorized

**Symptom:** Signup form shows "Email not authorized" error

**Causes:**
1. Email doesn't match `LJV_DEVELOPER_EMAIL` environment variable
2. Environment variable not set on Vercel

**Fix:**
```bash
# Check environment variable
echo $LJV_DEVELOPER_EMAIL

# Set correct admin email
export LJV_DEVELOPER_EMAIL=your-admin@domain.com

# Restart app (local)
# Or redeploy on Vercel
```

### "Session Expired" or "Not Authenticated"

**Symptom:** After login, dashboard shows 401 Unauthorized

**Causes:**
1. Session cookie not set (CORS issue)
2. Session TTL exceeded (default 8 hours)
3. Database/session table corrupted

**Fix:**
```bash
# Clear browser cookies and re-login
# Or check session in database:
sqlite3 /var/lib/ljv/auth.db \
  "SELECT session_id, user_id, expires_at FROM sessions ORDER BY expires_at DESC LIMIT 5;"

# Delete expired sessions:
sqlite3 /var/lib/ljv/auth.db \
  "DELETE FROM sessions WHERE expires_at < datetime('now');"
```

### "Admin Privileges Required"

**Symptom:** Control endpoints return 403 Forbidden

**Causes:**
1. User account created but not marked as admin
2. `LJV_DEVELOPER_EMAIL` mismatch

**Fix:**
```bash
# Check user admin status
sqlite3 /var/lib/ljv/auth.db "SELECT email, is_admin FROM users;"

# Grant admin if needed
sqlite3 /var/lib/ljv/auth.db "UPDATE users SET is_admin=1 WHERE email='admin@example.com';"
```

### Google OAuth Returns "Invalid Redirect URI"

**Symptom:** OAuth login fails with 400 error

**Causes:**
1. Redirect URI in Google Cloud Console doesn't match app configured origin
2. Google+ API not enabled

**Fix:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project → APIs & Services → Credentials
3. Edit OAuth 2.0 Client ID → Update "Authorized redirect URIs" to exactly:
   ```
   https://your-domain.com/auth/google/callback
   ```
4. Enable Google+ API if disabled

### Rate Limiting Locked Out

**Symptom:** Login attempts rejected, "Too many failed attempts"

**Causes:**
1. 5+ failed password attempts in last 5 minutes

**Fix:**
```bash
# Wait 5 minutes, OR
# Reset rate limit in database (dev only):
sqlite3 /var/lib/ljv/auth.db \
  "DELETE FROM failed_attempts WHERE created_at < datetime('now', '-5 minutes');"
```

### Vercel Deployment: Database Always Empty

**Symptom:** After redeployment, need to re-signup (auth DB lost)

**Root Cause:** Vercel serverless uses ephemeral `/tmp`, cleared on restart

**Solution Options:**
1. **Migrate to PostgreSQL** (recommended for production)
   ```bash
   # Set LJV_AUTH_DB_URL to PostgreSQL connection string in Vercel
   export LJV_AUTH_DB_URL="postgresql://user:pass@db.domain.com/ljv_auth"
   ```

2. **Use Vercel KV** (Redis alternative)
   ```bash
   # Install redis client
   pip install redis
   
   # Update 05_SCRIPTS/auth/database.py to use Vercel KV
   ```

3. **Accept ephemeral auth** (dev/demo only)
   - Acknowledge data loss on redeploy
   - Use for testing only

### Nginx Error: 502 Bad Gateway

**Symptom:** All requests return 502

**Causes:**
1. FastAPI app crashed or not listening on 127.0.0.1:8787
2. Systemd service failed

**Fix:**
```bash
# Check service status
sudo systemctl status ljv-dashboard
sudo journalctl -u ljv-dashboard -n 20

# Check if port 8787 is listening
sudo netstat -tulpn | grep 8787

# Restart service
sudo systemctl restart ljv-dashboard
```

### SSL Certificate Issues

**Symptom:** Browser shows "Not Secure" or "Expired Certificate"

**Fix:**
```bash
# Check certificate expiry
sudo openssl x509 -in /etc/letsencrypt/live/ljv.example.com/fullchain.pem -noout -dates

# Force renewal
sudo certbot renew --force-renewal

# Reload Nginx
sudo systemctl reload nginx
```

---

## Monitoring & Observability

### View Auth Logs

```bash
# All auth activity
sudo journalctl -u ljv-dashboard | grep "AUTH\|LOGIN\|SIGNUP"

# Real-time tail
sudo journalctl -u ljv-dashboard -f

# Parse structured logs (JSON)
sudo journalctl -u ljv-dashboard -o json --all | jq '.MESSAGE | fromjson?'
```

### Control Action Audit Trail

Every pipeline control action (start, pause, force) is logged with:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "action": "start",
  "user": "admin@example.com",
  "user_id": 1,
  "ip_address": "203.0.113.45",
  "status": "success",
  "notes": "Initiated by dashboard UI"
}
```

View recent actions:
```bash
tail -100 /path/to/app.log | grep "CONTROL_ACTION"
```

### Monitor Session Usage

```bash
# Active sessions
sqlite3 /var/lib/ljv/auth.db \
  "SELECT COUNT(*) as active_sessions FROM sessions WHERE expires_at > datetime('now');"

# Sessions by user
sqlite3 /var/lib/ljv/auth.db \
  "SELECT u.email, COUNT(s.session_id) as session_count FROM users u \
   LEFT JOIN sessions s ON u.id = s.user_id \
   WHERE s.expires_at > datetime('now') \
   GROUP BY u.id;"
```

---

## Security Hardening Checklist

- [ ] `LJV_SECRET_KEY` is 32+ characters, random, not stored in git
- [ ] `LJV_DEBUG=false` in production
- [ ] `LJV_SESSION_COOKIE_SECURE=true` (HTTPS only)
- [ ] `LJV_ALLOWED_ORIGINS` restricted to your domain(s)
- [ ] Session TTL configured (default 480 min = 8 hours)
- [ ] Step-up re-auth enabled for destructive actions (300 sec = 5 min)
- [ ] Rate limiting enabled (5 attempts per 300 sec)
- [ ] Database file owned by app user, not world-readable (`chmod 600 auth.db`)
- [ ] OAuth secrets (if enabled) stored in environment, not in code
- [ ] HTTPS/TLS enforced via reverse proxy
- [ ] Security headers set (HSTS, CSP, X-Frame-Options, etc.)
- [ ] Logs monitored for suspicious patterns (rate limit spikes, failed logins)
- [ ] Database backups automated (for persistent deployments)
- [ ] Admin user password strong (12+ chars, mixed case + symbols)
- [ ] Periodic password rotation policy (if multi-admin)

---

## Advanced Configuration

### Custom Session Store (Redis)

Replace SQLite sessions with Redis for multi-instance deployments:

```python
# 05_SCRIPTS/auth/database.py
import redis
from datetime import timedelta

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

def create_session(user_id: int) -> str:
    session_id = secrets.token_urlsafe(32)
    expires_in = timedelta(minutes=int(os.getenv("LJV_SESSION_LIFETIME_MINUTES", 480)))
    redis_client.setex(
        f"session:{session_id}",
        int(expires_in.total_seconds()),
        user_id
    )
    return session_id
```

### IP Whitelisting

Add to authentication config:

```python
# 05_SCRIPTS/auth/config.py
ALLOWED_IPS = os.getenv("LJV_ALLOWED_IPS", "").split(",")  # "203.0.113.0/24,192.168.0.0/16"

# In auth route
@app.post("/auth/login")
async def login(request: Request, credentials: LoginRequest):
    client_ip = request.client.host
    if ALLOWED_IPS and client_ip not in ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="IP not whitelisted")
    # ... rest of login logic
```

### Two-Factor Authentication (2FA)

Add TOTP-based 2FA:

```bash
pip install pyotp qrcode
```

See `05_SCRIPTS/auth/2fa.py` for TOTP enrollment and verification.
