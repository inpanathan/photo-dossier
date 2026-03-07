"""Admin console routes for managing static file mounts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import HTMLResponse

from src.admin.models import StaticMountCreate, StaticMountUpdate
from src.utils.config import settings
from src.utils.errors import AppError, ErrorCode
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.admin.service import StaticMountService

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_service: StaticMountService | None = None

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "static_files.html"


def set_service(service: StaticMountService) -> None:
    """Inject the service instance (called during app startup)."""
    global _service  # noqa: PLW0603
    _service = service


def _get_service() -> StaticMountService:
    if _service is None:
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Admin service not initialized",
        )
    return _service


def _require_admin(x_admin_secret: str = Header()) -> None:
    if x_admin_secret != settings.admin.secret_key:
        raise AppError(
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid admin secret",
        )


# ---- Admin UI ----


@router.get("/static-files", response_class=HTMLResponse)
async def admin_ui(request: Request) -> HTMLResponse:  # noqa: ARG001
    html = _TEMPLATE_PATH.read_text()
    return HTMLResponse(content=html)


# ---- CRUD API ----


@router.get("/static-mounts", dependencies=[Depends(_require_admin)])
async def list_mounts() -> dict:
    service = _get_service()
    mounts = service.list_mounts()
    return {"mounts": [m.model_dump(mode="json") for m in mounts]}


@router.post("/static-mounts", status_code=201, dependencies=[Depends(_require_admin)])
async def create_mount(data: StaticMountCreate) -> dict:
    service = _get_service()
    mount = service.create_mount(data)
    return {"mount": mount.model_dump(mode="json")}


@router.get("/static-mounts/{mount_id}", dependencies=[Depends(_require_admin)])
async def get_mount(mount_id: str) -> dict:
    service = _get_service()
    mount = service.get_mount(mount_id)
    return {"mount": mount.model_dump(mode="json")}


@router.patch("/static-mounts/{mount_id}", dependencies=[Depends(_require_admin)])
async def update_mount(mount_id: str, data: StaticMountUpdate) -> dict:
    service = _get_service()
    mount = service.update_mount(mount_id, data)
    return {"mount": mount.model_dump(mode="json")}


@router.delete("/static-mounts/{mount_id}", status_code=204, dependencies=[Depends(_require_admin)])
async def delete_mount(mount_id: str) -> None:
    service = _get_service()
    service.delete_mount(mount_id)


@router.post(
    "/static-mounts/{mount_id}/toggle", dependencies=[Depends(_require_admin)]
)
async def toggle_mount(mount_id: str) -> dict:
    service = _get_service()
    mount = service.toggle_mount(mount_id)
    return {"mount": mount.model_dump(mode="json")}


@router.post("/static-mounts/reload", dependencies=[Depends(_require_admin)])
async def reload_mounts() -> dict:
    service = _get_service()
    service.apply_all_mounts()
    mounts = service.list_mounts()
    enabled_count = sum(1 for m in mounts if m.enabled)
    return {"status": "reloaded", "total": len(mounts), "enabled": enabled_count}
