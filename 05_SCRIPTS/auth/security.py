"""Security utilities: password hashing, session tokens, CSRF."""

from __future__ import annotations

import hashlib
import secrets
from passlib.context import CryptContext

# Password hashing context (uses bcrypt by default)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_session_token(length: int = 32) -> str:
    """Generate a cryptographically secure random session token."""
    return secrets.token_urlsafe(length)


def generate_state_token(length: int = 32) -> str:
    """Generate a CSRF/OAuth state token."""
    return secrets.token_urlsafe(length)


def generate_password_reset_token(length: int = 32) -> str:
    """Generate a short-lived password reset token."""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token for storage (one-way)."""
    return hashlib.sha256(token.encode()).hexdigest()
