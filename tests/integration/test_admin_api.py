"""Integration tests for the admin static mount API."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def _admin_mounts_file(tmp_path: Path) -> Iterator[Path]:
    """Override the mounts file to use a temp path."""
    mounts_file = tmp_path / "static_mounts.json"
    with patch("src.utils.config.settings.admin.mounts_file", str(mounts_file)):
        yield mounts_file


@pytest.fixture()
def _static_dir(tmp_path: Path) -> Iterator[Path]:
    """Create a test static directory under an allowed base dir."""
    static_dir = tmp_path / "data" / "test_static"
    static_dir.mkdir(parents=True)
    (static_dir / "hello.txt").write_text("hello world")
    with patch(
        "src.utils.config.settings.admin.allowed_base_dirs",
        [str(tmp_path / "data")],
    ):
        yield static_dir


@pytest.fixture()
def client(
    _admin_mounts_file: Path, _static_dir: Path
) -> Iterator[TestClient]:
    """Create a test client with isolated admin config."""
    from main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


ADMIN_SECRET = "admin-secret-change-me"
HEADERS = {"X-Admin-Secret": ADMIN_SECRET}


def test_list_mounts_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/admin/static-mounts")
    assert response.status_code == 422  # missing header


def test_list_mounts_rejects_wrong_secret(client: TestClient) -> None:
    response = client.get(
        "/api/v1/admin/static-mounts",
        headers={"X-Admin-Secret": "wrong"},
    )
    assert response.status_code == 401


def test_list_mounts_empty(client: TestClient) -> None:
    response = client.get("/api/v1/admin/static-mounts", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["mounts"] == []


def test_create_mount(client: TestClient, _static_dir: Path) -> None:
    response = client.post(
        "/api/v1/admin/static-mounts",
        headers=HEADERS,
        json={
            "folder_path": str(_static_dir),
            "url_prefix": "/test-static",
        },
    )
    assert response.status_code == 201
    mount = response.json()["mount"]
    assert mount["folder_path"] == str(_static_dir)
    assert mount["url_prefix"] == "/test-static"
    assert mount["enabled"] is True
    assert mount["access_level"] == "public"


def test_create_mount_path_traversal_blocked(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/static-mounts",
        headers=HEADERS,
        json={
            "folder_path": "/etc/passwd",
            "url_prefix": "/evil",
        },
    )
    assert response.status_code == 422
    assert "MOUNT_FAILED" in json.dumps(response.json())


def test_create_mount_reserved_prefix_blocked(
    client: TestClient, _static_dir: Path
) -> None:
    response = client.post(
        "/api/v1/admin/static-mounts",
        headers=HEADERS,
        json={
            "folder_path": str(_static_dir),
            "url_prefix": "/api/data",
        },
    )
    assert response.status_code == 409
    assert "MOUNT_CONFLICT" in json.dumps(response.json())


def test_get_mount(client: TestClient, _static_dir: Path) -> None:
    create_resp = client.post(
        "/api/v1/admin/static-mounts",
        headers=HEADERS,
        json={"folder_path": str(_static_dir), "url_prefix": "/get-test"},
    )
    mount_id = create_resp.json()["mount"]["id"]
    response = client.get(f"/api/v1/admin/static-mounts/{mount_id}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["mount"]["id"] == mount_id


def test_update_mount(client: TestClient, _static_dir: Path) -> None:
    create_resp = client.post(
        "/api/v1/admin/static-mounts",
        headers=HEADERS,
        json={"folder_path": str(_static_dir), "url_prefix": "/upd-test"},
    )
    mount_id = create_resp.json()["mount"]["id"]
    response = client.patch(
        f"/api/v1/admin/static-mounts/{mount_id}",
        headers=HEADERS,
        json={"url_prefix": "/upd-test-2"},
    )
    assert response.status_code == 200
    assert response.json()["mount"]["url_prefix"] == "/upd-test-2"


def test_delete_mount(client: TestClient, _static_dir: Path) -> None:
    create_resp = client.post(
        "/api/v1/admin/static-mounts",
        headers=HEADERS,
        json={"folder_path": str(_static_dir), "url_prefix": "/del-test"},
    )
    mount_id = create_resp.json()["mount"]["id"]
    response = client.delete(f"/api/v1/admin/static-mounts/{mount_id}", headers=HEADERS)
    assert response.status_code == 204

    list_resp = client.get("/api/v1/admin/static-mounts", headers=HEADERS)
    assert len(list_resp.json()["mounts"]) == 0


def test_toggle_mount(client: TestClient, _static_dir: Path) -> None:
    create_resp = client.post(
        "/api/v1/admin/static-mounts",
        headers=HEADERS,
        json={"folder_path": str(_static_dir), "url_prefix": "/tog-test"},
    )
    mount_id = create_resp.json()["mount"]["id"]

    toggle_resp = client.post(
        f"/api/v1/admin/static-mounts/{mount_id}/toggle", headers=HEADERS
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["mount"]["enabled"] is False


def test_reload_mounts(client: TestClient) -> None:
    response = client.post("/api/v1/admin/static-mounts/reload", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "reloaded"


def test_admin_ui_accessible(client: TestClient) -> None:
    response = client.get("/api/v1/admin/static-files")
    assert response.status_code == 200
    assert "Static File Mounts" in response.text


def test_static_files_served_after_mount(
    client: TestClient, _static_dir: Path
) -> None:
    client.post(
        "/api/v1/admin/static-mounts",
        headers=HEADERS,
        json={"folder_path": str(_static_dir), "url_prefix": "/serve-test"},
    )
    response = client.get("/serve-test/hello.txt")
    assert response.status_code == 200
    assert response.text == "hello world"
