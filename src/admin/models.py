"""Pydantic models for static file mount configuration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class AccessLevel(StrEnum):
    """Access restriction levels for static mounts."""

    PUBLIC = "public"
    TOKEN = "token"
    ADMIN = "admin"


class StaticMount(BaseModel):
    """A configured static file mount."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    folder_path: str
    url_prefix: str
    access_level: AccessLevel = AccessLevel.PUBLIC
    access_token: str | None = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

    @model_validator(mode="after")
    def validate_token_required(self) -> StaticMount:
        if self.access_level == AccessLevel.TOKEN and not self.access_token:
            msg = "access_token is required when access_level is 'token'"
            raise ValueError(msg)
        return self


class StaticMountCreate(BaseModel):
    """Request body for creating a static mount."""

    folder_path: str
    url_prefix: str
    access_level: AccessLevel = AccessLevel.PUBLIC
    access_token: str | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def validate_token_required(self) -> StaticMountCreate:
        if self.access_level == AccessLevel.TOKEN and not self.access_token:
            msg = "access_token is required when access_level is 'token'"
            raise ValueError(msg)
        return self


class StaticMountUpdate(BaseModel):
    """Request body for updating a static mount. All fields optional."""

    folder_path: str | None = None
    url_prefix: str | None = None
    access_level: AccessLevel | None = None
    access_token: str | None = None
    enabled: bool | None = None
