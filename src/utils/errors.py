"""Consistent error response format for the application.

All application errors inherit from AppError and carry a machine-readable
error code, a human-readable message, and optional structured context.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Machine-readable error codes for every known failure mode."""

    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"

    # Configuration
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_MISSING = "CONFIG_MISSING"

    # Data pipeline
    DATA_LOAD_FAILED = "DATA_LOAD_FAILED"
    DATA_VALIDATION_FAILED = "DATA_VALIDATION_FAILED"

    # Model
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    MODEL_INFERENCE_FAILED = "MODEL_INFERENCE_FAILED"

    # External services
    EXTERNAL_TIMEOUT = "EXTERNAL_TIMEOUT"
    EXTERNAL_UNAVAILABLE = "EXTERNAL_UNAVAILABLE"

    # Add domain-specific codes here, e.g.:
    # RAG_RETRIEVAL_FAILED = "RAG_RETRIEVAL_FAILED"
    # EMBEDDING_FAILED = "EMBEDDING_FAILED"


class AppError(Exception):
    """Base application error with structured context.

    Usage:
        raise AppError(
            code=ErrorCode.DATA_LOAD_FAILED,
            message="Failed to load dataset",
            context={"path": "/data/raw/dataset.csv"},
        )
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        context: dict[str, Any] | None = None,
        *,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}
        self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSON API responses."""
        return {
            "error": {
                "code": self.code.value,
                "message": str(self),
                "context": self.context,
            }
        }

    def __repr__(self) -> str:
        return f"AppError(code={self.code!r}, message={self!s}, context={self.context!r})"
