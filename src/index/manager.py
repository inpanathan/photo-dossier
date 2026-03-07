"""FAISS vector index manager with type-separated indices.

Maintains separate indices for human and pet face embeddings to prevent
cross-contamination. Supports flat (exact) and IVF (approximate) indices.
"""

from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np
import structlog

from src.models import SubjectType
from src.utils.config import settings

logger = structlog.get_logger(__name__)


class IndexManager:
    """Manages FAISS indices for human and pet face embeddings."""

    def __init__(
        self,
        index_dir: str | Path | None = None,
        human_dim: int = 512,
        pet_dim: int = 768,
    ) -> None:
        self._index_dir = Path(index_dir or settings.index.faiss_index_dir)
        self._index_dir.mkdir(parents=True, exist_ok=True)

        self._human_dim = human_dim
        self._pet_dim = pet_dim

        self._human_index: faiss.Index | None = None
        self._pet_index: faiss.Index | None = None

        # Counters for assigning embedding IDs
        self._human_count = 0
        self._pet_count = 0

        self._load_or_create()

    def _load_or_create(self) -> None:
        """Load existing indices from disk or create new ones."""
        human_path = self._index_dir / settings.index.human_index_file
        pet_path = self._index_dir / settings.index.pet_index_file

        if human_path.exists():
            self._human_index = faiss.read_index(str(human_path))
            self._human_count = self._human_index.ntotal
            logger.info(
                "index_loaded",
                type="human",
                vectors=self._human_count,
                path=str(human_path),
            )
        else:
            self._human_index = self._create_index(self._human_dim)
            logger.info("index_created", type="human", dimensions=self._human_dim)

        if pet_path.exists():
            self._pet_index = faiss.read_index(str(pet_path))
            self._pet_count = self._pet_index.ntotal
            logger.info(
                "index_loaded",
                type="pet",
                vectors=self._pet_count,
                path=str(pet_path),
            )
        else:
            self._pet_index = self._create_index(self._pet_dim)
            logger.info("index_created", type="pet", dimensions=self._pet_dim)

    def _create_index(self, dim: int) -> faiss.Index:
        """Create a new FAISS index based on config."""
        if settings.index.index_type == "ivf":
            quantizer = faiss.IndexFlatIP(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, settings.index.ivf_nlist)
            return index
        # Default: flat inner product (cosine similarity on normalized vectors)
        return faiss.IndexFlatIP(dim)

    def _get_index(self, subject_type: SubjectType) -> faiss.Index:
        """Get the index for the given subject type."""
        if subject_type == SubjectType.HUMAN:
            return self._human_index
        return self._pet_index

    def add(
        self,
        vectors: np.ndarray,
        subject_type: SubjectType,
    ) -> list[int]:
        """Add embedding vectors to the type-specific index.

        Args:
            vectors: Normalized embedding vectors, shape (n, dim).
            subject_type: Which index to add to.

        Returns:
            List of assigned embedding index IDs.
        """
        index = self._get_index(subject_type)
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)

        # Assign sequential IDs
        if subject_type == SubjectType.HUMAN:
            start_id = self._human_count
            self._human_count += len(vectors)
        else:
            start_id = self._pet_count
            self._pet_count += len(vectors)

        index.add(vectors)
        ids = list(range(start_id, start_id + len(vectors)))

        logger.debug(
            "vectors_added",
            subject_type=subject_type,
            count=len(vectors),
            total=index.ntotal,
        )
        return ids

    def search(
        self,
        query_vector: np.ndarray,
        k: int | None = None,
        threshold: float | None = None,
        subject_type: SubjectType = SubjectType.HUMAN,
    ) -> list[tuple[int, float]]:
        """Search for nearest neighbors in the type-filtered index.

        Args:
            query_vector: Normalized query vector, shape (dim,) or (1, dim).
            k: Number of results to return. Defaults to settings.
            threshold: Minimum similarity score. Defaults to settings per type.
            subject_type: Which index to search.

        Returns:
            List of (embedding_index_id, similarity_score) tuples, sorted by score descending.
        """
        index = self._get_index(subject_type)
        if index.ntotal == 0:
            return []

        k = min(k or settings.index.default_top_k, index.ntotal)

        if threshold is None:
            threshold = (
                settings.index.human_similarity_threshold
                if subject_type == SubjectType.HUMAN
                else settings.index.pet_similarity_threshold
            )

        query = np.ascontiguousarray(query_vector.reshape(1, -1), dtype=np.float32)

        scores, indices = index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx == -1:
                continue
            if score >= threshold:
                results.append((int(idx), float(score)))

        logger.debug(
            "index_search_completed",
            subject_type=subject_type,
            k=k,
            threshold=threshold,
            results=len(results),
        )
        return results

    def save(self) -> None:
        """Persist both indices to disk."""
        human_path = self._index_dir / settings.index.human_index_file
        pet_path = self._index_dir / settings.index.pet_index_file

        faiss.write_index(self._human_index, str(human_path))
        faiss.write_index(self._pet_index, str(pet_path))

        logger.info(
            "indices_saved",
            human_vectors=self._human_index.ntotal if self._human_index is not None else 0,
            pet_vectors=self._pet_index.ntotal if self._pet_index is not None else 0,
            path=str(self._index_dir),
        )

    def stats(self) -> dict:
        """Return index statistics."""
        return {
            "human_vectors": self._human_index.ntotal if self._human_index is not None else 0,
            "pet_vectors": self._pet_index.ntotal if self._pet_index is not None else 0,
            "human_dimensions": self._human_dim,
            "pet_dimensions": self._pet_dim,
            "index_type": settings.index.index_type,
            "index_dir": str(self._index_dir),
        }

    def close(self) -> None:
        """Save and release indices."""
        self.save()

    def __enter__(self) -> IndexManager:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
