# Deploying LJV Visual Engine to Vercel

This guide walks you through deploying the LJV Visual Engine dashboard with authentication to Vercel.

## Prerequisites

1. **GitHub Account** - Repository must be hosted on GitHub
2. **Vercel Account** - Free account at https://vercel.com
3. **Python 3.8+** - For backend dependencies
4. **Environment Variables** - See `.env.example` for required configuration

## Step 1: Prepare Your Repository

### 1.1 Ensure All Files are Committed

```bash
git status
git add -A
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### 1.2 Create Environment Configuration

1. Copy `.env.example` to `.env.local` for local testing
2. Fill in your environment variables:
   ```bash
   LJV_SECRET_KEY=your-secure-random-key
   LJV_DEVELOPER_EMAIL=your-admin@email.com
   LJV_ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
   ```

## Step 2: Deploy to Vercel

### Option A: Using Vercel CLI (Recommended)

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login to Vercel
vercel login

# 3. Deploy
vercel --prod
```

### Option B: Using Vercel Dashboard

1. Go to https://vercel.com/dashboard
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. Click "Import"

## Step 3: Configure Environment Variables in Vercel

### Via CLI:
```bash
vercel env add LJV_SECRET_KEY
vercel env add LJV_DEVELOPER_EMAIL
vercel env add LJV_ALLOWED_ORIGINS
# ... repeat for other variables
```

### Via Dashboard:
1. Go to your project settings
2. Click "Environment Variables"
3. Add each variable:
   - **Name**: Variable name (e.g., `LJV_SECRET_KEY`)
   - **Value**: Your value
   - **Environments**: Select "Production" (and optionally "Preview" and "Development")
4. Click "Add"

**Critical Variables:**
- `LJV_SECRET_KEY` - Must be unique and secure (32+ characters)
- `LJV_DEVELOPER_EMAIL` - Your admin email
- `LJV_ALLOWED_ORIGINS` - Your Vercel domain (e.g., `https://myapp.vercel.app`)
- `LJV_SESSION_COOKIE_SECURE` - Set to `true` for HTTPS
- `LJV_AUTH_DB_PATH` - Set to `/tmp/ljv_auth.db` (Vercel uses ephemeral filesystem)

## Step 4: First Login

Once deployed:

1. Open your Vercel domain: `https://your-app.vercel.app/login.html`
2. Click "Sign Up"
3. Enter your admin email (from `LJV_DEVELOPER_EMAIL`)
4. Create a secure password (8+ characters)
5. Click "Create Account"
6. You're now logged in! You'll be redirected to the dashboard

## Important Notes for Vercel

### Database Persistence

Vercel has an **ephemeral filesystem** - files created during execution are deleted when the function terminates.

**Solution:** Use `LJV_AUTH_DB_PATH=/tmp/ljv_auth.db`

For persistent data, migrate to:
- **Vercel PostgreSQL** (recommended)
- **Firebase Realtime Database**
- **AWS RDS**
- **PlanetScale**

### Session Storage

Sessions are stored in SQLite by default. For production with multiple instances, consider:
- Redis (Upstash)
- Memcached
- PostgreSQL

### CORS Configuration

Update `LJV_ALLOWED_ORIGINS` to include all your domains:
```
https://myapp.vercel.app,https://www.myapp.vercel.app
```

### SSL/TLS Certificates

Vercel automatically provides HTTPS/SSL certificates. No additional configuration needed.

## Step 5: Custom Domain (Optional)

1. In Vercel Dashboard, click your project
2. Go to "Settings" → "Domains"
3. Click "Add"
4. Enter your custom domain
5. Follow DNS configuration instructions

## Monitoring and Logs

### View Logs
```bash
vercel logs your-project-name
```

### View Real-time Logs
```bash
vercel logs your-project-name --follow
```

## Troubleshooting

### 404 on /login.html
- Ensure `vercel.json` routes are correctly configured
- Clear Vercel cache and redeploy: `vercel --prod --force`

### 500 Error on Login
1. Check environment variables are set
2. View logs: `vercel logs`
3. Ensure `LJV_SECRET_KEY` is at least 32 characters

### Authentication Fails
- Verify `LJV_DEVELOPER_EMAIL` is set correctly
- Check `LJV_ALLOWED_ORIGINS` includes your domain
- Ensure `LJV_SESSION_COOKIE_SECURE=true` for HTTPS

### Database Errors
- Check `LJV_AUTH_DB_PATH` is set to `/tmp/`
- Ensure write permissions in `/tmp/`
- Consider migrating to persistent database

## Production Checklist

- [ ] `LJV_SECRET_KEY` is strong (32+ chars, random)
- [ ] `LJV_DEBUG` is set to `false`
- [ ] `LJV_SESSION_COOKIE_SECURE` is `true`
- [ ] `LJV_ALLOWED_ORIGINS` includes your domain
- [ ] Custom domain configured (if applicable)
- [ ] Monitoring/logging configured
- [ ] Know how to access logs
- [ ] Have backup authentication method documented
- [ ] Test login on production URL
- [ ] Share login credentials securely with team

## Updating Your Deployment

### Deploy Changes
```bash
git add -A
git commit -m "Update message"
git push origin main
vercel --prod
```

Or simply push to GitHub if you've connected Vercel to your repo (automatic deployments).

## Rolling Back

### Revert to Previous Deployment
```bash
vercel rollback
```

### Or Redeploy Specific Commit
```bash
vercel --prod
```

## Scaling and Performance

### Expected Performance
- Login page: < 500ms load time
- Authentication: < 200ms response time
- Dashboard: < 1s initial load

### Optimization Tips
1. CDN static assets (Vercel does this automatically)
2. Enable compression (use `Content-Encoding` headers)
3. Implement request caching where appropriate
4. Monitor function execution time in logs

## Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` only
2. **Rotate `LJV_SECRET_KEY`** periodically
3. **Monitor login attempts** - Check audit logs
4. **Enable 2FA** - Consider adding TOTP support
5. **Update dependencies** - Keep Python packages current
6. **Use strong passwords** - Enforce during admin creation
7. **Monitor CORS** - Don't allow all origins (`*`)
8. **Use HTTPS only** - Set `LJV_SESSION_COOKIE_SECURE=true`

## Support and Documentation

- **Vercel Docs**: https://vercel.com/docs
- **Python Runtime**: https://vercel.com/docs/runtimes/python
- **Environment Variables**: https://vercel.com/docs/concepts/projects/environment-variables
- **Local Testing**: Use `.env.local` with `vercel dev` command

## Next Steps

1. Configure persistent database (if needed)
2. Set up Google OAuth (optional)
3. Implement 2FA
4. Configure monitoring/alerting
5. Create disaster recovery plan
