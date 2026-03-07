"""JWT authentication for API access.

Stateless token-based auth suitable for both web and mobile clients.
Tokens are signed with the app's SECRET_KEY using HS256.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any

from src.utils.config import settings
from src.utils.errors import AppError, ErrorCode


def create_token(payload: dict[str, Any], expires_in: int = 86400) -> str:
    """Create a signed JWT-like token.

    Uses HMAC-SHA256 for signing. Not a full JWT implementation
    but sufficient for internal API auth without external deps.

    Args:
        payload: Claims to encode (e.g., user_id, role).
        expires_in: Token lifetime in seconds (default: 24h).

    Returns:
        Signed token string.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        **payload,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }

    h = _b64encode(json.dumps(header))
    p = _b64encode(json.dumps(payload))
    signature = _sign(f"{h}.{p}")

    return f"{h}.{p}.{signature}"


def verify_token(token: str) -> dict[str, Any]:
    """Verify and decode a token.

    Args:
        token: The signed token string.

    Returns:
        Decoded payload dict.

    Raises:
        AppError: If token is invalid, expired, or tampered with.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise AppError(code=ErrorCode.UNAUTHORIZED, message="Invalid token format")

    header_b64, payload_b64, signature = parts

    # Verify signature
    expected = _sign(f"{header_b64}.{payload_b64}")
    if not hmac.compare_digest(signature, expected):
        raise AppError(code=ErrorCode.UNAUTHORIZED, message="Invalid token signature")

    # Decode payload
    try:
        payload: dict[str, Any] = json.loads(_b64decode(payload_b64))
    except (json.JSONDecodeError, ValueError) as e:
        raise AppError(code=ErrorCode.UNAUTHORIZED, message="Invalid token payload") from e

    # Check expiration
    if payload.get("exp", 0) < time.time():
        raise AppError(code=ErrorCode.UNAUTHORIZED, message="Token expired")

    return payload


def _sign(data: str) -> str:
    """Create HMAC-SHA256 signature."""
    key = settings.secret_key.encode()
    sig = hmac.new(key, data.encode(), hashlib.sha256).digest()
    return urlsafe_b64encode(sig).rstrip(b"=").decode()


def _b64encode(data: str) -> str:
    return urlsafe_b64encode(data.encode()).rstrip(b"=").decode()


def _b64decode(data: str) -> str:
    # Add padding
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return urlsafe_b64decode(data.encode()).decode()
