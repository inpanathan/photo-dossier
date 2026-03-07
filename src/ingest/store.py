"""SQLite-backed metadata store for images, faces, and query sessions.

Provides CRUD operations for the indexing pipeline and query system.
Uses WAL mode for concurrent read access during queries.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import structlog

from src.models import FaceRecord, ImageMetadata, SubjectType
from src.utils.config import settings

logger = structlog.get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    format TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    indexed_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'indexed'
);

CREATE TABLE IF NOT EXISTS metadata (
    image_id TEXT PRIMARY KEY REFERENCES images(id),
    timestamp TEXT,
    latitude REAL,
    longitude REAL,
    orientation INTEGER,
    camera_make TEXT,
    camera_model TEXT,
    location_name TEXT,
    location_city TEXT,
    location_country TEXT
);

CREATE TABLE IF NOT EXISTS faces (
    id TEXT PRIMARY KEY,
    image_id TEXT NOT NULL REFERENCES images(id),
    subject_type TEXT NOT NULL,
    bbox_x REAL NOT NULL,
    bbox_y REAL NOT NULL,
    bbox_w REAL NOT NULL,
    bbox_h REAL NOT NULL,
    confidence REAL NOT NULL,
    embedding_index_id INTEGER,
    model_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_faces_image ON faces(image_id);
CREATE INDEX IF NOT EXISTS idx_faces_type ON faces(subject_type);
CREATE INDEX IF NOT EXISTS idx_metadata_timestamp ON metadata(timestamp);
"""


class MetadataStore:
    """SQLite store for image metadata and face records."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = str(db_path or settings.index.metadata_db_path)

        # Ensure parent directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info("metadata_store_opened", path=self._db_path)

    def add_image(self, meta: ImageMetadata) -> None:
        """Insert or update an image record with its metadata."""
        now = datetime.now(tz=UTC).isoformat()

        self._conn.execute(
            """INSERT OR REPLACE INTO images (id, path, format, size_bytes, indexed_at, status)
               VALUES (?, ?, ?, ?, ?, 'indexed')""",
            (meta.image_id, meta.path, meta.format, meta.size_bytes, now),
        )
        self._conn.execute(
            """INSERT OR REPLACE INTO metadata
               (image_id, timestamp, latitude, longitude, orientation, camera_make, camera_model)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                meta.image_id,
                meta.timestamp.isoformat() if meta.timestamp else None,
                meta.latitude,
                meta.longitude,
                meta.orientation,
                meta.camera_make,
                meta.camera_model,
            ),
        )

    def add_face(self, face: FaceRecord) -> None:
        """Insert a face record."""
        now = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO faces
               (id, image_id, subject_type, bbox_x, bbox_y, bbox_w, bbox_h,
                confidence, embedding_index_id, model_name, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                face.face_id,
                face.image_id,
                face.subject_type.value,
                face.bbox.x,
                face.bbox.y,
                face.bbox.width,
                face.bbox.height,
                face.confidence,
                face.embedding_index_id,
                face.model_name,
                now,
            ),
        )

    def commit(self) -> None:
        """Commit pending changes."""
        self._conn.commit()

    def get_indexed_paths(self) -> set[str]:
        """Return set of all indexed image paths (for incremental indexing)."""
        cursor = self._conn.execute("SELECT path FROM images WHERE status = 'indexed'")
        return {row["path"] for row in cursor}

    def get_image_metadata(self, image_id: str) -> ImageMetadata | None:
        """Fetch image metadata by image ID."""
        row = self._conn.execute(
            """SELECT i.id, i.path, i.format, i.size_bytes,
                      m.timestamp, m.latitude, m.longitude, m.orientation,
                      m.camera_make, m.camera_model
               FROM images i
               LEFT JOIN metadata m ON i.id = m.image_id
               WHERE i.id = ?""",
            (image_id,),
        ).fetchone()

        if not row:
            return None

        ts = None
        if row["timestamp"]:
            import contextlib

            with contextlib.suppress(ValueError):
                ts = datetime.fromisoformat(row["timestamp"])

        return ImageMetadata(
            image_id=row["id"],
            path=row["path"],
            format=row["format"],
            size_bytes=row["size_bytes"],
            timestamp=ts,
            latitude=row["latitude"],
            longitude=row["longitude"],
            orientation=row["orientation"],
            camera_make=row["camera_make"],
            camera_model=row["camera_model"],
            has_gps=row["latitude"] is not None and row["longitude"] is not None,
            has_timestamp=ts is not None,
        )

    def get_face_by_embedding_id(
        self, embedding_index_id: int, subject_type: SubjectType
    ) -> FaceRecord | None:
        """Fetch face record by FAISS embedding index ID and subject type."""
        from src.models import BoundingBox

        row = self._conn.execute(
            """SELECT * FROM faces
               WHERE embedding_index_id = ? AND subject_type = ?""",
            (embedding_index_id, subject_type.value),
        ).fetchone()

        if not row:
            return None

        return FaceRecord(
            face_id=row["id"],
            image_id=row["image_id"],
            subject_type=SubjectType(row["subject_type"]),
            bbox=BoundingBox(
                x=row["bbox_x"],
                y=row["bbox_y"],
                width=row["bbox_w"],
                height=row["bbox_h"],
            ),
            confidence=row["confidence"],
            embedding_index_id=row["embedding_index_id"],
            model_name=row["model_name"],
        )

    def count_images(self) -> int:
        """Return total number of indexed images."""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM images").fetchone()
        return int(row["cnt"])

    def count_faces(self, subject_type: SubjectType | None = None) -> int:
        """Return total number of face records, optionally filtered by type."""
        if subject_type:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM faces WHERE subject_type = ?",
                (subject_type.value,),
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) as cnt FROM faces").fetchone()
        return int(row["cnt"])

    def close(self) -> None:
        self._conn.close()
        logger.info("metadata_store_closed", path=self._db_path)

    def __enter__(self) -> MetadataStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
