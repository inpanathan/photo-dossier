"""In-memory async job manager for long-running operations.

Supports indexing, query, and dossier generation jobs with
progress tracking, TTL-based cleanup, and concurrent limits.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from src.models import Job, JobStatus, JobType
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class JobManager:
    """Manages background jobs with concurrency limits and TTL cleanup."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(settings.jobs.max_concurrent_jobs)

    def submit(
        self,
        job_type: JobType,
        work_fn: Callable[..., Coroutine[Any, Any, dict]],
        *args: Any,
        **kwargs: Any,
    ) -> Job:
        """Submit a new background job.

        Args:
            job_type: Type of job (index, query, dossier, evaluate).
            work_fn: Async function to execute. Must return a dict result.
            *args, **kwargs: Arguments to pass to work_fn.

        Returns:
            Job object with assigned ID.
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = Job(id=job_id, type=job_type)
        self._jobs[job_id] = job

        # Pass a progress callback to the work function
        async def _run() -> None:
            async with self._semaphore:
                job.status = JobStatus.RUNNING
                job.updated_at = datetime.now(tz=UTC)
                logger.info("job_started", job_id=job_id, job_type=job_type)

                try:
                    result = await work_fn(
                        *args,
                        progress_callback=lambda p, msg: self._update_progress(job_id, p, msg),
                        **kwargs,
                    )
                    job.status = JobStatus.COMPLETED
                    job.result = result
                    job.progress = 1.0
                    job.completed_at = datetime.now(tz=UTC)
                    logger.info("job_completed", job_id=job_id, job_type=job_type)

                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = datetime.now(tz=UTC)
                    logger.error(
                        "job_failed",
                        job_id=job_id,
                        job_type=job_type,
                        error=str(e),
                        exc_info=True,
                    )

                finally:
                    job.updated_at = datetime.now(tz=UTC)

        task = asyncio.create_task(_run())
        self._tasks[job_id] = task

        logger.info("job_submitted", job_id=job_id, job_type=job_type)
        return job

    def get(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        job_type: JobType | None = None,
        status: JobStatus | None = None,
    ) -> list[Job]:
        """List jobs, optionally filtered by type and status."""
        jobs = list(self._jobs.values())
        if job_type:
            jobs = [j for j in jobs if j.type == job_type]
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def cancel(self, job_id: str) -> bool:
        """Cancel a pending or running job."""
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return False

        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()

        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.now(tz=UTC)
        job.completed_at = datetime.now(tz=UTC)
        logger.info("job_cancelled", job_id=job_id)
        return True

    def cleanup_expired(self) -> int:
        """Remove completed/failed jobs older than TTL.

        Returns:
            Number of jobs cleaned up.
        """
        ttl = timedelta(seconds=settings.jobs.result_ttl_seconds)
        cutoff = datetime.now(tz=UTC) - ttl
        expired = []

        for job_id, job in self._jobs.items():
            if job.completed_at and job.completed_at < cutoff:
                expired.append(job_id)

        for job_id in expired:
            del self._jobs[job_id]
            self._tasks.pop(job_id, None)

        if expired:
            logger.info("jobs_cleaned_up", count=len(expired))

        return len(expired)

    def _update_progress(self, job_id: str, progress: float, message: str) -> None:
        """Update job progress (called from work functions)."""
        job = self._jobs.get(job_id)
        if job:
            job.progress = progress
            job.message = message
            job.updated_at = datetime.now(tz=UTC)

    def stats(self) -> dict:
        """Return job queue statistics."""
        statuses: dict[str, int] = {}
        for job in self._jobs.values():
            statuses[job.status.value] = statuses.get(job.status.value, 0) + 1

        return {
            "total_jobs": len(self._jobs),
            "by_status": statuses,
            "max_concurrent": settings.jobs.max_concurrent_jobs,
        }
