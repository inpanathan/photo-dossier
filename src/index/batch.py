"""Batch indexing pipeline for the photo corpus.

Orchestrates: scan -> detect -> embed -> index for the full corpus.
Supports resumable processing and progress reporting.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from pathlib import Path

import numpy as np
import structlog

from src.embeddings.client import InferenceClient
from src.index.manager import IndexManager
from src.ingest.metadata import extract_metadata
from src.ingest.scanner import scan_corpus
from src.ingest.store import MetadataStore
from src.models import BoundingBox, FaceRecord, SubjectType
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class BatchIndexer:
    """Indexes a photo corpus by scanning, detecting faces, and building FAISS indices."""

    def __init__(
        self,
        inference_client: InferenceClient,
        metadata_store: MetadataStore,
        index_manager: IndexManager,
    ) -> None:
        self._client = inference_client
        self._store = metadata_store
        self._index = index_manager

    def run(
        self,
        corpus_dir: str | Path | None = None,
        batch_size: int = 100,
        incremental: bool = True,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> dict:
        """Run the full indexing pipeline.

        Args:
            corpus_dir: Directory to index. Defaults to settings.
            batch_size: Number of images to process before committing.
            incremental: If True, skip already-indexed images.
            progress_callback: Optional callback(progress_float, message_str).

        Returns:
            Summary dict with counts and timing.
        """
        root = Path(corpus_dir or settings.corpus.corpus_dir).resolve()
        start_time = time.monotonic()

        # Get already indexed paths for incremental mode
        already_indexed = self._store.get_indexed_paths() if incremental else set()

        # Collect all image paths first to know total count
        image_paths = list(scan_corpus(root, already_indexed=already_indexed))
        total = len(image_paths)

        if total == 0:
            logger.info("batch_index_nothing_to_do", corpus_dir=str(root))
            return {"total_images": 0, "total_faces": 0, "elapsed_seconds": 0}

        logger.info("batch_index_started", total_images=total, corpus_dir=str(root))

        stats: dict[str, int | float] = {
            "total_images": 0,
            "human_faces": 0,
            "pet_faces": 0,
            "errors": 0,
        }

        for i, image_path in enumerate(image_paths):
            try:
                self._process_image(image_path, root, stats)
            except Exception:
                stats["errors"] += 1
                logger.warning("image_processing_failed", image=str(image_path), exc_info=True)

            stats["total_images"] = i + 1

            # Commit and report progress periodically
            if (i + 1) % batch_size == 0:
                self._store.commit()
                self._index.save()
                progress = (i + 1) / total
                msg = (
                    f"Processed {i + 1}/{total} images. "
                    f"Faces: {stats['human_faces']} human, {stats['pet_faces']} pet. "
                    f"Errors: {stats['errors']}"
                )
                logger.info("batch_index_progress", progress=progress, **stats)
                if progress_callback:
                    progress_callback(progress, msg)

        # Final commit
        self._store.commit()
        self._index.save()

        elapsed_seconds = round(time.monotonic() - start_time, 1)
        stats["elapsed_seconds"] = elapsed_seconds
        stats["total_faces"] = stats["human_faces"] + stats["pet_faces"]

        logger.info("batch_index_completed", **stats)

        if progress_callback:
            progress_callback(1.0, f"Indexing complete. {stats['total_faces']} faces indexed.")

        return stats

    def _process_image(
        self,
        image_path: Path,
        corpus_root: Path,
        stats: dict,
    ) -> None:
        """Process a single image: extract metadata, detect faces, compute embeddings."""
        # Extract and store EXIF metadata
        meta = extract_metadata(image_path, corpus_root)
        self._store.add_image(meta)

        # Detect faces and compute embeddings via inference service
        results = self._client.detect_and_embed(image_path)

        for item in results:
            face = item["face"]
            embedding = item["embedding"]

            # Add embedding vector to FAISS index
            vector = np.array(embedding.vector, dtype=np.float32).reshape(1, -1)
            subject_type = SubjectType(face.subject_type)
            embedding_ids = self._index.add(vector, subject_type)

            # Store face record in SQLite
            face_record = FaceRecord(
                face_id=str(uuid.uuid4()),
                image_id=meta.image_id,
                subject_type=subject_type,
                bbox=BoundingBox(
                    x=face.bbox.x,
                    y=face.bbox.y,
                    width=face.bbox.width,
                    height=face.bbox.height,
                ),
                confidence=face.confidence,
                embedding_index_id=embedding_ids[0],
                model_name=embedding.model_name,
            )
            self._store.add_face(face_record)

            if subject_type == SubjectType.HUMAN:
                stats["human_faces"] += 1
            else:
                stats["pet_faces"] += 1
