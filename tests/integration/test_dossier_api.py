"""Integration tests for Dossier API endpoints.

Tests route logic, validation, error handling, and response schemas
using mock services injected via the dossier_client fixture.
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

# ---- Detection ----


def test_detect_returns_faces(dossier_client: TestClient, sample_image_bytes: bytes) -> None:
    resp = dossier_client.post(
        "/api/v1/detect",
        files={"image": ("photo.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["faces"]) == 1
    assert data["faces"][0]["subject_type"] == "human"
    assert data["faces"][0]["confidence"] == 0.95
    assert data["image_width"] == 640


# ---- Query ----


def test_query_returns_matches(dossier_client: TestClient, sample_image_bytes: bytes) -> None:
    resp = dossier_client.post(
        "/api/v1/query",
        files={"image": ("photo.jpg", sample_image_bytes, "image/jpeg")},
        data={"subject_type": "human"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["total_results"] == 2
    assert data["results"][0]["similarity_score"] == 0.92


def test_query_with_bbox(dossier_client: TestClient, sample_image_bytes: bytes) -> None:
    resp = dossier_client.post(
        "/api/v1/query",
        files={"image": ("photo.jpg", sample_image_bytes, "image/jpeg")},
        data={
            "subject_type": "human",
            "bbox_x": "10",
            "bbox_y": "20",
            "bbox_w": "100",
            "bbox_h": "100",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_results"] == 2


# ---- Index Stats ----


def test_index_stats(dossier_client: TestClient) -> None:
    resp = dossier_client.get("/api/v1/index/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_images"] == 100
    assert data["total_faces"] == 150
    assert data["human_faces"] == 120
    assert data["pet_faces"] == 30
    assert data["human_vectors"] == 120
    assert data["pet_vectors"] == 30
    assert data["index_type"] == "IndexFlatIP"


# ---- Jobs ----


def test_list_jobs_empty(dossier_client: TestClient) -> None:
    resp = dossier_client.get("/api/v1/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jobs"] == []


def test_dossier_creates_job(dossier_client: TestClient) -> None:
    resp = dossier_client.post(
        "/api/v1/dossier",
        json={"session_id": "test_session_123", "subject_type": "human"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_get_job_by_id(dossier_client: TestClient) -> None:
    # Create a job first
    resp = dossier_client.post(
        "/api/v1/dossier",
        json={"session_id": "test_session", "subject_type": "human"},
    )
    job_id = resp.json()["job_id"]

    resp = dossier_client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == job_id
    assert data["type"] == "dossier"


def test_get_nonexistent_job_returns_404(dossier_client: TestClient) -> None:
    resp = dossier_client.get("/api/v1/jobs/job_nonexistent")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_cancel_completed_job_returns_404(dossier_client: TestClient) -> None:
    """A completed job cannot be cancelled — returns 404."""
    resp = dossier_client.post(
        "/api/v1/dossier",
        json={"session_id": "cancel_me", "subject_type": "human"},
    )
    job_id = resp.json()["job_id"]

    # Wait for the trivial job to complete
    for _ in range(20):
        r = dossier_client.get(f"/api/v1/jobs/{job_id}")
        if r.json()["status"] == "completed":
            break
        time.sleep(0.05)

    resp = dossier_client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert resp.status_code == 404


def test_cancel_nonexistent_job_returns_404(dossier_client: TestClient) -> None:
    resp = dossier_client.post("/api/v1/jobs/job_fake/cancel")
    assert resp.status_code == 404


def test_list_jobs_after_creating(dossier_client: TestClient) -> None:
    dossier_client.post(
        "/api/v1/dossier",
        json={"session_id": "sess_a", "subject_type": "human"},
    )
    dossier_client.post(
        "/api/v1/dossier",
        json={"session_id": "sess_b", "subject_type": "pet"},
    )

    resp = dossier_client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert len(resp.json()["jobs"]) == 2


def test_job_completes_async(dossier_client: TestClient) -> None:
    """Verify that the dossier job completes within a reasonable time."""
    resp = dossier_client.post(
        "/api/v1/dossier",
        json={"session_id": "async_test", "subject_type": "human"},
    )
    job_id = resp.json()["job_id"]

    # Poll until completed (should be near-instant since work_fn is trivial)
    for _ in range(20):
        resp = dossier_client.get(f"/api/v1/jobs/{job_id}")
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert resp.json()["status"] == "completed"
    assert resp.json()["result"]["session_id"] == "async_test"


# ---- Media Serving ----


def test_serve_media_file(dossier_client: TestClient, corpus_dir) -> None:
    resp = dossier_client.get("/api/v1/media/test_image.jpg")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")


def test_serve_media_nested_file(dossier_client: TestClient, corpus_dir) -> None:
    resp = dossier_client.get("/api/v1/media/subdir/nested.jpg")
    assert resp.status_code == 200


def test_serve_media_not_found(dossier_client: TestClient) -> None:
    resp = dossier_client.get("/api/v1/media/nonexistent.jpg")
    assert resp.status_code == 404


def test_serve_media_path_traversal_blocked(dossier_client: TestClient) -> None:
    resp = dossier_client.get("/api/v1/media/../../../etc/passwd")
    assert resp.status_code in (400, 404)


# ---- Pipeline ----


def test_pipeline_creates_job(dossier_client: TestClient, sample_image_bytes: bytes) -> None:
    resp = dossier_client.post(
        "/api/v1/pipeline",
        files={"image": ("photo.jpg", sample_image_bytes, "image/jpeg")},
        data={"subject_type": "human", "generate_narrative": "false"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"


# ---- Error cases: services not initialized ----


def test_detect_without_services_returns_503(sample_image_bytes: bytes) -> None:
    """When services are not initialized, detection endpoints return 503."""
    from main import create_app
    from src.api.routes import set_services

    # Reset all services to None
    set_services(
        inference_client=None,
        index_manager=None,
        metadata_store=None,
        retrieval_service=None,
        job_manager=None,
        describer=None,
        generator=None,
    )

    app = create_app()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/detect",
            files={"image": ("photo.jpg", sample_image_bytes, "image/jpeg")},
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "INFERENCE_SERVICE_UNAVAILABLE"
