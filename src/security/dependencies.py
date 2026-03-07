"""FastAPI security dependencies for JWT authentication."""

from __future__ import annotations

from fastapi import Header

from src.security.auth import verify_token
from src.utils.config import settings
from src.utils.errors import AppError, ErrorCode


async def require_auth(authorization: str = Header("")) -> dict:
    """FastAPI dependency that validates the JWT bearer token.

    Returns the decoded payload if auth is required and valid.
    When auth is disabled via config, returns a guest payload.
    """
    if not settings.security.require_auth:
        return {"user_id": "anonymous", "role": "guest"}

    if not authorization.startswith("Bearer "):
        raise AppError(
            code=ErrorCode.UNAUTHORIZED,
            message="Missing or invalid Authorization header. Use: Bearer <token>",
        )

    token = authorization[7:]  # Strip "Bearer "
    return verify_token(token)
