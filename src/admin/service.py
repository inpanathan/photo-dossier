"""Business logic for static file mount management."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from src.admin.models import AccessLevel, StaticMountCreate, StaticMountUpdate
from src.admin.repository import StaticMountRepository
from src.utils.config import PROJECT_ROOT, settings
from src.utils.errors import AppError, ErrorCode
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.admin.models import StaticMount

logger = get_logger(__name__)

# Tag used to identify dynamically-added static mount routes
_MOUNT_ROUTE_ATTR = "_static_mount_id"

# Reserved prefixes that cannot be used for static mounts
_RESERVED_PREFIXES = {"/api", "/health", "/docs", "/redoc", "/openapi.json", "/admin"}


class AuthMiddleware:
    """ASGI middleware that checks auth before serving static files."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        access_level: AccessLevel,
        access_token: str | None = None,
        admin_secret: str = "",
    ) -> None:
        self.app = app
        self.access_level = access_level
        self.access_token = access_token
        self.admin_secret = admin_secret

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        if self.access_level == AccessLevel.TOKEN:
            token = self._extract_token(request)
            if token != self.access_token:
                response = JSONResponse(
                    {"error": {"code": "UNAUTHORIZED", "message": "Invalid or missing token"}},
                    status_code=401,
                )
                await response(scope, receive, send)
                return

        elif self.access_level == AccessLevel.ADMIN:
            secret = request.headers.get("x-admin-secret", "")
            if secret != self.admin_secret:
                response = JSONResponse(
                    {"error": {"code": "UNAUTHORIZED", "message": "Admin access required"}},
                    status_code=401,
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)

    @staticmethod
    def _extract_token(request: Request) -> str:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return request.query_params.get("token", "")


class StaticMountService:
    """Manages static file mounts on the FastAPI app."""

    def __init__(self, repository: StaticMountRepository) -> None:
        self._repo = repository
        self._app: ASGIApp | None = None

    def bind_app(self, app: ASGIApp) -> None:
        self._app = app

    @property
    def repo(self) -> StaticMountRepository:
        return self._repo

    def list_mounts(self) -> list[StaticMount]:
        return self._repo.list_all()

    def get_mount(self, mount_id: str) -> StaticMount:
        return self._repo.get(mount_id)

    def create_mount(self, data: StaticMountCreate) -> StaticMount:
        self._validate_folder(data.folder_path)
        self._validate_prefix(data.url_prefix)
        mount = self._repo.add(data)
        self._apply_all_mounts()
        return mount

    def update_mount(self, mount_id: str, data: StaticMountUpdate) -> StaticMount:
        if data.folder_path is not None:
            self._validate_folder(data.folder_path)
        if data.url_prefix is not None:
            self._validate_prefix(data.url_prefix)
        mount = self._repo.update(mount_id, data)
        self._apply_all_mounts()
        return mount

    def delete_mount(self, mount_id: str) -> None:
        self._repo.delete(mount_id)
        self._apply_all_mounts()

    def toggle_mount(self, mount_id: str) -> StaticMount:
        mount = self._repo.toggle(mount_id)
        self._apply_all_mounts()
        return mount

    def apply_all_mounts(self) -> None:
        self._apply_all_mounts()

    def _apply_all_mounts(self) -> None:
        """Remove old static mounts and re-add all enabled ones."""
        from fastapi import FastAPI

        if not isinstance(self._app, FastAPI):
            return

        app: FastAPI = self._app

        # Remove previously-added static mount routes
        app.routes[:] = [r for r in app.routes if not getattr(r, _MOUNT_ROUTE_ATTR, False)]

        for mount in self._repo.list_all():
            if not mount.enabled:
                continue

            folder = self._resolve_folder(mount.folder_path)
            if not folder.is_dir():
                logger.warning(
                    "static_mount_skip_missing_dir",
                    mount_id=mount.id,
                    folder=str(folder),
                )
                continue

            static_app: ASGIApp = StaticFiles(directory=str(folder), html=True)

            if mount.access_level != AccessLevel.PUBLIC:
                static_app = AuthMiddleware(
                    static_app,
                    access_level=mount.access_level,
                    access_token=mount.access_token,
                    admin_secret=settings.admin.secret_key,
                )

            prefix = mount.url_prefix.rstrip("/")
            from starlette.routing import Mount

            route = Mount(prefix, app=static_app, name=f"static_{mount.id}")
            setattr(route, _MOUNT_ROUTE_ATTR, True)
            app.routes.append(route)

            logger.info(
                "static_mount_applied",
                mount_id=mount.id,
                prefix=prefix,
                folder=str(folder),
                access_level=mount.access_level,
            )

    def _validate_folder(self, folder_path: str) -> None:
        resolved = self._resolve_folder(folder_path)
        allowed = [PROJECT_ROOT / d for d in settings.admin.allowed_base_dirs]
        if not any(self._is_subpath(resolved, base) for base in allowed):
            raise AppError(
                code=ErrorCode.MOUNT_FAILED,
                message=f"Folder must be under one of: {settings.admin.allowed_base_dirs}",
                context={"folder_path": folder_path},
            )

    @staticmethod
    def _validate_prefix(url_prefix: str) -> None:
        normalized = url_prefix.rstrip("/")
        if not normalized.startswith("/"):
            raise AppError(
                code=ErrorCode.MOUNT_FAILED,
                message="URL prefix must start with '/'",
                context={"url_prefix": url_prefix},
            )
        for reserved in _RESERVED_PREFIXES:
            if normalized == reserved or normalized.startswith(reserved + "/"):
                raise AppError(
                    code=ErrorCode.MOUNT_CONFLICT,
                    message=f"URL prefix '{url_prefix}' conflicts with reserved path '{reserved}'",
                    context={"url_prefix": url_prefix, "reserved": reserved},
                )

    @staticmethod
    def _resolve_folder(folder_path: str) -> Path:
        p = Path(folder_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p.resolve()

    @staticmethod
    def _is_subpath(path: Path, base: Path) -> bool:
        try:
            path.relative_to(base.resolve())
            return True
        except ValueError:
            return False
