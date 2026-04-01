"""Database models and session storage for authentication."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .config import config

Base = declarative_base()


class User(Base):
    """User account record."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # NULL if OAuth-only
    provider = Column(
        String(50), default="local"
    )  # 'local', 'google', or comma-separated for linked
    provider_id = Column(String(255), nullable=True, unique=True)  # Google subject
    name = Column(String(255), nullable=True)
    profile_picture_url = Column(String(512), nullable=True)
    reset_token_hash = Column(String(64), nullable=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Integer, default=1)  # Boolean-like (0 or 1)
    is_admin = Column(Integer, default=0)  # Boolean-like (0 or 1)

    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<User {self.email} id={self.id}>"


class Session(Base):
    """Server-side session storage for cookie-based sessions."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Serialized session data (IP, user agent, etc.)
    data = Column(Text, default="{}")

    # For destructive action step-up: timestamp of last re-auth
    last_reauth_at = Column(DateTime(timezone=True), nullable=True)

    # Expiry tracking
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_used_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<Session {self.session_id[:8]}... user_id={self.user_id}>"

    def get_data(self) -> dict:
        """Deserialize session data."""
        try:
            return json.loads(self.data) if self.data else {}
        except Exception:
            return {}

    def set_data(self, data: dict) -> None:
        """Serialize and store session data."""
        self.data = json.dumps(data)


# Database setup
def init_db() -> None:
    """Create all tables if they don't exist."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _ensure_user_table_columns(engine)


def _ensure_user_table_columns(engine) -> None:
    """Backfill schema columns for existing SQLite auth databases."""
    with engine.connect() as conn:
        table_info = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        existing_columns = {row[1] for row in table_info}

        if "reset_token_hash" not in existing_columns:
            conn.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN reset_token_hash VARCHAR(64)"
            )

        if "reset_token_expires_at" not in existing_columns:
            conn.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN reset_token_expires_at DATETIME"
            )

        conn.commit()


def get_engine():
    """Get or create SQLAlchemy engine."""
    db_url = f"sqlite:///{config.DB_PATH}"
    return create_engine(db_url, connect_args={"check_same_thread": False})


def get_session_local():
    """Get sessionmaker for dependency injection."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency function for FastAPI
def get_db():
    """FastAPI dependency to get a DB session."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
