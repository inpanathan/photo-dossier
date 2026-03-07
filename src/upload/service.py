"""Photo upload service with standard and resumable chunked upload support.

Handles file validation, EXIF extraction, and HEIC conversion.
Resumable uploads use a session-based approach with Content-Range semantics.
"""

from __future__ import annotations

import hashlib
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from src.models import ImageMetadata
from src.utils.config import settings
from src.utils.errors import AppError, ErrorCode

logger = structlog.get_logger(__name__)

# Magic bytes for supported image formats
_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"\x00\x00\x00": "image/heic",  # ftyp box (simplified check)
}


class UploadResult(BaseModel):
    """Result of a completed photo upload."""

    photo_id: str
    filename: str
    size_bytes: int
    content_type: str
    metadata: ImageMetadata | None = None
    path: str = ""


class UploadSession(BaseModel):
    """Tracks state of a resumable upload."""

    session_id: str
    filename: str
    total_size: int
    received_bytes: int = 0
    content_type: str = "image/jpeg"
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    completed: bool = False
    photo_id: str | None = None


class UploadService:
    """Manages photo uploads with validation and metadata extraction."""

    def __init__(self) -> None:
        self._upload_dir = Path(settings.upload.upload_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._chunks_dir = self._upload_dir / "chunks"
        self._chunks_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, UploadSession] = {}

    def upload_standard(self, filename: str, content: bytes) -> UploadResult:
        """Handle a standard single-request upload.

        Validates file type, size, extracts EXIF, and stores the file.
        """
        self._validate_size(len(content))
        content_type = self._validate_magic_bytes(content)
        self._validate_content_type(content_type)

        photo_id = f"photo_{uuid.uuid4().hex[:12]}"
        safe_name = self._safe_filename(filename)
        dest = self._upload_dir / f"{photo_id}_{safe_name}"
        dest.write_bytes(content)

        metadata = self._extract_metadata_safe(dest, photo_id)

        logger.info(
            "photo_uploaded",
            photo_id=photo_id,
            filename=safe_name,
            size_bytes=len(content),
            content_type=content_type,
        )

        return UploadResult(
            photo_id=photo_id,
            filename=safe_name,
            size_bytes=len(content),
            content_type=content_type,
            metadata=metadata,
            path=str(dest),
        )

    def init_resumable(self, filename: str, total_size: int, content_type: str) -> UploadSession:
        """Initialize a resumable upload session."""
        self._validate_size(total_size)
        self._validate_content_type(content_type)

        session_id = f"upload_{uuid.uuid4().hex[:12]}"
        session_dir = self._chunks_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        session = UploadSession(
            session_id=session_id,
            filename=self._safe_filename(filename),
            total_size=total_size,
            content_type=content_type,
        )
        self._sessions[session_id] = session

        logger.info(
            "resumable_upload_initiated",
            session_id=session_id,
            filename=session.filename,
            total_size=total_size,
        )

        return session

    def upload_chunk(self, session_id: str, chunk: bytes, offset: int) -> UploadSession:
        """Receive a chunk for a resumable upload.

        Args:
            session_id: The upload session ID.
            chunk: The chunk data.
            offset: Byte offset where this chunk starts.

        Returns:
            Updated session state.
        """
        session = self._get_session(session_id)

        if session.completed:
            raise AppError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Upload session already completed",
            )

        if offset != session.received_bytes:
            raise AppError(
                code=ErrorCode.UPLOAD_CHUNK_INVALID,
                message=f"Expected offset {session.received_bytes}, got {offset}",
            )

        if session.received_bytes + len(chunk) > session.total_size:
            raise AppError(
                code=ErrorCode.UPLOAD_SIZE_EXCEEDED,
                message="Chunk would exceed declared total size",
            )

        # Write chunk to session directory
        chunk_path = self._chunks_dir / session_id / f"chunk_{offset:012d}"
        chunk_path.write_bytes(chunk)
        session.received_bytes += len(chunk)

        logger.info(
            "chunk_received",
            session_id=session_id,
            offset=offset,
            chunk_size=len(chunk),
            received=session.received_bytes,
            total=session.total_size,
        )

        # Auto-complete if all bytes received
        if session.received_bytes >= session.total_size:
            self._assemble_and_complete(session)

        return session

    def get_session(self, session_id: str) -> UploadSession:
        """Get the current state of an upload session."""
        return self._get_session(session_id)

    def _get_session(self, session_id: str) -> UploadSession:
        session = self._sessions.get(session_id)
        if not session:
            raise AppError(
                code=ErrorCode.UPLOAD_SESSION_NOT_FOUND,
                message=f"Upload session {session_id} not found",
            )
        return session

    def _assemble_and_complete(self, session: UploadSession) -> None:
        """Assemble chunks into final file and complete the session."""
        session_dir = self._chunks_dir / session.session_id
        chunk_files = sorted(session_dir.iterdir())

        photo_id = f"photo_{uuid.uuid4().hex[:12]}"
        dest = self._upload_dir / f"{photo_id}_{session.filename}"

        with open(dest, "wb") as out:
            for chunk_file in chunk_files:
                out.write(chunk_file.read_bytes())

        # Validate assembled file
        content = dest.read_bytes()
        content_type = self._validate_magic_bytes(content)
        session.content_type = content_type

        # Cleanup chunks
        shutil.rmtree(session_dir, ignore_errors=True)

        session.completed = True
        session.photo_id = photo_id

        logger.info(
            "resumable_upload_completed",
            session_id=session.session_id,
            photo_id=photo_id,
            filename=session.filename,
            size_bytes=session.total_size,
        )

    def _validate_size(self, size: int) -> None:
        max_bytes = settings.upload.max_file_size_mb * 1024 * 1024
        if size > max_bytes:
            raise AppError(
                code=ErrorCode.UPLOAD_SIZE_EXCEEDED,
                message=f"File size {size} exceeds max {settings.upload.max_file_size_mb}MB",
            )

    def _validate_content_type(self, content_type: str) -> None:
        if content_type not in settings.upload.accepted_types:
            raise AppError(
                code=ErrorCode.UNSUPPORTED_IMAGE_FORMAT,
                message=f"Content type {content_type} not supported. "
                f"Accepted: {settings.upload.accepted_types}",
            )

    def _validate_magic_bytes(self, content: bytes) -> str:
        """Check file magic bytes match a supported image format."""
        for magic, mime in _MAGIC_BYTES.items():
            if content[: len(magic)] == magic:
                return mime
        raise AppError(
            code=ErrorCode.UNSUPPORTED_IMAGE_FORMAT,
            message="File content does not match any supported image format",
        )

    def _safe_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        name = Path(filename).name
        # Remove any remaining dangerous characters
        safe = "".join(c for c in name if c.isalnum() or c in ".-_")
        return safe or f"upload_{hashlib.md5(filename.encode()).hexdigest()[:8]}"

    def _extract_metadata_safe(self, path: Path, photo_id: str) -> ImageMetadata | None:
        """Extract EXIF metadata, returning None on failure or missing deps."""
        try:
            from src.ingest.metadata import extract_metadata

            return extract_metadata(path, self._upload_dir)
        except ImportError:
            logger.debug("metadata_extraction_skipped", reason="PIL not installed")
            return None
        except Exception:
            logger.warning("metadata_extraction_failed", photo_id=photo_id, path=str(path))
            return None

    def close(self) -> None:
        """Cleanup any pending sessions."""
        self._sessions.clear()
