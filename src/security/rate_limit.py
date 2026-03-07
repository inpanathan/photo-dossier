"""In-memory rate limiter middleware.

Limits requests per IP address using a sliding window counter.
Returns 429 Too Many Requests with Retry-After header when exceeded.
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.utils.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter per client IP."""

    def __init__(self, app, max_requests: int = 0, window_seconds: int = 60) -> None:
        super().__init__(app)
        self._max_requests = max_requests or settings.security.rate_limit_rpm
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._max_requests <= 0:
            return await call_next(request)

        # Skip rate limiting for health/ready checks
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - self._window

        # Prune old entries
        timestamps = self._requests[client_ip]
        self._requests[client_ip] = [t for t in timestamps if t > cutoff]

        if len(self._requests[client_ip]) >= self._max_requests:
            retry_after = int(self._window - (now - self._requests[client_ip][0]))
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": f"Rate limit exceeded. "
                        f"Max {self._max_requests} requests per {self._window}s.",
                        "context": {},
                    }
                },
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)
