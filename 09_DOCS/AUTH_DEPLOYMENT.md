# Authentication & Dashboard Deployment Guide

## Overview

The LJV Visual Engine dashboard now supports secure authentication with Google OAuth and email/password login. This guide covers setup, environment configuration, and deployment procedures.

## Quick Start (Local Development)

### 1. Install Dependencies

```bash
pip install sqlalchemy passlib[bcrypt] python-jose authlib python-multipart email-validator
```

Or use the updated REQUIREMENTS.md:

```bash
pip install -r requirements.txt  # Update with new auth dependencies
```

### 2. Set Environment Variables (Local Dev)

```bash
# For local testing, set these in your shell or .env file:
export LJV_DEBUG=true
export LJV_SECRET_KEY=dev-secret-change-in-production
export LJV_ALLOWED_ORIGINS=http://127.0.0.1:8787,http://localhost:8787
export LJV_SESSION_COOKIE_SECURE=false
export LJV_DEVELOPER_EMAIL=your-email@example.com  # For single-admin signup
export LJV_GOOGLE_OAUTH_ENABLED=false  # For now, test email/password
```

### 3. Run Dashboard

```bash
cd 05_SCRIPTS/dashboard
python app.py
```

Navigate to `http://127.0.0.1:8787/login.html`

### 4. Create First Admin Account

On the login page, click "Sign Up" and enter:
- Email: `your-email@example.com` (must match `LJV_DEVELOPER_EMAIL`)
- Password: Your secure password (8+ characters)

## Production Deployment

### Prerequisites

- Python 3.10+
- FastAPI + Uvicorn (already in REQUIREMENTS.md)
- Reverse proxy with TLS (Caddy, Nginx, or Apache)
- Valid domain name (e.g., `ljv-engine.example.com`)

### Google OAuth Setup (Optional; Email/Password Sufficient for MVP)

**Note:** The current implementation supports email/password login fully. Google OAuth is available as an optional enhancement and requires additional setup files in the `05_SCRIPTS/auth/` directory.

For **MVP/initial deployment**, use email/password only:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable APIs:
   - Google+ API
   - Google Identity Services
4. Create OAuth 2.0 credentials:
   - Type: **Web application**
   - Authorized JavaScript origins: `https://ljv-engine.example.com`
   - Authorized redirect URIs: `https://ljv-engine.example.com/auth/google/callback`
5. Copy client ID and secret

### Environment Configuration

Create a `.env` file or use systemd environ/Docker secrets:

```bash
# === Production Security ===
LJV_DEBUG=false
LJV_SECRET_KEY=your-strong-random-key-min-32-chars
LJV_SESSION_COOKIE_SECURE=true  # HTTPS only
LJV_SESSION_LIFETIME_MINUTES=480  # 8 hours
LJV_DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC=300  # 5 minutes

# === CORS & Origins ===
LJV_ALLOWED_ORIGINS=https://ljv-engine.example.com

# === Google OAuth (Optional) ===
LJV_GOOGLE_OAUTH_ENABLED=false  # Start with email/password only

# === Single-Admin Mode ===
LJV_DEVELOPER_EMAIL=admin@example.com

# === Database ===
LJV_AUTH_DB_PATH=/var/lib/ljv/auth.db

# === Rate Limiting ===
LJV_AUTH_RATE_LIMIT_ATTEMPTS=5
LJV_AUTH_RATE_LIMIT_WINDOW_SEC=300
```

Save to `/etc/ljv/env` or load into your deployment environment.

### Reverse Proxy Configuration (Caddy)

```caddy
ljv-engine.example.com {
  reverse_proxy 127.0.0.1:8787
  
  # Security headers (already set by app middleware, but good to reinforce)
  header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
  header X-Content-Type-Options nosniff
  header X-Frame-Options DENY
}
```

### Reverse Proxy Configuration (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name ljv-engine.example.com;
    
    ssl_certificate /etc/letsencrypt/live/ljv-engine.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ljv-engine.example.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Preserve session cookies
        proxy_cookie_path / /;
        proxy_cookie_flags ~ secure httponly samesite=lax;
    }
}
```

### Systemd Service

Create `/etc/systemd/system/ljv-dashboard.service`:

```ini
[Unit]
Description=LJV Visual Engine Dashboard
After=network.target
Wants=ljv-pipeline.service

[Service]
Type=simple
User=ljv
Group=ljv
WorkingDirectory=/opt/ljv/
EnvironmentFile=/etc/ljv/env
ExecStart=/usr/bin/python3 -m uvicorn 05_SCRIPTS.dashboard.app:app --host 127.0.0.1 --port 8787
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ljv-dashboard
sudo systemctl start ljv-dashboard
```

### Database Initialization

On first deployment, the database is auto-initialized by the app lifespan. Verify:

```bash
ls -la /var/lib/ljv/auth.db
sqlite3 /var/lib/ljv/auth.db ".tables"
```

Expected tables: `users`, `sessions`

### First Admin Account (Production)

1. Start the service
2. Access `https://ljv-engine.example.com/login.html`
3. Click "Sign Up" with the email from `LJV_DEVELOPER_EMAIL`
4. Create account
5. Log in with credentials or Google OAuth (if enabled)

## Testing

### Manual API Tests

**Login with email/password:**
```bash
curl -X POST http://127.0.0.1:8787/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"mypassword"}'
```

**Check session status:**
```bash
curl -X GET http://127.0.0.1:8787/auth/status \
  -H "Authorization: Bearer YOUR_SESSION_ID"
```

**Start pipeline (requires auth):**
```bash
curl -X POST http://127.0.0.1:8787/api/control/start \
  -H "Authorization: Bearer YOUR_SESSION_ID"
```

**Force restart (requires step-up):**
```bash
curl -X POST http://127.0.0.1:8787/api/control/force \
  -H "Authorization: Bearer YOUR_SESSION_ID"
```

Should return 428 if re-auth window expired.

### Automated Tests

See `05_SCRIPTS/auth/tests/` directory for pytest suite covering:
- Email/password login flow
- Google OAuth callback validation
- Session expiry
- Destructive action step-up checks
- Rate limiting

Run: `pytest 05_SCRIPTS/auth/tests/`

## Troubleshooting

### "Session expired" on dashboard

The session cookie may have expired (8 hours default) or the session table was cleared.

**Fix:** Log in again via `http://your-domain/login.html`

### Google OAuth redirect fails

Verify in Google Cloud Console:
1. Client ID and secret are correct
2. Authorized redirect URI matches *exactly* (protocol + domain + path)
3. Google+ API is enabled

### Database locked errors

If running multiple dashboard instances, ensure they use separate database paths or implement shared storage (SQLite over NFS not recommended). For production: migrate to PostgreSQL.

### "Admin privileges required"

Only users with `is_admin=1` can control the pipeline. Check database:

```bash
sqlite3 /var/lib/ljv/auth.db "SELECT email, is_admin FROM users;"
```

To fix: `UPDATE users SET is_admin=1 WHERE email='your@email.com';`

## Monitoring & Logs

Auth actions are logged with identity context:

```bash
tail -f /path/to/app.log | grep "CONTROL_ACTION"
```

Example log output:
```
CONTROL_ACTION [start] user=admin@example.com (id=1) from 203.0.113.45 [success]
CONTROL_ACTION [force] user=admin@example.com (id=1) from 203.0.113.45 [success]
```

## Security Checklist

- [ ] `LJV_SECRET_KEY` is a strong random string (not "dev-secret-...")
- [ ] `LJV_SESSION_COOKIE_SECURE=true` in production
- [ ] HTTPS/TLS enabled via reverse proxy
- [ ] Database file is readable only by app process (`chmod 600 auth.db`)
- [ ] Google OAuth secrets stored in environment, not in code
- [ ] Rate limiting enabled (`LJV_AUTH_RATE_LIMIT_ATTEMPTS > 0`)
- [ ] CORS allowed origins restricted to your domain
- [ ] Session timeout appropriate for your use case
- [ ] Destructive action re-auth window configured (5-10 minutes recommended)

## Additional References

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Authlib Documentation](https://docs.authlib.org/)
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
