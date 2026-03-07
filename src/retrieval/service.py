"""Retrieval service — orchestrates query pipeline.

Given a reference photo, detects the subject, embeds the face,
searches the FAISS index, and enriches results with metadata.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import numpy as np
import structlog

from src.embeddings.client import InferenceClient
from src.index.manager import IndexManager
from src.ingest.store import MetadataStore
from src.models import BoundingBox, Match, SubjectType
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class RetrievalService:
    """Handles the full query pipeline: embed -> search -> enrich."""

    def __init__(
        self,
        inference_client: InferenceClient,
        index_manager: IndexManager,
        metadata_store: MetadataStore,
    ) -> None:
        self._client = inference_client
        self._index = index_manager
        self._store = metadata_store

    def query(
        self,
        image_path: str | Path,
        subject_type: SubjectType,
        bbox: BoundingBox | None = None,
        threshold: float | None = None,
        top_k: int | None = None,
    ) -> tuple[str, list[Match]]:
        """Run a retrieval query against the corpus index.

        Args:
            image_path: Path to the reference photo.
            subject_type: Whether searching for a human or pet.
            bbox: Optional face bounding box to crop before embedding.
            threshold: Minimum similarity score override.
            top_k: Max results override.

        Returns:
            Tuple of (session_id, list of Match objects sorted by similarity).
        """
        start = time.monotonic()
        session_id = f"qs_{uuid.uuid4().hex[:12]}"

        # Compute embedding for the reference face
        embedding = self._client.embed(image_path, subject_type, bbox)
        query_vector = np.array(embedding.vector, dtype=np.float32)

        # Search the type-filtered FAISS index
        raw_results = self._index.search(
            query_vector,
            k=top_k,
            threshold=threshold,
            subject_type=subject_type,
        )

        # Enrich results with metadata
        matches = []
        corpus_dir = Path(settings.corpus.corpus_dir).resolve()

        for embedding_idx, score in raw_results:
            face_record = self._store.get_face_by_embedding_id(embedding_idx, subject_type)
            if not face_record:
                continue

            image_meta = self._store.get_image_metadata(face_record.image_id)
            image_path_str = image_meta.path if image_meta else face_record.image_id

            matches.append(
                Match(
                    face_id=face_record.face_id,
                    image_id=face_record.image_id,
                    image_path=str(corpus_dir / image_path_str),
                    image_url=f"/api/v1/media/{image_path_str}",
                    similarity_score=score,
                    subject_type=subject_type,
                    bbox=face_record.bbox,
                    metadata=image_meta,
                )
            )

        elapsed_ms = round((time.monotonic() - start) * 1000)
        logger.info(
            "retrieval_completed",
            session_id=session_id,
            subject_type=subject_type,
            total_results=len(matches),
            latency_ms=elapsed_ms,
        )

        return session_id, matches
