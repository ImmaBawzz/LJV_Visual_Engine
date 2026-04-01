"""Session management: creation, validation, expiry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from .config import config
from .database import Session as SessionModel, User
from .security import generate_session_token


def create_session(
    db: DBSession, user_id: int, client_ip: str = "", user_agent: str = ""
) -> str:
    """
    Create a new server-side session for a user.
    
    Returns the session_id token.
    """
    session_id = generate_session_token()
    now = datetime.now(timezone.utc)
    expires_at = now + config.SESSION_TIMEOUT_DELTA

    session_data = {"client_ip": client_ip, "user_agent": user_agent}

    db_session = SessionModel(
        session_id=session_id,
        user_id=user_id,
        data=str(session_data),
        created_at=now,
        last_used_at=now,
        expires_at=expires_at,
    )
    db.add(db_session)
    db.commit()

    return session_id


def validate_session(db: DBSession, session_id: str) -> Optional[int]:
    """
    Validate a session token.
    
    Returns user_id if valid, None if expired or not found.
    Updates last_used_at on success.
    """
    now = datetime.now(timezone.utc)

    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id
    ).first()

    if not session:
        return None

    # Check expiry
    if session.expires_at < now:
        db.delete(session)
        db.commit()
        return None

    # Check inactivity timeout (8 hours default)
    idle_time = (now - session.last_used_at).total_seconds()
    if idle_time > config.SESSION_LIFETIME_MINUTES * 60:
        db.delete(session)
        db.commit()
        return None

    # Update last used
    session.last_used_at = now
    db.commit()

    return session.user_id


def get_user_from_session(
    db: DBSession, session_id: str
) -> Optional[User]:
    """
    Get User object from a valid session.
    
    Returns None if session invalid.
    """
    user_id = validate_session(db, session_id)
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


def invalidate_session(db: DBSession, session_id: str) -> bool:
    """
    Invalidate (delete) a session.
    
    Returns True if session was deleted, False if not found.
    """
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id
    ).first()

    if not session:
        return False

    db.delete(session)
    db.commit()
    return True


def mark_session_reauthed(db: DBSession, session_id: str) -> bool:
    """
    Mark a session as recently re-authenticated (for destructive action guard).
    
    Used when user re-verifies password or 2FA before doing force/stop actions.
    Returns True if marked, False if session invalid.
    """
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id
    ).first()

    if not session:
        return False

    session.last_reauth_at = datetime.now(timezone.utc)
    db.commit()
    return True


def check_reauth_window(db: DBSession, session_id: str) -> bool:
    """
    Check if a session is within the destructive-action re-auth window.
    
    Returns True if last_reauth_at is recent enough.
    """
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id
    ).first()

    if not session or not session.last_reauth_at:
        return False

    now = datetime.now(timezone.utc)
    time_since_reauth = (
        now - session.last_reauth_at
    ).total_seconds()

    return time_since_reauth <= config.DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC
