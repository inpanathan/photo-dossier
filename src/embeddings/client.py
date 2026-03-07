"""HTTP client for the remote inference service on 7810.

All face detection and embedding computation is delegated to the
inference service running on the 7810 node (2x RTX 3060).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import structlog

from src.models import (
    BoundingBox,
    DetectedFace,
    DetectionResult,
    FaceEmbedding,
    SubjectType,
)
from src.utils.config import settings
from src.utils.errors import AppError, ErrorCode

logger = structlog.get_logger(__name__)


class InferenceClient:
    """Client for the Dossier inference service running on 7810."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._base_url = base_url or settings.inference.base_url
        self._timeout = timeout or settings.inference.timeout_seconds
        self._client = httpx.Client(base_url=self._base_url, timeout=self._timeout)

    def health(self) -> dict:
        """Check inference service health."""
        try:
            resp = self._client.get("/health")
            resp.raise_for_status()
            result: dict = resp.json()
            return result
        except httpx.HTTPError as e:
            raise AppError(
                code=ErrorCode.INFERENCE_SERVICE_UNAVAILABLE,
                message=f"Inference service at {self._base_url} is not reachable",
                cause=e,
            ) from e

    def detect(self, image_path: str | Path) -> DetectionResult:
        """Detect all human and pet faces in an image.

        Args:
            image_path: Path to the image file on the local filesystem.

        Returns:
            DetectionResult with bounding boxes, types, and confidence scores.
        """
        start = time.monotonic()
        path = Path(image_path)

        try:
            with open(path, "rb") as f:
                resp = self._client.post(
                    "/detect",
                    files={"file": (path.name, f, _guess_mime(path))},
                )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise AppError(
                code=ErrorCode.INFERENCE_SERVICE_UNAVAILABLE,
                message=f"Detection request failed for {path.name}",
                context={"image_path": str(path)},
                cause=e,
            ) from e

        data = resp.json()
        elapsed_ms = round((time.monotonic() - start) * 1000)
        logger.info(
            "detection_completed",
            image=path.name,
            faces=len(data["faces"]),
            latency_ms=elapsed_ms,
        )

        return DetectionResult(
            image_width=data["image_width"],
            image_height=data["image_height"],
            faces=[DetectedFace(**f) for f in data["faces"]],
        )

    def embed(
        self,
        image_path: str | Path,
        subject_type: SubjectType,
        bbox: BoundingBox | None = None,
    ) -> FaceEmbedding:
        """Compute face/body embedding for a subject in an image.

        Args:
            image_path: Path to the image file.
            subject_type: Whether this is a human or pet subject.
            bbox: Optional bounding box to crop before embedding.

        Returns:
            FaceEmbedding with the normalized vector and model metadata.
        """
        start = time.monotonic()
        path = Path(image_path)
        bbox_json = json.dumps(bbox.model_dump()) if bbox else ""

        try:
            with open(path, "rb") as f:
                resp = self._client.post(
                    "/embed",
                    files={"file": (path.name, f, _guess_mime(path))},
                    data={
                        "subject_type": subject_type.value,
                        "bbox_json": bbox_json,
                    },
                )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise AppError(
                code=ErrorCode.INFERENCE_SERVICE_UNAVAILABLE,
                message=f"Embedding request failed for {path.name}",
                context={"image_path": str(path), "subject_type": subject_type},
                cause=e,
            ) from e

        data = resp.json()
        emb_data = data["embeddings"][0]
        elapsed_ms = round((time.monotonic() - start) * 1000)
        logger.info(
            "embedding_computed",
            image=path.name,
            subject_type=subject_type,
            model=emb_data["model_name"],
            dimensions=emb_data["dimensions"],
            latency_ms=elapsed_ms,
        )

        return FaceEmbedding(**emb_data)

    def detect_and_embed(self, image_path: str | Path) -> list[dict]:
        """Detect all faces and compute embeddings in a single call.

        Optimized for batch indexing — avoids two round trips per image.

        Returns:
            List of dicts with 'face' (DetectedFace) and 'embedding' (FaceEmbedding).
        """
        start = time.monotonic()
        path = Path(image_path)

        try:
            with open(path, "rb") as f:
                resp = self._client.post(
                    "/detect-and-embed",
                    files={"file": (path.name, f, _guess_mime(path))},
                )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise AppError(
                code=ErrorCode.INFERENCE_SERVICE_UNAVAILABLE,
                message=f"Detect-and-embed request failed for {path.name}",
                context={"image_path": str(path)},
                cause=e,
            ) from e

        data = resp.json()
        elapsed_ms = round((time.monotonic() - start) * 1000)

        results = []
        for item in data["results"]:
            results.append(
                {
                    "face": DetectedFace(**item["face"]),
                    "embedding": FaceEmbedding(**item["embedding"]),
                }
            )

        logger.info(
            "detect_and_embed_completed",
            image=path.name,
            faces=len(results),
            latency_ms=elapsed_ms,
        )

        return results

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> InferenceClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _guess_mime(path: Path) -> str:
    """Guess MIME type from file extension."""
    suffix = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".heic": "image/heic",
        ".heif": "image/heif",
    }.get(suffix, "application/octet-stream")
