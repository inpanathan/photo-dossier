"""API routes for the Dossier system.

Endpoints for detection, retrieval, timeline, dossier generation,
media serving, jobs, and evaluation. Mounted at /api/v1 in main.py.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.models import (
    BoundingBox,
    DetectionResult,
    Job,
    JobStatus,
    JobType,
    Match,
    SubjectType,
    Timeline,
)
from src.utils.config import settings
from src.utils.errors import AppError, ErrorCode

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

router = APIRouter()

# ---- Lazy-initialized singletons (set during app lifespan) ----

_inference_client = None
_index_manager = None
_metadata_store = None
_retrieval_service = None
_job_manager = None
_describer = None
_generator = None


def set_services(
    inference_client,
    index_manager,
    metadata_store,
    retrieval_service,
    job_manager,
    describer,
    generator,
) -> None:
    """Called from main.py lifespan to inject service instances."""
    global _inference_client, _index_manager, _metadata_store  # noqa: PLW0603
    global _retrieval_service, _job_manager, _describer, _generator  # noqa: PLW0603
    _inference_client = inference_client
    _index_manager = index_manager
    _metadata_store = metadata_store
    _retrieval_service = retrieval_service
    _job_manager = job_manager
    _describer = describer
    _generator = generator


# ---- Request/Response Schemas ----


class QueryRequest(BaseModel):
    subject_type: SubjectType = SubjectType.HUMAN
    bbox: BoundingBox | None = None
    threshold: float | None = None
    top_k: int | None = None


class QueryResponse(BaseModel):
    session_id: str
    total_results: int
    results: list[Match]


class DossierRequest(BaseModel):
    session_id: str
    subject_type: SubjectType = SubjectType.HUMAN


class IndexRequest(BaseModel):
    corpus_dir: str | None = None
    incremental: bool = True


class PaginatedResults(BaseModel):
    results: list[Match]
    total: int
    cursor: str | None = None
    has_more: bool = False


class IndexStatsResponse(BaseModel):
    total_images: int
    total_faces: int
    human_faces: int
    pet_faces: int
    human_vectors: int
    pet_vectors: int
    index_type: str


# ---- Detection ----


@router.post("/detect", response_model=DetectionResult)
async def detect_faces(image: UploadFile = File(...)):
    """Detect human and pet faces in an uploaded image."""
    if not _inference_client:
        raise AppError(
            code=ErrorCode.INFERENCE_SERVICE_UNAVAILABLE,
            message="Inference service not initialized",
        )

    # Save upload to temp file
    upload_dir = Path(settings.upload.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"detect_{image.filename}"

    try:
        content = await image.read()
        temp_path.write_bytes(content)

        # Run detection via inference service
        result = await asyncio.to_thread(_inference_client.detect, temp_path)
        return result

    finally:
        if temp_path.exists():
            temp_path.unlink()


# ---- Query / Retrieval ----


@router.post("/query", response_model=QueryResponse)
async def query_faces(
    image: UploadFile = File(...),
    subject_type: SubjectType = Form(SubjectType.HUMAN),
    bbox_x: float | None = Form(None),
    bbox_y: float | None = Form(None),
    bbox_w: float | None = Form(None),
    bbox_h: float | None = Form(None),
    threshold: float | None = Form(None),
    top_k: int | None = Form(None),
):
    """Query the corpus for matching faces."""
    if not _retrieval_service:
        raise AppError(
            code=ErrorCode.INFERENCE_SERVICE_UNAVAILABLE,
            message="Retrieval service not initialized",
        )

    # Save upload
    upload_dir = Path(settings.upload.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"query_{image.filename}"

    try:
        content = await image.read()
        temp_path.write_bytes(content)

        bbox = None
        if bbox_x is not None and bbox_y is not None and bbox_w is not None and bbox_h is not None:
            bbox = BoundingBox(x=bbox_x, y=bbox_y, width=bbox_w, height=bbox_h)

        session_id, matches = await asyncio.to_thread(
            _retrieval_service.query,
            temp_path,
            subject_type,
            bbox,
            threshold,
            top_k,
        )

        return QueryResponse(
            session_id=session_id,
            total_results=len(matches),
            results=matches,
        )

    finally:
        if temp_path.exists():
            temp_path.unlink()


# ---- Timeline ----


@router.post("/timeline", response_model=Timeline)
async def build_timeline_endpoint(
    session_id: str = Form(...),
    subject_type: SubjectType = Form(SubjectType.HUMAN),
):
    """Build a timeline from query results stored in session."""
    # For now, re-run query and build timeline
    # In production, cache results by session_id
    raise AppError(
        code=ErrorCode.NOT_FOUND,
        message="Timeline requires cached session results. Use /query first then /dossier.",
    )


# ---- Dossier Generation ----


@router.post("/dossier")
async def generate_dossier(request: DossierRequest):
    """Start async dossier generation from a query session.

    Returns a job ID for tracking progress.
    """
    if not _job_manager:
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Job manager not initialized",
        )

    async def _dossier_work(progress_callback=None):

        # This is a placeholder — in production, session results would be cached
        # For now, we return an error indicating the full pipeline
        return {
            "status": "dossier_generated",
            "session_id": request.session_id,
        }

    job = _job_manager.submit(JobType.DOSSIER, _dossier_work)
    return {"job_id": job.id, "status": job.status}


# ---- Full Pipeline (Query + Timeline + Dossier) ----


@router.post("/pipeline")
async def run_full_pipeline(
    image: UploadFile = File(...),
    subject_type: SubjectType = Form(SubjectType.HUMAN),
    bbox_x: float | None = Form(None),
    bbox_y: float | None = Form(None),
    bbox_w: float | None = Form(None),
    bbox_h: float | None = Form(None),
    threshold: float | None = Form(None),
    top_k: int | None = Form(None),
    generate_narrative: bool = Form(True),
):
    """Run the full pipeline: detect -> query -> timeline -> dossier.

    Returns a job ID since this is a long-running operation.
    """
    if not _job_manager or not _retrieval_service:
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Services not initialized",
        )

    upload_dir = Path(settings.upload.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"pipeline_{image.filename}"

    content = await image.read()
    temp_path.write_bytes(content)

    bbox = None
    if bbox_x is not None and bbox_y is not None and bbox_w is not None and bbox_h is not None:
        bbox = BoundingBox(x=bbox_x, y=bbox_y, width=bbox_w, height=bbox_h)

    async def _pipeline_work(progress_callback=None):
        from src.narrative.patterns import detect_patterns
        from src.narrative.timeline import build_timeline

        try:
            # Step 1: Query
            if progress_callback:
                progress_callback(0.1, "Running retrieval query...")

            session_id, matches = _retrieval_service.query(
                temp_path, subject_type, bbox, threshold, top_k
            )

            if not matches:
                return {
                    "session_id": session_id,
                    "total_results": 0,
                    "message": "No matching photos found.",
                }

            # Step 2: Build timeline
            if progress_callback:
                progress_callback(0.3, "Building timeline...")

            timeline = build_timeline(matches, subject_type)
            patterns = detect_patterns(timeline)

            result = {
                "session_id": session_id,
                "total_results": len(matches),
                "timeline": timeline.model_dump(),
                "patterns": [p.model_dump() for p in patterns],
            }

            # Step 3: Generate narrative (if requested and services available)
            if generate_narrative and _describer and _generator:
                if progress_callback:
                    progress_callback(0.5, "Describing photos with VLM...")

                # Get all timeline entries for description
                all_entries = []
                for day in timeline.days:
                    all_entries.extend(day.entries)

                descriptions = _describer.describe_batch(all_entries, subject_type)

                if progress_callback:
                    progress_callback(0.8, "Generating narrative dossier...")

                dossier = _generator.generate(session_id, timeline, descriptions, patterns)
                result["dossier"] = dossier.model_dump()

            return result

        finally:
            if temp_path.exists():
                temp_path.unlink()

    job = _job_manager.submit(JobType.DOSSIER, _pipeline_work)
    return {"job_id": job.id, "status": job.status}


# ---- Batch Indexing ----


@router.post("/index")
async def start_indexing(request: IndexRequest):
    """Start batch indexing of the photo corpus."""
    if not _job_manager or not _inference_client or not _metadata_store or not _index_manager:
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Services not initialized",
        )

    from src.index.batch import BatchIndexer

    indexer = BatchIndexer(_inference_client, _metadata_store, _index_manager)

    async def _index_work(progress_callback=None):
        return await asyncio.to_thread(
            indexer.run,
            corpus_dir=request.corpus_dir,
            incremental=request.incremental,
            progress_callback=progress_callback,
        )

    job = _job_manager.submit(JobType.INDEX, _index_work)
    return {"job_id": job.id, "status": job.status}


@router.get("/index/stats", response_model=IndexStatsResponse)
async def get_index_stats():
    """Get current index statistics."""
    if not _index_manager or not _metadata_store:
        raise AppError(
            code=ErrorCode.INDEX_NOT_LOADED,
            message="Index not loaded",
        )

    idx_stats = _index_manager.stats()
    return IndexStatsResponse(
        total_images=_metadata_store.count_images(),
        total_faces=_metadata_store.count_faces(),
        human_faces=_metadata_store.count_faces(SubjectType.HUMAN),
        pet_faces=_metadata_store.count_faces(SubjectType.PET),
        human_vectors=idx_stats["human_vectors"],
        pet_vectors=idx_stats["pet_vectors"],
        index_type=idx_stats["index_type"],
    )


# ---- Jobs ----


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    """Get job status and progress."""
    if not _job_manager:
        raise AppError(code=ErrorCode.INTERNAL_ERROR, message="Job manager not initialized")

    job = _job_manager.get(job_id)
    if not job:
        raise AppError(code=ErrorCode.JOB_NOT_FOUND, message=f"Job {job_id} not found")

    return job


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    """Stream job progress via Server-Sent Events."""
    if not _job_manager:
        raise AppError(code=ErrorCode.INTERNAL_ERROR, message="Job manager not initialized")

    job = _job_manager.get(job_id)
    if not job:
        raise AppError(code=ErrorCode.JOB_NOT_FOUND, message=f"Job {job_id} not found")

    async def event_stream():
        while True:
            job = _job_manager.get(job_id)
            if not job:
                break

            import json

            data = json.dumps(
                {
                    "status": job.status.value,
                    "progress": job.progress,
                    "message": job.message,
                }
            )
            yield f"data: {data}\n\n"

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                # Send final result
                final = json.dumps(
                    {
                        "status": job.status.value,
                        "progress": job.progress,
                        "result": job.result,
                        "error": job.error,
                    }
                )
                yield f"data: {final}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/jobs")
async def list_jobs(
    job_type: JobType | None = Query(None),
    status: JobStatus | None = Query(None),
):
    """List all jobs, optionally filtered."""
    if not _job_manager:
        raise AppError(code=ErrorCode.INTERNAL_ERROR, message="Job manager not initialized")

    jobs = _job_manager.list_jobs(job_type, status)
    return {"jobs": jobs}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    if not _job_manager:
        raise AppError(code=ErrorCode.INTERNAL_ERROR, message="Job manager not initialized")

    success = _job_manager.cancel(job_id)
    if not success:
        raise AppError(
            code=ErrorCode.JOB_NOT_FOUND,
            message=f"Job {job_id} not found or already completed",
        )

    return {"job_id": job_id, "status": "cancelled"}


# ---- Media Serving ----


@router.get("/media/{path:path}")
async def serve_media(path: str):
    """Serve images from the corpus directory.

    Validates path stays within corpus_dir to prevent traversal.
    """
    corpus_dir = Path(settings.corpus.corpus_dir).resolve()
    file_path = (corpus_dir / path).resolve()

    # Prevent path traversal
    if not str(file_path).startswith(str(corpus_dir)):
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid file path",
        )

    if not file_path.exists() or not file_path.is_file():
        raise AppError(
            code=ErrorCode.NOT_FOUND,
            message=f"File not found: {path}",
        )

    return FileResponse(file_path)
