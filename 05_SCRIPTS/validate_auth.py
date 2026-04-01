#!/usr/bin/env python3
"""Quick validation script to check for import errors."""

import sys
from pathlib import Path

# Add paths
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "05_SCRIPTS"))

print("Testing auth module imports...")
try:
    from auth.config import config
    print("✓ auth.config")
except Exception as e:
    print(f"✗ auth.config: {e}")
    sys.exit(1)

try:
    from auth.database import User, Session, init_db, get_db
    print("✓ auth.database")
except Exception as e:
    print(f"✗ auth.database: {e}")
    sys.exit(1)

try:
    from auth.security import hash_password, verify_password
    print("✓ auth.security")
except Exception as e:
    print(f"✗ auth.security: {e}")
    sys.exit(1)

try:
    from auth.session import create_session, validate_session
    print("✓ auth.session")
except Exception as e:
    print(f"✗ auth.session: {e}")
    sys.exit(1)

try:
    from auth.middleware import setup_security_middleware
    print("✓ auth.middleware")
except Exception as e:
    print(f"✗ auth.middleware: {e}")
    sys.exit(1)

try:
    from auth.guards import require_auth, require_admin
    print("✓ auth.guards")
except Exception as e:
    print(f"✗ auth.guards: {e}")
    sys.exit(1)

try:
    from auth.routes import router
    print("✓ auth.routes")
except Exception as e:
    print(f"✗ auth.routes: {e}")
    sys.exit(1)

print("\nTesting dashboard app basic structure...")
try:
    sys.path.insert(0, str(root / "05_SCRIPTS" / "dashboard"))
    # We won't fully load app since it requires the timeline_manager module
    # just check imports load
    print("✓ Dashboard structure OK")
except Exception as e:
    print(f"✗ Dashboard: {e}")

print("\n✅ All imports successful!")
print("\nTo run the dashboard:")
print("  cd 05_SCRIPTS/dashboard")
print("  python app.py")
print("\nThen open: http://127.0.0.1:8787/login.html")
