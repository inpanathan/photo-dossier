"""Unit tests for src/ingest/store.py — MetadataStore."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.ingest.store import MetadataStore
from src.models import BoundingBox, FaceRecord, ImageMetadata, SubjectType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> MetadataStore:
    """Create a MetadataStore backed by a temp SQLite file."""
    db = tmp_path / "test_metadata.db"
    s = MetadataStore(db_path=db)
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image(
    image_id: str = "img001",
    path: str | None = None,
    timestamp: datetime | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> ImageMetadata:
    return ImageMetadata(
        image_id=image_id,
        path=path or f"/photos/{image_id}.jpg",
        format="jpeg",
        size_bytes=512_000,
        timestamp=timestamp,
        latitude=lat,
        longitude=lon,
        has_gps=lat is not None and lon is not None,
        has_timestamp=timestamp is not None,
    )


def _make_face(
    face_id: str = "face001",
    image_id: str = "img001",
    subject_type: SubjectType = SubjectType.HUMAN,
    embedding_index_id: int = 0,
) -> FaceRecord:
    return FaceRecord(
        face_id=face_id,
        image_id=image_id,
        subject_type=subject_type,
        bbox=BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4),
        confidence=0.95,
        embedding_index_id=embedding_index_id,
        model_name="insightface",
    )


# ---------------------------------------------------------------------------
# MetadataStore initialisation
# ---------------------------------------------------------------------------


def test_store_creates_db_file(tmp_path: Path) -> None:
    db = tmp_path / "subdir" / "nested" / "test.db"
    store = MetadataStore(db_path=db)
    store.close()
    assert db.exists()


def test_store_empty_on_creation(store: MetadataStore) -> None:
    assert store.count_images() == 0
    assert store.count_faces() == 0


def test_store_supports_context_manager(tmp_path: Path) -> None:
    db = tmp_path / "ctx.db"
    with MetadataStore(db_path=db) as s:
        assert s.count_images() == 0


# ---------------------------------------------------------------------------
# add_image / get_image_metadata
# ---------------------------------------------------------------------------


def test_add_image_then_count(store: MetadataStore) -> None:
    store.add_image(_make_image("img1"))
    store.commit()
    assert store.count_images() == 1


def test_add_multiple_images(store: MetadataStore) -> None:
    for i in range(5):
        store.add_image(_make_image(f"img{i}"))
    store.commit()
    assert store.count_images() == 5


def test_get_image_metadata_returns_correct_fields(store: MetadataStore) -> None:
    ts = datetime(2024, 6, 15, 10, 30, 0)
    meta = _make_image("img_ts", timestamp=ts, lat=51.5, lon=-0.1)
    store.add_image(meta)
    store.commit()

    result = store.get_image_metadata("img_ts")
    assert result is not None
    assert result.image_id == "img_ts"
    assert result.path == "/photos/img_ts.jpg"
    assert result.format == "jpeg"
    assert result.size_bytes == 512_000
    assert result.timestamp == ts
    assert result.latitude == pytest.approx(51.5)
    assert result.longitude == pytest.approx(-0.1)
    assert result.has_gps is True
    assert result.has_timestamp is True


def test_get_image_metadata_no_gps_no_timestamp(store: MetadataStore) -> None:
    store.add_image(_make_image("img_bare"))
    store.commit()
    result = store.get_image_metadata("img_bare")
    assert result is not None
    assert result.has_gps is False
    assert result.has_timestamp is False
    assert result.timestamp is None
    assert result.latitude is None
    assert result.longitude is None


def test_get_image_metadata_nonexistent_returns_none(store: MetadataStore) -> None:
    result = store.get_image_metadata("does_not_exist")
    assert result is None


def test_add_image_upsert_replaces_existing(store: MetadataStore) -> None:
    store.add_image(_make_image("img_dup", path="/old.jpg"))
    store.commit()
    store.add_image(_make_image("img_dup", path="/new.jpg"))
    store.commit()
    assert store.count_images() == 1
    result = store.get_image_metadata("img_dup")
    assert result is not None
    assert result.path == "/new.jpg"


def test_add_image_with_camera_info(store: MetadataStore) -> None:
    meta = ImageMetadata(
        image_id="cam_img",
        path="/cam.jpg",
        format="jpeg",
        size_bytes=1_000,
        camera_make="Apple",
        camera_model="iPhone 15",
    )
    store.add_image(meta)
    store.commit()
    result = store.get_image_metadata("cam_img")
    assert result is not None
    assert result.camera_make == "Apple"
    assert result.camera_model == "iPhone 15"


# ---------------------------------------------------------------------------
# add_face / count_faces / get_face_by_embedding_id
# ---------------------------------------------------------------------------


def test_add_face_then_count(store: MetadataStore) -> None:
    store.add_image(_make_image("img1"))
    store.add_face(_make_face("face1", "img1"))
    store.commit()
    assert store.count_faces() == 1


def test_count_faces_filtered_by_subject_type(store: MetadataStore) -> None:
    store.add_image(_make_image("i1"))
    store.add_image(_make_image("i2"))
    store.add_face(_make_face("f1", "i1", SubjectType.HUMAN))
    store.add_face(_make_face("f2", "i1", SubjectType.HUMAN))
    store.add_face(_make_face("f3", "i2", SubjectType.PET))
    store.commit()

    assert store.count_faces(SubjectType.HUMAN) == 2
    assert store.count_faces(SubjectType.PET) == 1
    assert store.count_faces() == 3


def test_get_face_by_embedding_id_returns_correct_face(store: MetadataStore) -> None:
    store.add_image(_make_image("img1"))
    face = _make_face("face1", "img1", embedding_index_id=42)
    store.add_face(face)
    store.commit()

    result = store.get_face_by_embedding_id(42, SubjectType.HUMAN)
    assert result is not None
    assert result.face_id == "face1"
    assert result.image_id == "img1"
    assert result.embedding_index_id == 42
    assert result.subject_type == SubjectType.HUMAN


def test_get_face_by_embedding_id_wrong_type_returns_none(store: MetadataStore) -> None:
    store.add_image(_make_image("img1"))
    store.add_face(_make_face("f1", "img1", SubjectType.HUMAN, embedding_index_id=5))
    store.commit()

    result = store.get_face_by_embedding_id(5, SubjectType.PET)
    assert result is None


def test_get_face_by_embedding_id_nonexistent_returns_none(store: MetadataStore) -> None:
    result = store.get_face_by_embedding_id(999, SubjectType.HUMAN)
    assert result is None


def test_get_face_bbox_values_roundtrip(store: MetadataStore) -> None:
    store.add_image(_make_image("img1"))
    face = FaceRecord(
        face_id="f_bbox",
        image_id="img1",
        subject_type=SubjectType.HUMAN,
        bbox=BoundingBox(x=0.15, y=0.25, width=0.35, height=0.45),
        confidence=0.88,
        embedding_index_id=7,
        model_name="insightface",
    )
    store.add_face(face)
    store.commit()

    result = store.get_face_by_embedding_id(7, SubjectType.HUMAN)
    assert result is not None
    assert result.bbox.x == pytest.approx(0.15)
    assert result.bbox.y == pytest.approx(0.25)
    assert result.bbox.width == pytest.approx(0.35)
    assert result.bbox.height == pytest.approx(0.45)
    assert result.confidence == pytest.approx(0.88)


def test_add_face_pet_type(store: MetadataStore) -> None:
    store.add_image(_make_image("img_pet"))
    store.add_face(_make_face("f_pet", "img_pet", SubjectType.PET, embedding_index_id=1))
    store.commit()

    result = store.get_face_by_embedding_id(1, SubjectType.PET)
    assert result is not None
    assert result.subject_type == SubjectType.PET


# ---------------------------------------------------------------------------
# get_indexed_paths
# ---------------------------------------------------------------------------


def test_get_indexed_paths_empty(store: MetadataStore) -> None:
    assert store.get_indexed_paths() == set()


def test_get_indexed_paths_returns_all_paths(store: MetadataStore) -> None:
    store.add_image(_make_image("i1", path="/photos/a.jpg"))
    store.add_image(_make_image("i2", path="/photos/b.jpg"))
    store.commit()

    paths = store.get_indexed_paths()
    assert paths == {"/photos/a.jpg", "/photos/b.jpg"}


def test_get_indexed_paths_is_a_set(store: MetadataStore) -> None:
    store.add_image(_make_image("i1", path="/photos/x.jpg"))
    store.commit()
    result = store.get_indexed_paths()
    assert isinstance(result, set)


# ---------------------------------------------------------------------------
# commit / transactions
# ---------------------------------------------------------------------------


def test_uncommitted_changes_not_visible_across_connections(tmp_path: Path) -> None:
    """Changes must be committed before another connection can see them."""
    db = tmp_path / "txn.db"

    store1 = MetadataStore(db_path=db)
    store1.add_image(_make_image("img1"))
    # Do NOT commit

    store2 = MetadataStore(db_path=db)
    assert store2.count_images() == 0
    store1.close()
    store2.close()


def test_committed_changes_visible_across_connections(tmp_path: Path) -> None:
    db = tmp_path / "txn.db"

    store1 = MetadataStore(db_path=db)
    store1.add_image(_make_image("img1"))
    store1.commit()
    store1.close()

    store2 = MetadataStore(db_path=db)
    assert store2.count_images() == 1
    store2.close()
