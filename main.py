"""Application entry point.

Starts the FastAPI server with structured logging and validated configuration.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import uvicorn
from fastapi import Request

from src.utils.config import settings
from src.utils.logger import get_logger, setup_logging

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """App startup/shutdown lifecycle."""
    logger.info("app_startup", env=settings.app_env)

    # Initialize admin static mount service
    from pathlib import Path

    from src.admin.repository import StaticMountRepository
    from src.admin.routes import set_service
    from src.admin.service import StaticMountService

    mounts_file = Path(settings.admin.mounts_file)
    if not mounts_file.is_absolute():
        from src.utils.config import PROJECT_ROOT

        mounts_file = PROJECT_ROOT / mounts_file
    repo = StaticMountRepository(mounts_file)
    service = StaticMountService(repo)
    service.bind_app(app)
    set_service(service)
    service.apply_all_mounts()
    logger.info("static_mounts_loaded", count=len(repo.list_all()))

    # Initialize Dossier services (requires ML dependencies)
    _dossier_resources = []
    try:
        from src.api.routes import set_services
        from src.embeddings.client import InferenceClient
        from src.index.manager import IndexManager
        from src.ingest.store import MetadataStore
        from src.jobs.manager import JobManager
        from src.narrative.describer import PhotoDescriber
        from src.narrative.generator import DossierGenerator
        from src.retrieval.service import RetrievalService

        inference_client = InferenceClient()
        metadata_store = MetadataStore()
        index_manager = IndexManager()
        retrieval_service = RetrievalService(inference_client, index_manager, metadata_store)
        job_manager = JobManager()
        describer = PhotoDescriber()
        generator = DossierGenerator()

        set_services(
            inference_client=inference_client,
            index_manager=index_manager,
            metadata_store=metadata_store,
            retrieval_service=retrieval_service,
            job_manager=job_manager,
            describer=describer,
            generator=generator,
        )

        _dossier_resources = [metadata_store, index_manager, describer, generator, inference_client]

        logger.info(
            "dossier_services_initialized",
            index_stats=index_manager.stats(),
            corpus_dir=settings.corpus.corpus_dir,
        )

    except ImportError as e:
        logger.warning(
            "dossier_services_skipped",
            reason="ML dependencies not installed (install with: uv sync --extra ml)",
            missing_module=str(e),
        )

    yield

    # Shutdown: close resources
    for resource in _dossier_resources:
        resource.close()

    logger.info("app_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse

    from src.admin.routes import router as admin_router
    from src.api.routes import router
    from src.utils.errors import AppError

    app = FastAPI(
        title="AI/ML Project",
        description="Add your project description here.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # CORS middleware — open in debug, locked down otherwise
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check(request: Request) -> dict:  # noqa: ARG001
        return {
            "status": "ok",
            "env": settings.app_env,
            "version": "0.1.0",
        }

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(
            status_code=_error_code_to_status(exc.code),
            content=exc.to_dict(),
        )

    return app


def _error_code_to_status(code: str) -> int:
    """Map AppError codes to HTTP status codes."""
    mapping = {
        "VALIDATION_ERROR": 400,
        "UNSUPPORTED_IMAGE_FORMAT": 400,
        "IMAGE_TOO_LARGE": 400,
        "UPLOAD_CHUNK_INVALID": 400,
        "UPLOAD_SIZE_EXCEEDED": 400,
        "MANIFEST_INVALID": 400,
        "UNAUTHORIZED": 401,
        "NOT_FOUND": 404,
        "MOUNT_NOT_FOUND": 404,
        "SESSION_NOT_FOUND": 404,
        "SUBJECT_NOT_FOUND": 404,
        "JOB_NOT_FOUND": 404,
        "UPLOAD_SESSION_NOT_FOUND": 404,
        "MOUNT_CONFLICT": 409,
        "SESSION_EXPIRED": 410,
        "MOUNT_FAILED": 422,
        "NO_FACE_DETECTED": 422,
        "RATE_LIMITED": 429,
        "INDEX_NOT_LOADED": 503,
        "INDEX_BUILD_FAILED": 503,
        "INFERENCE_SERVICE_UNAVAILABLE": 503,
        "VLM_UNAVAILABLE": 503,
        "LLM_UNAVAILABLE": 503,
        "JOB_TIMEOUT": 504,
    }
    return mapping.get(code, 500)


def main() -> None:
    """Initialize logging, validate config, and start the server."""
    setup_logging(
        level=settings.logging.level,
        fmt=settings.logging.format,
    )

    logger.info(
        "starting_server",
        env=settings.app_env,
        debug=settings.app_debug,
        host=settings.server.host,
        port=settings.server.port,
    )

    uvicorn.run(
        "main:create_app",
        factory=True,
        host=settings.server.host,
        port=settings.server.port,
        workers=settings.server.workers,
        reload=settings.server.reload,
    )


if __name__ == "__main__":
    main()
