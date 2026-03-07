"""Ground-truth manifest loader and validator.

Loads JSON manifests defining which photos belong to which subjects
for evaluating retrieval precision and recall.
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from src.models import SubjectManifest, SubjectType
from src.utils.errors import AppError, ErrorCode

logger = structlog.get_logger(__name__)


def load_manifest(manifest_path: str | Path) -> list[SubjectManifest]:
    """Load and validate a ground-truth manifest file.

    Args:
        manifest_path: Path to the JSON manifest file.

    Returns:
        List of validated SubjectManifest objects.

    Raises:
        AppError: If the manifest file is invalid or missing.
    """
    path = Path(manifest_path)
    if not path.exists():
        raise AppError(
            code=ErrorCode.MANIFEST_INVALID,
            message=f"Manifest file not found: {path}",
        )

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise AppError(
            code=ErrorCode.MANIFEST_INVALID,
            message=f"Invalid JSON in manifest: {e}",
            cause=e,
        ) from e

    subjects_data = data.get("subjects", [])
    if not subjects_data:
        raise AppError(
            code=ErrorCode.MANIFEST_INVALID,
            message="Manifest contains no subjects",
        )

    subjects = []
    for i, entry in enumerate(subjects_data):
        try:
            subject = SubjectManifest(
                subject_id=entry["id"],
                name=entry["name"],
                subject_type=SubjectType(entry["subject_type"]),
                reference_photo=entry["reference_photo"],
                photos=entry["photos"],
            )
            subjects.append(subject)
        except (KeyError, ValueError) as e:
            raise AppError(
                code=ErrorCode.MANIFEST_INVALID,
                message=f"Invalid subject entry at index {i}: {e}",
                cause=e,
            ) from e

    logger.info(
        "manifest_loaded",
        path=str(path),
        total_subjects=len(subjects),
        human_subjects=sum(1 for s in subjects if s.subject_type == SubjectType.HUMAN),
        pet_subjects=sum(1 for s in subjects if s.subject_type == SubjectType.PET),
    )

    return subjects
