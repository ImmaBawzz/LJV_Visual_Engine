"""Authentication route handlers (login, logout, OAuth callback, status)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session as DBSession

from .config import config
from .database import User, get_db
from .security import hash_password, verify_password
from .session import (
    create_session,
    get_user_from_session,
    invalidate_session,
    mark_session_reauthed,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# === Request/Response Models ===


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ReauthRequest(BaseModel):
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class SessionResponse(BaseModel):
    session_id: str
    user_id: int
    email: str
    name: Optional[str] = None
    is_admin: bool = False


class StatusResponse(BaseModel):
    authenticated: bool
    user: Optional[SessionResponse] = None


# === Endpoints ===


@router.post("/login", response_model=SessionResponse)
async def login(
    req: LoginRequest, request: Request, db: DBSession = Depends(get_db)
):
    """
    Email/password login.
    
    On success, returns session info and sets secure session cookie.
    """
    # Look up user by email
    user = db.query(User).filter(User.email == req.email).first()

    if not user:
        # Avoid timing attacks: hash a dummy password anyway
        verify_password(req.password, "dummy-hash-value")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="This account uses OAuth. Please login with Google.",
        )

    # Verify password
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Create session
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    session_id = create_session(db, user.id, client_ip, user_agent)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"User logged in: {user.email}")

    return SessionResponse(
        session_id=session_id,
        user_id=user.id,
        email=user.email,
        name=user.name,
        is_admin=bool(user.is_admin),
    )


@router.post("/signup", response_model=SessionResponse)
async def signup(
    req: SignupRequest, request: Request, db: DBSession = Depends(get_db)
):
    """
    Email/password signup (single-admin mode).
    
    In single-admin mode, only the developer's email can sign up.
    """
    # Single-admin constraint
    if config.DEVELOPER_EMAIL and req.email != config.DEVELOPER_EMAIL:
        raise HTTPException(
            status_code=403,
            detail="Signup is restricted. Contact the system administrator.",
        )

    # Check if email already exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.email.split("@")[0],  # Default name from email
        provider="local",
        is_active=1,
        is_admin=1,  # First user is admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New user registered: {user.email}")

    # Create session immediately
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    session_id = create_session(db, user.id, client_ip, user_agent)

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return SessionResponse(
        session_id=session_id,
        user_id=user.id,
        email=user.email,
        name=user.name,
        is_admin=bool(user.is_admin),
    )


@router.post("/google/login")
async def google_login():
    """
    Redirect to Google OAuth authorization endpoint.
    """
    if not config.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Google OAuth not available")

    # This is handled by Authlib middleware; return redirect
    from starlette.responses import RedirectResponse

    return RedirectResponse(url="/auth/google/authorize")


@router.get("/google/authorize")
async def google_authorize(request: Request):
    """
    Authlib-handled OAuth redirect (in real setup, framework handles this).
    """
    if not config.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Google OAuth not available")

    # In production, Authlib middleware intercepts this
    from starlette.responses import RedirectResponse

    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/auth/google/callback"
    return RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?client_id={config.GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=openid%20email%20profile"
    )


@router.get("/google/callback")
async def google_callback(request: Request, db: DBSession = Depends(get_db)):
    """
    Google OAuth callback handler.
    
    Creates or updates user, creates session, sets cookie.
    """
    if not config.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(status_code=503, detail="Google OAuth not available")

    try:
        user_info = await handle_google_callback(request)
    except Exception as exc:
        logger.error(f"Google callback failed: {exc}")
        raise HTTPException(status_code=400, detail="Authorization failed")

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No email from Google")

    # Find or create user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # In single-admin mode, check email constraint
        if config.DEVELOPER_EMAIL and email != config.DEVELOPER_EMAIL:
            logger.warning(
                f"Signup attempt with non-developer email via Google: {email}"
            )
            raise HTTPException(
                status_code=403, detail="Signup is restricted to the developer"
            )

        user = User(
            email=email,
            name=user_info.get("name", email),
            profile_picture_url=user_info.get("picture_url"),
            provider="google",
            provider_id=user_info.get("provider_id"),
            is_active=1,
            is_admin=1,  # First user is admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New user created via Google OAuth: {email}")
    else:
        # Update user profile
        if not user.profile_picture_url:
            user.profile_picture_url = user_info.get("picture_url")
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"User logged in via Google OAuth: {email}")

    # Create session
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    session_id = create_session(db, user.id, client_ip, user_agent)

    # Return with session cookie
    from starlette.responses import JSONResponse

    response = JSONResponse(
        {
            "session_id": session_id,
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": bool(user.is_admin),
        }
    )
    _set_session_cookie(response, session_id)
    return response


@router.post("/logout")
async def logout(request: Request, db: DBSession = Depends(get_db)):
    """
    Invalidate the current session.
    """
    session_id = _get_session_id_from_request(request)

    if session_id:
        invalidate_session(db, session_id)
        logger.info(f"Session invalidated: {session_id[:8]}...")

    from starlette.responses import JSONResponse

    response = JSONResponse({"status": "logged_out"})
    _clear_session_cookie(response)
    return response


@router.post("/reauth")
async def reauth(
    req: ReauthRequest,
    request: Request,
    db: DBSession = Depends(get_db),
):
    """
    Re-authenticate current user (for destructive action step-up).
    
    Marks session as recently re-authed if password correct.
    """
    session_id = _get_session_id_from_request(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_user_from_session(db, session_id)
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Verify password
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Mark session as recently re-authed
    mark_session_reauthed(db, session_id)
    logger.info(f"Session re-authenticated: {session_id[:8]}...")

    from starlette.responses import JSONResponse

    return JSONResponse({"status": "reauthed", "window_sec": config.DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC})


@router.get("/status", response_model=StatusResponse)
async def status(request: Request, db: DBSession = Depends(get_db)):
    """
    Get current authentication status.
    
    Returns user info if authenticated, null otherwise.
    """
    session_id = _get_session_id_from_request(request)

    if not session_id:
        return StatusResponse(authenticated=False, user=None)

    user = get_user_from_session(db, session_id)

    if not user:
        return StatusResponse(authenticated=False, user=None)

    return StatusResponse(
        authenticated=True,
        user=SessionResponse(
            session_id=session_id,
            user_id=user.id,
            email=user.email,
            name=user.name,
            is_admin=bool(user.is_admin),
        ),
    )


# === Helper Functions ===


def _get_session_id_from_request(request: Request) -> Optional[str]:
    """Extract session_id from cookie or Authorization header."""
    # Try cookie first
    session_id = request.cookies.get("ljv_session")
    if session_id:
        return session_id

    # Try Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


def _set_session_cookie(response: Response, session_id: str) -> None:
    """Set secure session cookie on response."""
    response.set_cookie(
        key="ljv_session",
        value=session_id,
        max_age=int(config.SESSION_TIMEOUT_DELTA.total_seconds()),
        secure=config.SESSION_COOKIE_SECURE,
        httponly=config.SESSION_COOKIE_HTTPONLY,
        samesite=config.SESSION_COOKIE_SAMESITE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    """Clear session cookie from response."""
    response.delete_cookie(
        key="ljv_session",
        path="/",
        secure=config.SESSION_COOKIE_SECURE,
        httponly=config.SESSION_COOKIE_HTTPONLY,
        samesite=config.SESSION_COOKIE_SAMESITE,
    )
