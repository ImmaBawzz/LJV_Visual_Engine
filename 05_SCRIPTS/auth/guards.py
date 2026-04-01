"""Authorization guards for engine control endpoints."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from .config import config
from .database import get_db
from .session import get_user_from_session, check_reauth_window

logger = logging.getLogger(__name__)


def _get_session_id_from_request(request: Request) -> Optional[str]:
    """Extract session_id from cookie or Authorization header."""
    session_id = request.cookies.get("ljv_session")
    if session_id:
        return session_id

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


async def require_auth(
    request: Request, db: DBSession = Depends(get_db)
):
    """
    Dependency: verify user is authenticated.
    
    Raises 401 if not authenticated.
    Returns (user, session_id) on success.
    """
    session_id = _get_session_id_from_request(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_user_from_session(db, session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return (user, session_id)


async def require_admin(
    request: Request, db: DBSession = Depends(get_db)
):
    """
    Dependency: require admin user.
    
    Raises 401/403 if not authenticated or not admin.
    Returns (user, session_id) on success.
    """
    session_id = _get_session_id_from_request(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_user_from_session(db, session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    if not user.is_admin:
        # Log unauthorized access attempt
        logger.warning(
            f"Unauthorized admin access attempt by user {user.email} (id={user.id})"
        )
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return (user, session_id)


async def require_destructive_action_stepup(
    request: Request, db: DBSession = Depends(get_db)
):
    """
    Dependency: require auth + recent re-auth for destructive actions.
    
    If DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC is 0, skip re-auth check.
    Otherwise, user must have re-authed within the window.
    
    Raises 401/403/428 if denied.
    Returns (user, session_id) on success.
    """
    session_id = _get_session_id_from_request(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_user_from_session(db, session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    if not user.is_admin:
        logger.warning(
            f"Unauthorized destructive action by user {user.email} (id={user.id})"
        )
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Check re-auth window if configured
    if config.DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC > 0:
        if not check_reauth_window(db, session_id):
            logger.warning(
                f"Destructive action blocked: re-auth required for user {user.email}"
            )
            raise HTTPException(
                status_code=428,
                detail=f"Re-authentication required within {config.DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC} seconds",
            )

    return (user, session_id)


def log_control_action(
    action: str, user_email: str, user_id: int, ip: str, success: bool = True
) -> None:
    """
    Log a control action for audit trail.
    
    In production, write to structured log with identity context.
    """
    status = "success" if success else "blocked"
    logger.info(
        f"CONTROL_ACTION [{action}] user={user_email} (id={user_id}) from {ip} [{status}]"
    )
