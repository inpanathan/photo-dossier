"""Unit tests for static mount repository."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.admin.models import AccessLevel, StaticMountCreate, StaticMountUpdate
from src.admin.repository import StaticMountRepository
from src.utils.errors import AppError


@pytest.fixture()
def mounts_file(tmp_path: Path) -> Path:
    return tmp_path / "static_mounts.json"


@pytest.fixture()
def repo(mounts_file: Path) -> StaticMountRepository:
    return StaticMountRepository(mounts_file)


def test_empty_repo_returns_no_mounts(repo: StaticMountRepository) -> None:
    assert repo.list_all() == []


def test_add_and_list(repo: StaticMountRepository) -> None:
    create = StaticMountCreate(folder_path="data/uploads", url_prefix="/files")
    mount = repo.add(create)
    assert mount.folder_path == "data/uploads"
    assert mount.url_prefix == "/files"
    assert mount.access_level == AccessLevel.PUBLIC
    assert mount.enabled is True
    assert len(repo.list_all()) == 1


def test_add_persists_to_file(mounts_file: Path, repo: StaticMountRepository) -> None:
    repo.add(StaticMountCreate(folder_path="data/raw", url_prefix="/raw"))
    assert mounts_file.exists()
    data = json.loads(mounts_file.read_text())
    assert len(data) == 1
    assert data[0]["url_prefix"] == "/raw"


def test_get_existing_mount(repo: StaticMountRepository) -> None:
    mount = repo.add(StaticMountCreate(folder_path="data/x", url_prefix="/x"))
    found = repo.get(mount.id)
    assert found.id == mount.id


def test_get_nonexistent_raises(repo: StaticMountRepository) -> None:
    with pytest.raises(AppError) as exc_info:
        repo.get("nonexistent")
    assert exc_info.value.code == "MOUNT_NOT_FOUND"


def test_update_mount(repo: StaticMountRepository) -> None:
    mount = repo.add(StaticMountCreate(folder_path="data/a", url_prefix="/a"))
    updated = repo.update(mount.id, StaticMountUpdate(folder_path="data/b"))
    assert updated.folder_path == "data/b"
    assert updated.url_prefix == "/a"


def test_delete_mount(repo: StaticMountRepository) -> None:
    mount = repo.add(StaticMountCreate(folder_path="data/d", url_prefix="/d"))
    repo.delete(mount.id)
    assert len(repo.list_all()) == 0


def test_toggle_mount(repo: StaticMountRepository) -> None:
    mount = repo.add(StaticMountCreate(folder_path="data/t", url_prefix="/t"))
    assert mount.enabled is True
    toggled = repo.toggle(mount.id)
    assert toggled.enabled is False
    toggled2 = repo.toggle(mount.id)
    assert toggled2.enabled is True


def test_duplicate_prefix_raises(repo: StaticMountRepository) -> None:
    repo.add(StaticMountCreate(folder_path="data/a", url_prefix="/dup"))
    with pytest.raises(AppError) as exc_info:
        repo.add(StaticMountCreate(folder_path="data/b", url_prefix="/dup"))
    assert exc_info.value.code == "MOUNT_CONFLICT"


def test_loads_from_existing_file(mounts_file: Path) -> None:
    data = [
        {
            "id": "abc123",
            "folder_path": "data/uploads",
            "url_prefix": "/uploads",
            "access_level": "public",
            "access_token": None,
            "enabled": True,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    ]
    mounts_file.parent.mkdir(parents=True, exist_ok=True)
    mounts_file.write_text(json.dumps(data))
    repo = StaticMountRepository(mounts_file)
    assert len(repo.list_all()) == 1
    assert repo.list_all()[0].id == "abc123"


def test_loads_gracefully_from_corrupt_file(mounts_file: Path) -> None:
    mounts_file.parent.mkdir(parents=True, exist_ok=True)
    mounts_file.write_text("not valid json{{{")
    repo = StaticMountRepository(mounts_file)
    assert repo.list_all() == []
