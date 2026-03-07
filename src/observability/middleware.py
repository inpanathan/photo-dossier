"""Request correlation ID middleware and observability helpers.

Adds a unique request_id to every incoming request and binds it to
structlog context so all log entries within a request are correlated.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every request and log request metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Use client-provided ID or generate one
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
        request.state.request_id = request_id

        # Bind to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000

        # Add request_id to response headers
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        structlog.contextvars.clear_contextvars()
        return response
