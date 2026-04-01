"""Security and authentication configuration from environment."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

# Root directory for configuration
ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "01_CONFIG"


class AuthConfig:
    """
    Authentication and security configuration.
    
    All values come from environment variables or sensible defaults.
    For production internet deployment, set via reverse proxy or systemd environ.
    """

    # === Session & Cookies ===
    SESSION_LIFETIME_MINUTES: int = int(
        os.getenv("LJV_SESSION_LIFETIME_MINUTES", "480")
    )  # 8 hours
    SESSION_TIMEOUT_DELTA = timedelta(minutes=SESSION_LIFETIME_MINUTES)

    SESSION_ABSOLUTE_TIMEOUT_MINUTES: int = int(
        os.getenv("LJV_SESSION_ABSOLUTE_TIMEOUT_MINUTES", "1440")
    )  # 24 hours
    SESSION_ABSOLUTE_TIMEOUT_DELTA = timedelta(
        minutes=SESSION_ABSOLUTE_TIMEOUT_MINUTES
    )

    # Mark cookies as httpOnly, secure (HTTPS only), SameSite=Lax
    SESSION_COOKIE_SECURE: bool = os.getenv("LJV_SESSION_COOKIE_SECURE", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"

    # === Destructive Action Step-Up ===
    # If non-zero, destructive actions (force, stop) require re-auth within this window (seconds)
    DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC: int = int(
        os.getenv("LJV_DESTRUCTIVE_ACTION_REAUTH_WINDOW_SEC", "300")
    )  # 5 min

    # === OAuth (Google) ===
    GOOGLE_OAUTH_ENABLED: bool = os.getenv("LJV_GOOGLE_OAUTH_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    GOOGLE_CLIENT_ID: str = os.getenv("LJV_GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("LJV_GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "LJV_GOOGLE_REDIRECT_URI", "http://127.0.0.1:8787/auth/google/callback"
    )

    # === Developer Email (for email/password signup mode) ===
    # In single-admin mode, only this email can create an account
    DEVELOPER_EMAIL: str = os.getenv("LJV_DEVELOPER_EMAIL", "")

    # === CORS & Origin Restrictions ===
    # Comma-separated list of allowed origins (for reverse proxy scenarios)
    ALLOWED_ORIGINS_STR: str = os.getenv(
        "LJV_ALLOWED_ORIGINS", "http://127.0.0.1:8787,http://localhost:8787"
    )
    ALLOWED_ORIGINS: list[str] = [
        o.strip() for o in ALLOWED_ORIGINS_STR.split(",") if o.strip()
    ]

    # === Database ===
    # Path to SQLite database (defaults to 03_WORK/auth.db)
    DB_PATH: Path = Path(
        os.getenv("LJV_AUTH_DB_PATH", str(ROOT / "03_WORK" / "auth.db"))
    )

    # === Secrets ===
    # Used for session signing and CSRF tokens
    SECRET_KEY: str = os.getenv("LJV_SECRET_KEY", "dev-secret-change-in-production")

    # === Rate Limiting ===
    # Maximum auth attempts per IP in a time window
    AUTH_RATE_LIMIT_ATTEMPTS: int = int(
        os.getenv("LJV_AUTH_RATE_LIMIT_ATTEMPTS", "5")
    )
    AUTH_RATE_LIMIT_WINDOW_SEC: int = int(
        os.getenv("LJV_AUTH_RATE_LIMIT_WINDOW_SEC", "300")
    )  # 5 min

    # === Developer Mode ===
    # If True, session cookies are not marked Secure and CORS is relaxed
    DEBUG: bool = os.getenv("LJV_DEBUG", "false").lower() in ("true", "1", "yes")

    def validate(self) -> list[str]:
        """
        Validate critical config values.
        
        Returns list of error messages if any.
        """
        errors = []

        if not self.SECRET_KEY or self.SECRET_KEY == "dev-secret-change-in-production":
            errors.append(
                "LJV_SECRET_KEY not set. Set a strong random value for production."
            )

        if self.GOOGLE_OAUTH_ENABLED:
            if not self.GOOGLE_CLIENT_ID:
                errors.append("Google OAuth enabled but LJV_GOOGLE_CLIENT_ID not set.")
            if not self.GOOGLE_CLIENT_SECRET:
                errors.append(
                    "Google OAuth enabled but LJV_GOOGLE_CLIENT_SECRET not set."
                )

        if not self.ALLOWED_ORIGINS:
            errors.append("LJV_ALLOWED_ORIGINS is empty.")

        if not self.DEBUG and not self.SESSION_COOKIE_SECURE:
            errors.append(
                "Production mode (DEBUG=false) requires SESSION_COOKIE_SECURE=true. "
                "Set behind reverse proxy with TLS termination."
            )

        return errors


# Global config instance
config = AuthConfig()
