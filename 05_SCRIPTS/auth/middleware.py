"""FastAPI middleware for security headers, request logging, and rate limiting."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter by IP address."""

    def __init__(self, max_attempts: int, window_sec: int):
        self.max_attempts = max_attempts
        self.window_sec = window_sec
        # {ip: [(timestamp, count), ...]}
        self.attempts: dict[str, list[tuple[float, int]]] = defaultdict(list)

    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed; return True if within limit."""
        now = time.time()
        cutoff = now - self.window_sec

        # Prune old entries
        if ip in self.attempts:
            self.attempts[ip] = [
                (ts, cnt) for ts, cnt in self.attempts[ip] if ts > cutoff
            ]

        # Count current window
        current_count = sum(cnt for ts, cnt in self.attempts[ip])

        if current_count >= self.max_attempts:
            return False

        # Record this attempt
        if ip not in self.attempts:
            self.attempts[ip] = []
        self.attempts[ip].append((now, 1))

        return True


# Global rate limiters
auth_rate_limiter = RateLimiter(
    config.AUTH_RATE_LIMIT_ATTEMPTS, config.AUTH_RATE_LIMIT_WINDOW_SEC
)


def setup_security_middleware(app: FastAPI) -> None:
    """Attach security middleware to FastAPI app."""

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next: Callable):
        """Add security headers to all responses."""
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection (browser-level)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next: Callable):
        """Log requests with context for debugging."""
        start_time = time.time()
        request_id = request.headers.get("x-request-id", "no-id")
        client_ip = request.client.host if request.client else "unknown"

        logger.debug(
            f"[{request_id}] → {request.method} {request.url.path} from {client_ip}"
        )

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        logger.debug(
            f"[{request_id}] ← {response.status_code} in {duration_ms:.1f}ms"
        )

        # Attach request ID to response for tracing
        response.headers["X-Request-ID"] = request_id

        return response


def setup_auth_rate_limiting(app: FastAPI) -> None:
    """
    Attach rate limiting to auth endpoints.
    
    Call this after all auth routes are registered.
    Usage: add rate_limit_guard dependency to auth endpoint handlers.
    """

    async def rate_limit_guard(request: Request):
        """Check rate limit by IP; raise 429 if exceeded."""
        client_ip = request.client.host if request.client else "127.0.0.1"

        if not auth_rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                {"detail": "Too many auth attempts. Try again later."},
                status_code=429,
            )

        return True

    # Store on app for use by route handlers
    app.state.rate_limit_guard = rate_limit_guard
