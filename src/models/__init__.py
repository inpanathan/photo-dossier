"""Core domain models for the Dossier system.

All data structures that cross module boundaries are defined here as
Pydantic models. Internal-only data uses plain dataclasses or dicts.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SubjectType(enum.StrEnum):
    HUMAN = "human"
    PET = "pet"


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DetectedFace(BaseModel):
    bbox: BoundingBox
    confidence: float
    subject_type: SubjectType
    landmarks: list[list[float]] | None = None


class FaceEmbedding(BaseModel):
    vector: list[float]
    model_name: str
    dimensions: int


class DetectionResult(BaseModel):
    image_width: int
    image_height: int
    faces: list[DetectedFace]


class FaceRecord(BaseModel):
    face_id: str
    image_id: str
    subject_type: SubjectType
    bbox: BoundingBox
    confidence: float
    embedding_index_id: int
    model_name: str


class ImageMetadata(BaseModel):
    image_id: str
    path: str
    format: str
    size_bytes: int
    timestamp: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    orientation: int | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    has_gps: bool = False
    has_timestamp: bool = False


class LocationInfo(BaseModel):
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    venue_type: str | None = None
    display_name: str = "Unknown location"


class Match(BaseModel):
    face_id: str
    image_id: str
    image_path: str
    image_url: str = ""
    similarity_score: float
    subject_type: SubjectType
    bbox: BoundingBox
    metadata: ImageMetadata | None = None
    location: LocationInfo | None = None


# ---- Timeline Models ----


class TimelineEntry(BaseModel):
    image_id: str
    image_url: str = ""
    image_path: str = ""
    timestamp: datetime | None = None
    date: str | None = None
    time: str | None = None
    location: LocationInfo | None = None
    confidence: float = 0.0
    scene_label: str | None = None


class Scene(BaseModel):
    start_time: str | None = None
    end_time: str | None = None
    location: LocationInfo | None = None
    entries: list[TimelineEntry] = Field(default_factory=list)
    label: str = ""


class DateGap(BaseModel):
    start_date: str
    end_date: str
    gap_days: int


class DayGroup(BaseModel):
    date: str
    day_label: str
    entries: list[TimelineEntry] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)


class Timeline(BaseModel):
    subject_type: SubjectType
    date_range_start: str | None = None
    date_range_end: str | None = None
    total_days_spanned: int = 0
    active_days: int = 0
    days: list[DayGroup] = Field(default_factory=list)
    gaps: list[DateGap] = Field(default_factory=list)


class Pattern(BaseModel):
    pattern_type: str
    description: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


# ---- Dossier Models ----


class DossierEntry(BaseModel):
    time: str | None = None
    location: str | None = None
    description: str = ""
    image_url: str = ""
    image_path: str = ""
    confidence: float = 0.0
    confidence_label: str = "medium"


class DossierDay(BaseModel):
    date: str
    day_label: str
    day_summary: str = ""
    entries: list[DossierEntry] = Field(default_factory=list)


class Dossier(BaseModel):
    session_id: str
    subject_type: SubjectType
    executive_summary: str = ""
    date_range: str = ""
    total_photos: int = 0
    total_days: int = 0
    days: list[DossierDay] = Field(default_factory=list)
    patterns: list[Pattern] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


# ---- Evaluation Models ----


class SubjectManifest(BaseModel):
    subject_id: str
    name: str
    subject_type: SubjectType
    reference_photo: str
    photos: list[str]


class SubjectEvaluation(BaseModel):
    subject_id: str
    subject_type: SubjectType
    total_ground_truth: int
    retrieved_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    false_positive_images: list[str] = Field(default_factory=list)
    false_negative_images: list[str] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    total_subjects: int = 0
    human_subjects: int = 0
    pet_subjects: int = 0
    aggregate_precision: float = 0.0
    aggregate_recall: float = 0.0
    aggregate_f1: float = 0.0
    human_precision: float = 0.0
    human_recall: float = 0.0
    human_f1: float = 0.0
    pet_precision: float = 0.0
    pet_recall: float = 0.0
    pet_f1: float = 0.0
    per_subject: list[SubjectEvaluation] = Field(default_factory=list)
    cross_type_confusions: int = 0
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


# ---- Job Models ----


class JobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(enum.StrEnum):
    INDEX = "index"
    QUERY = "query"
    DOSSIER = "dossier"
    EVALUATE = "evaluate"


class Job(BaseModel):
    id: str
    type: JobType
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str | None = None
    result: dict | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    completed_at: datetime | None = None
