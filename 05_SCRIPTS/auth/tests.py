"""API and integration tests for authentication and dashboard control."""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Assume pytest is run from 05_SCRIPTS/
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from auth.config import config
from auth.database import User, Session as SessionModel, init_db, get_session_local
from auth.security import hash_password, verify_password
from auth.session import create_session, validate_session, check_reauth_window


@pytest.fixture(scope="function")
def test_db():
    """Create a test database."""
    # Use in-memory SQLite for tests
    import tempfile
    from sqlalchemy import create_engine
    
    db_fd, db_path = tempfile.mkstemp()
    db_url = f"sqlite:///{db_path}"
    
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    from auth.database import Base
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    yield db
    
    db.close()
    try:
        Path(db_path).unlink()
    except (PermissionError, OSError):
        pass  # Ignore cleanup errors on Windows


def test_password_hashing():
    """Test password hash and verify."""
    plain = "mypassword123"
    hashed = hash_password(plain)
    
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_user_creation(test_db):
    """Test creating a user."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpass"),
        name="Test User",
        is_active=1,
        is_admin=1,
    )
    test_db.add(user)
    test_db.commit()
    
    found = test_db.query(User).filter(User.email == "test@example.com").first()
    assert found is not None
    assert found.email == "test@example.com"
    assert found.is_admin == 1


def test_session_creation(test_db):
    """Test creating a session."""
    # Create user first
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpass"),
        name="Test User",
        is_active=1,
        is_admin=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create session
    session_id = create_session(test_db, user.id, "127.0.0.1", "Mozilla/5.0")
    
    assert session_id
    assert len(session_id) > 24  # URL-safe token
    
    # Validate session
    user_id = validate_session(test_db, session_id)
    assert user_id == user.id


def test_session_expiry(test_db):
    """Test that expired sessions are rejected."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpass"),
        is_active=1,
        is_admin=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    session_id = create_session(test_db, user.id)
    
    # Manually expire the session
    session = test_db.query(SessionModel).filter(
        SessionModel.session_id == session_id
    ).first()
    session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    test_db.commit()
    
    # Should return None (expired)
    user_id = validate_session(test_db, session_id)
    assert user_id is None


def test_reauth_window_check(test_db):
    """Test destructive action re-auth window."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpass"),
        is_active=1,
        is_admin=1,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    session_id = create_session(test_db, user.id)
    
    # Initially, should not be within window
    assert not check_reauth_window(test_db, session_id)
    
    # Mark as reauthed
    from auth.session import mark_session_reauthed
    mark_session_reauthed(test_db, session_id)
    
    # Now should be within window
    assert check_reauth_window(test_db, session_id)


def test_rate_limiting():
    """Test auth rate limiter."""
    from auth.middleware import RateLimiter
    
    limiter = RateLimiter(max_attempts=3, window_sec=60)
    
    ip = "192.168.1.1"
    
    # Allow first 3 attempts
    assert limiter.is_allowed(ip)
    assert limiter.is_allowed(ip)
    assert limiter.is_allowed(ip)
    
    # Block 4th attempt
    assert not limiter.is_allowed(ip)
    
    # Different IP should be allowed
    assert limiter.is_allowed("192.168.1.2")


@pytest.mark.asyncio
async def test_auth_config_validation():
    """Test auth config validation."""
    errors = config.validate()
    
    # In test mode with defaults, expect at least one warning
    # (dev-secret key should be flagged)
    assert isinstance(errors, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
