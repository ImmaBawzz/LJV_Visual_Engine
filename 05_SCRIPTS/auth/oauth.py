"""Google OAuth flow implementation."""

from __future__ import annotations

import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

from .config import config

logger = logging.getLogger(__name__)


def get_google_authorization_url(state_token: str) -> str:
    """
    Generate Google OAuth authorization URL.
    
    Args:
        state_token: CSRF protection token
    
    Returns:
        Full authorization URL to redirect to
    """
    if not config.GOOGLE_OAUTH_ENABLED:
        raise RuntimeError("Google OAuth not enabled")

    params = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state_token,
    }

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def handle_google_callback(code: str, state: str) -> Optional[dict]:
    """
    Exchange authorization code for tokens and fetch user info.
    
    Requires additional implementation with an HTTP client (httpx or requests).
    For now, returns a stub indicating the need for server-side token exchange.
    
    In production, use:
    - google-auth-oauthlib for browser-based flow OR
    - requests + google-auth for server-side token exchange
    """
    if not config.GOOGLE_OAUTH_ENABLED:
        raise RuntimeError("Google OAuth not enabled")

    # NOTE: Full OAuth token exchange requires making an HTTPS POST to Google's token endpoint.
    # This is deferred to allow flexible implementation (sync requests vs async httpx).
    # 
    # Basic flow:
    # 1. Exchange code for tokens (POST to https://oauth2.googleapis.com/token)
    # 2. Fetch userinfo from tokens (GET to https://www.googleapis.com/oauth2/v2/userinfo)
    # 3. Verify token signature and expiry
    # 4. Return user data (email, name, picture, sub)
    
    raise NotImplementedError(
        "Google OAuth token exchange requires google-auth libraries. "
        "Install: pip install google-auth google-auth-oauthlib google-auth-httplib2"
    )


def get_google_redirect_uri() -> str:
    """Get the configured Google OAuth redirect URI."""
    return config.GOOGLE_REDIRECT_URI


def generate_state_token() -> str:
    """Generate a CSRF protection token."""
    return secrets.token_urlsafe(32)

