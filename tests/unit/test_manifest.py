"""Unit tests for src/evaluation/manifest.py — load_manifest()."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.manifest import load_manifest
from src.models import SubjectManifest, SubjectType
from src.utils.errors import AppError, ErrorCode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data))
    return path


def _valid_subject(
    subject_id: str = "s001",
    name: str = "Alice",
    subject_type: str = "human",
    reference_photo: str = "ref/alice.jpg",
    photos: list[str] | None = None,
) -> dict:
    return {
        "id": subject_id,
        "name": name,
        "subject_type": subject_type,
        "reference_photo": reference_photo,
        "photos": photos if photos is not None else ["img1.jpg", "img2.jpg"],
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_load_manifest_returns_list_of_subject_manifests(tmp_path: Path) -> None:
    manifest_file = _write_manifest(
        tmp_path / "manifest.json",
        {"subjects": [_valid_subject()]},
    )
    result = load_manifest(manifest_file)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], SubjectManifest)


def test_load_manifest_human_subject(tmp_path: Path) -> None:
    manifest_file = _write_manifest(
        tmp_path / "m.json",
        {"subjects": [_valid_subject(subject_type="human")]},
    )
    subjects = load_manifest(manifest_file)
    assert subjects[0].subject_type == SubjectType.HUMAN


def test_load_manifest_pet_subject(tmp_path: Path) -> None:
    manifest_file = _write_manifest(
        tmp_path / "m.json",
        {"subjects": [_valid_subject(subject_id="p01", subject_type="pet", name="Rex")]},
    )
    subjects = load_manifest(manifest_file)
    assert subjects[0].subject_type == SubjectType.PET


def test_load_manifest_multiple_subjects(tmp_path: Path) -> None:
    data = {
        "subjects": [
            _valid_subject("s001", "Alice", "human"),
            _valid_subject("s002", "Bob", "human"),
            _valid_subject("s003", "Fido", "pet"),
        ]
    }
    manifest_file = _write_manifest(tmp_path / "m.json", data)
    subjects = load_manifest(manifest_file)
    assert len(subjects) == 3


def test_load_manifest_fields_are_populated(tmp_path: Path) -> None:
    photos = ["photo1.jpg", "photo2.jpg", "photo3.jpg"]
    data = {"subjects": [_valid_subject(subject_id="s99", name="Eve", photos=photos)]}
    manifest_file = _write_manifest(tmp_path / "m.json", data)
    subject = load_manifest(manifest_file)[0]
    assert subject.subject_id == "s99"
    assert subject.name == "Eve"
    assert subject.reference_photo == "ref/alice.jpg"
    assert subject.photos == photos


def test_load_manifest_accepts_str_path(tmp_path: Path) -> None:
    manifest_file = _write_manifest(tmp_path / "m.json", {"subjects": [_valid_subject()]})
    result = load_manifest(str(manifest_file))
    assert len(result) == 1


def test_load_manifest_accepts_path_object(tmp_path: Path) -> None:
    manifest_file = _write_manifest(tmp_path / "m.json", {"subjects": [_valid_subject()]})
    result = load_manifest(manifest_file)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Error: file not found
# ---------------------------------------------------------------------------


def test_load_manifest_missing_file_raises_app_error(tmp_path: Path) -> None:
    with pytest.raises(AppError) as exc_info:
        load_manifest(tmp_path / "nonexistent.json")
    assert exc_info.value.code == ErrorCode.MANIFEST_INVALID
    assert "not found" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Error: invalid JSON
# ---------------------------------------------------------------------------


def test_load_manifest_invalid_json_raises_app_error(tmp_path: Path) -> None:
    manifest_file = tmp_path / "bad.json"
    manifest_file.write_text("{this is not valid json{{}")
    with pytest.raises(AppError) as exc_info:
        load_manifest(manifest_file)
    assert exc_info.value.code == ErrorCode.MANIFEST_INVALID
    assert "Invalid JSON" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Error: empty subjects list
# ---------------------------------------------------------------------------


def test_load_manifest_empty_subjects_raises_app_error(tmp_path: Path) -> None:
    manifest_file = _write_manifest(tmp_path / "empty.json", {"subjects": []})
    with pytest.raises(AppError) as exc_info:
        load_manifest(manifest_file)
    assert exc_info.value.code == ErrorCode.MANIFEST_INVALID
    assert "no subjects" in str(exc_info.value).lower()


def test_load_manifest_missing_subjects_key_raises_app_error(tmp_path: Path) -> None:
    manifest_file = _write_manifest(tmp_path / "no_subjects.json", {"data": []})
    with pytest.raises(AppError) as exc_info:
        load_manifest(manifest_file)
    assert exc_info.value.code == ErrorCode.MANIFEST_INVALID


# ---------------------------------------------------------------------------
# Error: malformed subject entries
# ---------------------------------------------------------------------------


def test_load_manifest_missing_id_field_raises_app_error(tmp_path: Path) -> None:
    bad_subject = {
        "name": "Alice",
        "subject_type": "human",
        "reference_photo": "ref.jpg",
        "photos": ["a.jpg"],
    }
    manifest_file = _write_manifest(tmp_path / "m.json", {"subjects": [bad_subject]})
    with pytest.raises(AppError) as exc_info:
        load_manifest(manifest_file)
    assert exc_info.value.code == ErrorCode.MANIFEST_INVALID
    assert "index 0" in str(exc_info.value)


def test_load_manifest_invalid_subject_type_raises_app_error(tmp_path: Path) -> None:
    bad_subject = _valid_subject(subject_type="robot")
    manifest_file = _write_manifest(tmp_path / "m.json", {"subjects": [bad_subject]})
    with pytest.raises(AppError) as exc_info:
        load_manifest(manifest_file)
    assert exc_info.value.code == ErrorCode.MANIFEST_INVALID


def test_load_manifest_second_invalid_entry_reports_correct_index(tmp_path: Path) -> None:
    valid = _valid_subject("s001")
    invalid = {"name": "Broken"}  # missing required fields
    manifest_file = _write_manifest(tmp_path / "m.json", {"subjects": [valid, invalid]})
    with pytest.raises(AppError) as exc_info:
        load_manifest(manifest_file)
    assert "index 1" in str(exc_info.value)


def test_load_manifest_missing_photos_field_raises_app_error(tmp_path: Path) -> None:
    bad_subject = {
        "id": "s001",
        "name": "Alice",
        "subject_type": "human",
        "reference_photo": "ref.jpg",
        # "photos" is missing
    }
    manifest_file = _write_manifest(tmp_path / "m.json", {"subjects": [bad_subject]})
    with pytest.raises(AppError) as exc_info:
        load_manifest(manifest_file)
    assert exc_info.value.code == ErrorCode.MANIFEST_INVALID
