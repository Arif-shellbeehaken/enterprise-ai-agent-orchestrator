"""
Production middleware: request ID, security headers, simple rate limiting.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from typing import Callable, Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-ID for distributed tracing / log correlation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline security headers for API responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory sliding-window rate limiter (per client IP).
    Suitable for single-instance deployments; use Redis for multi-replica.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        burst: int = 30,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip health probes
        if request.url.path in ("/health", "/ready", "/"):
            return await call_next(request)

        key = self._client_key(request)
        now = time.monotonic()
        window = 60.0
        q = self._hits[key]

        # Drop timestamps outside window
        while q and now - q[0] > window:
            q.popleft()

        if len(q) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Try again later.",
                        "details": {"retry_after_seconds": 60},
                    }
                },
                headers={"Retry-After": "60"},
            )

        q.append(now)
        return await call_next(request)
