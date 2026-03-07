"""Unit tests for src/jobs/manager.py — JobManager.

All tests are async because JobManager.submit() calls asyncio.create_task(),
which requires a running event loop. The project configures asyncio_mode="auto"
in pytest.ini_options so plain async def functions are auto-collected.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from src.jobs.manager import JobManager
from src.models import Job, JobStatus, JobType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def manager() -> JobManager:
    return JobManager()


# ---------------------------------------------------------------------------
# Async work-function helpers
# ---------------------------------------------------------------------------


async def _success_fn(*, progress_callback) -> dict:
    progress_callback(0.5, "halfway")
    await asyncio.sleep(0)
    progress_callback(1.0, "done")
    return {"output": "ok"}


async def _failing_fn(*, progress_callback) -> dict:
    await asyncio.sleep(0)
    raise ValueError("deliberate failure")


async def _slow_fn(*, progress_callback) -> dict:
    await asyncio.sleep(10)
    return {}


# ---------------------------------------------------------------------------
# submit
# ---------------------------------------------------------------------------


async def test_submit_returns_job_with_id(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    assert isinstance(job, Job)
    assert job.id.startswith("job_")
    assert job.type == JobType.QUERY
    assert job.status == JobStatus.PENDING


async def test_submit_different_types(manager: JobManager) -> None:
    j1 = manager.submit(JobType.INDEX, _success_fn)
    j2 = manager.submit(JobType.DOSSIER, _success_fn)
    assert j1.type == JobType.INDEX
    assert j2.type == JobType.DOSSIER
    assert j1.id != j2.id


async def test_submit_job_appears_in_list(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    jobs = manager.list_jobs()
    assert any(j.id == job.id for j in jobs)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


async def test_get_existing_job_returns_job(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    found = manager.get(job.id)
    assert found is not None
    assert found.id == job.id


def test_get_nonexistent_job_returns_none(manager: JobManager) -> None:
    # get() is synchronous — no event loop needed
    result = manager.get("job_doesnotexist")
    assert result is None


# ---------------------------------------------------------------------------
# list_jobs
# ---------------------------------------------------------------------------


def test_list_jobs_empty_manager(manager: JobManager) -> None:
    assert manager.list_jobs() == []


async def test_list_jobs_filter_by_type(manager: JobManager) -> None:
    manager.submit(JobType.INDEX, _success_fn)
    manager.submit(JobType.QUERY, _success_fn)
    manager.submit(JobType.QUERY, _success_fn)

    index_jobs = manager.list_jobs(job_type=JobType.INDEX)
    query_jobs = manager.list_jobs(job_type=JobType.QUERY)

    assert len(index_jobs) == 1
    assert len(query_jobs) == 2


async def test_list_jobs_filter_by_status(manager: JobManager) -> None:
    j1 = manager.submit(JobType.QUERY, _success_fn)
    manager.submit(JobType.QUERY, _success_fn)
    manager.cancel(j1.id)

    cancelled = manager.list_jobs(status=JobStatus.CANCELLED)
    assert any(j.id == j1.id for j in cancelled)
    assert all(j.status == JobStatus.CANCELLED for j in cancelled)


async def test_list_jobs_sorted_newest_first(manager: JobManager) -> None:
    j1 = manager.submit(JobType.QUERY, _success_fn)
    j2 = manager.submit(JobType.QUERY, _success_fn)
    jobs = manager.list_jobs()
    # j2 was created after j1 so it should appear first
    assert jobs[0].id == j2.id
    assert jobs[1].id == j1.id


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


async def test_cancel_pending_job_marks_cancelled(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    result = manager.cancel(job.id)
    assert result is True
    assert job.status == JobStatus.CANCELLED
    assert job.completed_at is not None


def test_cancel_nonexistent_job_returns_false(manager: JobManager) -> None:
    assert manager.cancel("job_missing") is False


async def test_cancel_already_cancelled_job_returns_false(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    manager.cancel(job.id)
    result = manager.cancel(job.id)
    assert result is False


async def test_cancel_running_job_stops_task(manager: JobManager) -> None:
    job = manager.submit(JobType.INDEX, _slow_fn)
    # Yield to let the task acquire the semaphore and enter RUNNING state
    await asyncio.sleep(0.01)
    result = manager.cancel(job.id)
    assert result is True
    assert job.status == JobStatus.CANCELLED


async def test_cancel_completed_job_returns_false(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    await asyncio.sleep(0.05)
    assert job.status == JobStatus.COMPLETED
    assert manager.cancel(job.id) is False


# ---------------------------------------------------------------------------
# Job execution (async)
# ---------------------------------------------------------------------------


async def test_successful_job_sets_completed_status(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    await asyncio.sleep(0.05)
    assert job.status == JobStatus.COMPLETED
    assert job.result == {"output": "ok"}
    assert job.progress == pytest.approx(1.0)
    assert job.completed_at is not None


async def test_failing_job_sets_failed_status(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _failing_fn)
    await asyncio.sleep(0.05)
    assert job.status == JobStatus.FAILED
    assert job.error == "deliberate failure"
    assert job.completed_at is not None


async def test_progress_callback_updates_job(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    await asyncio.sleep(0.05)
    # After completion the progress must be 1.0
    assert job.progress == pytest.approx(1.0)


async def test_job_passes_extra_kwargs_to_work_fn(manager: JobManager) -> None:
    received: dict = {}

    async def _echo_fn(*, progress_callback, value: int) -> dict:
        received["value"] = value
        return {}

    manager.submit(JobType.QUERY, _echo_fn, value=42)
    await asyncio.sleep(0.05)
    assert received["value"] == 42


async def test_running_job_has_updated_at_set(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    before = job.updated_at
    await asyncio.sleep(0.05)
    assert job.updated_at >= before


# ---------------------------------------------------------------------------
# cleanup_expired
# ---------------------------------------------------------------------------


async def test_cleanup_expired_removes_old_completed_jobs(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    # Manually mark as completed far in the past
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.now(tz=UTC) - timedelta(seconds=9999)

    removed = manager.cleanup_expired()
    assert removed == 1
    assert manager.get(job.id) is None


async def test_cleanup_expired_keeps_recent_completed_jobs(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.now(tz=UTC)

    removed = manager.cleanup_expired()
    assert removed == 0
    assert manager.get(job.id) is not None


async def test_cleanup_expired_keeps_pending_jobs(manager: JobManager) -> None:
    manager.submit(JobType.QUERY, _success_fn)
    removed = manager.cleanup_expired()
    assert removed == 0


def test_cleanup_expired_returns_zero_when_nothing_to_clean(manager: JobManager) -> None:
    assert manager.cleanup_expired() == 0


async def test_cleanup_expired_removes_multiple_stale_jobs(manager: JobManager) -> None:
    j1 = manager.submit(JobType.QUERY, _success_fn)
    j2 = manager.submit(JobType.INDEX, _success_fn)
    for job in (j1, j2):
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now(tz=UTC) - timedelta(seconds=9999)

    removed = manager.cleanup_expired()
    assert removed == 2


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


def test_stats_empty_manager(manager: JobManager) -> None:
    s = manager.stats()
    assert s["total_jobs"] == 0
    assert s["by_status"] == {}


async def test_stats_counts_by_status(manager: JobManager) -> None:
    j1 = manager.submit(JobType.QUERY, _success_fn)
    manager.submit(JobType.INDEX, _success_fn)
    manager.cancel(j1.id)

    s = manager.stats()
    assert s["total_jobs"] == 2
    assert s["by_status"].get("cancelled", 0) == 1
    assert s["by_status"].get("pending", 0) == 1


def test_stats_max_concurrent_present(manager: JobManager) -> None:
    s = manager.stats()
    assert "max_concurrent" in s
    assert s["max_concurrent"] > 0


# ---------------------------------------------------------------------------
# _update_progress (internal method — called from within work functions)
# ---------------------------------------------------------------------------


async def test_update_progress_updates_message_and_progress(manager: JobManager) -> None:
    job = manager.submit(JobType.QUERY, _success_fn)
    manager._update_progress(job.id, 0.42, "working hard")
    assert job.progress == pytest.approx(0.42)
    assert job.message == "working hard"


def test_update_progress_nonexistent_job_noop(manager: JobManager) -> None:
    # Should not raise even when the job doesn't exist
    manager._update_progress("job_missing", 0.5, "noop")
