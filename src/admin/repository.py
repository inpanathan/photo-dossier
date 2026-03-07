"""JSON file persistence for static mount configuration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.admin.models import StaticMount, StaticMountCreate, StaticMountUpdate
from src.utils.errors import AppError, ErrorCode
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StaticMountRepository:
    """Read/write static mount configs to a JSON file."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._mounts: list[StaticMount] = []
        self._load()

    def _load(self) -> None:
        if not self._file_path.exists():
            self._mounts = []
            return
        try:
            raw = json.loads(self._file_path.read_text())
            self._mounts = [StaticMount.model_validate(m) for m in raw]
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("static_mounts_load_failed", error=str(e))
            self._mounts = []

    def _save(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        data = [m.model_dump(mode="json") for m in self._mounts]
        self._file_path.write_text(json.dumps(data, indent=2, default=str))

    def list_all(self) -> list[StaticMount]:
        return list(self._mounts)

    def get(self, mount_id: str) -> StaticMount:
        for m in self._mounts:
            if m.id == mount_id:
                return m
        raise AppError(
            code=ErrorCode.MOUNT_NOT_FOUND,
            message=f"Static mount '{mount_id}' not found",
            context={"mount_id": mount_id},
        )

    def add(self, create: StaticMountCreate) -> StaticMount:
        self._check_prefix_conflict(create.url_prefix)
        mount = StaticMount(
            folder_path=create.folder_path,
            url_prefix=create.url_prefix,
            access_level=create.access_level,
            access_token=create.access_token,
            enabled=create.enabled,
        )
        self._mounts.append(mount)
        self._save()
        logger.info("static_mount_created", mount_id=mount.id, prefix=mount.url_prefix)
        return mount

    def update(self, mount_id: str, data: StaticMountUpdate) -> StaticMount:
        mount = self.get(mount_id)
        updates = data.model_dump(exclude_none=True)
        if "url_prefix" in updates and updates["url_prefix"] != mount.url_prefix:
            self._check_prefix_conflict(updates["url_prefix"], exclude_id=mount_id)
        for key, value in updates.items():
            setattr(mount, key, value)
        mount.updated_at = datetime.now(tz=UTC)
        self._save()
        logger.info("static_mount_updated", mount_id=mount_id)
        return mount

    def delete(self, mount_id: str) -> None:
        mount = self.get(mount_id)
        self._mounts.remove(mount)
        self._save()
        logger.info("static_mount_deleted", mount_id=mount_id)

    def toggle(self, mount_id: str) -> StaticMount:
        mount = self.get(mount_id)
        mount.enabled = not mount.enabled
        mount.updated_at = datetime.now(tz=UTC)
        self._save()
        logger.info("static_mount_toggled", mount_id=mount_id, enabled=mount.enabled)
        return mount

    def _check_prefix_conflict(self, prefix: str, *, exclude_id: str | None = None) -> None:
        normalized = prefix.rstrip("/")
        for m in self._mounts:
            if m.id == exclude_id:
                continue
            if m.url_prefix.rstrip("/") == normalized:
                raise AppError(
                    code=ErrorCode.MOUNT_CONFLICT,
                    message=f"URL prefix '{prefix}' is already in use",
                    context={"existing_mount_id": m.id, "url_prefix": prefix},
                )
