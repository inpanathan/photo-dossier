"""Integration test fixtures for Dossier API endpoints.

Provides a test client with mock services injected so endpoints
can be tested without ML dependencies or running inference services.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.models import (
    BoundingBox,
    DetectedFace,
    DetectionResult,
    FaceEmbedding,
    Match,
    SubjectType,
)

# ---- Mock service factories ----


def _make_inference_client() -> MagicMock:
    """Create a mock InferenceClient that returns canned detections."""
    client = MagicMock()
    client.detect.return_value = DetectionResult(
        faces=[
            DetectedFace(
                bbox=BoundingBox(x=10, y=20, width=100, height=100),
                confidence=0.95,
                subject_type=SubjectType.HUMAN,
            ),
        ],
        image_width=640,
        image_height=480,
    )
    client.embed.return_value = FaceEmbedding(
        vector=[0.1] * 512,
        model_name="arcface",
        dimensions=512,
    )
    client.close.return_value = None
    return client


def _make_metadata_store() -> MagicMock:
    """Create a mock MetadataStore."""
    store = MagicMock()
    store.count_images.return_value = 100
    store.count_faces.side_effect = lambda st=None: {
        None: 150,
        SubjectType.HUMAN: 120,
        SubjectType.PET: 30,
    }.get(st, 0)
    store.close.return_value = None
    return store


def _make_index_manager() -> MagicMock:
    """Create a mock IndexManager."""
    mgr = MagicMock()
    mgr.stats.return_value = {
        "human_vectors": 120,
        "pet_vectors": 30,
        "index_type": "IndexFlatIP",
    }
    mgr.close.return_value = None
    return mgr


def _make_retrieval_service() -> MagicMock:
    """Create a mock RetrievalService that returns canned matches."""
    svc = MagicMock()
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    svc.query.return_value = (
        session_id,
        [
            Match(
                face_id="face_001",
                image_id="img_001",
                image_path="photos/day1/IMG_001.jpg",
                similarity_score=0.92,
                subject_type=SubjectType.HUMAN,
                bbox=BoundingBox(x=10, y=20, width=100, height=100),
            ),
            Match(
                face_id="face_002",
                image_id="img_002",
                image_path="photos/day2/IMG_002.jpg",
                similarity_score=0.87,
                subject_type=SubjectType.HUMAN,
                bbox=BoundingBox(x=50, y=60, width=80, height=80),
            ),
        ],
    )
    return svc


def _make_job_manager() -> Any:
    """Create a real JobManager for testing job lifecycle."""
    from src.jobs.manager import JobManager

    return JobManager()


# ---- Fixtures ----


@pytest.fixture()
def corpus_dir(tmp_path: Path) -> Path:
    """Create a temporary corpus directory with sample images."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    # Create a minimal JPEG-like file (1x1 white pixel)
    img_data = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa7\x13\xa2\x80"
        b"\xff\xd9"
    )
    (corpus / "test_image.jpg").write_bytes(img_data)
    sub = corpus / "subdir"
    sub.mkdir()
    (sub / "nested.jpg").write_bytes(img_data)
    return corpus


@pytest.fixture()
def dossier_client(corpus_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Create a test client with mock Dossier services injected.

    Bypasses the normal lifespan service initialization and injects
    mocks directly, so tests work without ML dependencies.
    """
    from main import create_app
    from src.api.routes import set_services
    from src.utils.config import settings

    # Patch the settings singleton to use our temp corpus directory
    original_corpus_dir = settings.corpus.corpus_dir
    settings.corpus.corpus_dir = str(corpus_dir)

    app = create_app()

    with TestClient(app) as client:
        # Inject mock services after the app lifespan has run
        set_services(
            inference_client=_make_inference_client(),
            index_manager=_make_index_manager(),
            metadata_store=_make_metadata_store(),
            retrieval_service=_make_retrieval_service(),
            job_manager=_make_job_manager(),
            describer=MagicMock(),
            generator=MagicMock(),
        )
        yield client

    # Restore original settings and reset services
    settings.corpus.corpus_dir = original_corpus_dir
    set_services(
        inference_client=None,
        index_manager=None,
        metadata_store=None,
        retrieval_service=None,
        job_manager=None,
        describer=None,
        generator=None,
    )


@pytest.fixture()
def sample_image_bytes() -> bytes:
    """Minimal valid JPEG bytes for upload tests."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\xa7\x13\xa2\x80"
        b"\xff\xd9"
    )
