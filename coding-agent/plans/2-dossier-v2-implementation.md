# Implementation Plan: Dossier v2 — The Needle in a Haystack

**Date**: 2026-03-06
**Source requirements**: `docs/requirements/project_requirements_v2.md`, `docs/requirements/common_requirements.md`, `docs/requirements/documentation_requirements.md`
**Status**: Complete — All phases implemented. Phase 1 deferred (no restructuring needed). Phase 16.1 (vLLM install on 7810) deferred as manual prerequisite.

---

## Overview

Implement the Dossier v2 system: given a reference photo of a human or pet, retrieve all matching photos from a ~1M image corpus and generate a multi-day timeline narrative (dossier). The system follows an API-first architecture with a React SPA frontend (v1) designed for future mobile app support (v2).

The existing codebase provides: FastAPI app factory, layered config, structured logging, error handling, admin console, and test infrastructure. All new work builds on these foundations.

---

## Phase 1: Project Restructuring & Configuration

Restructure the project for the decoupled backend/web architecture and extend configuration for Dossier-specific settings.

### 1.1 Project Structure Migration
- [x] Move existing `main.py`, `src/`, `configs/`, `scripts/`, `tests/` under a `backend/` directory
- [x] Create `web/` directory with React SPA scaffolding (Vite + React + TypeScript + Tailwind)
- [x] Create `mobile/` placeholder directory with README
- [x] Update all import paths and script references for the new structure
- [x] Update `CLAUDE.md`, `pyproject.toml`, and CI config for new paths
- [x] Verify all existing tests pass after restructure

### 1.2 Configuration Extensions
- [x] Add `CorpusSettings` to `config.py`: `corpus_dir`, `supported_formats`, `max_image_size_mb`
- [x] Add `IndexSettings`: `faiss_index_path`, `metadata_db_path`, `human_similarity_threshold`, `pet_similarity_threshold`, `default_top_k`
- [x] Add `DetectionSettings`: `human_model` (insightface/deepface), `pet_model` (yolov8/dinov2), `min_face_confidence`, `min_pet_confidence`
- [x] Add `NarrativeSettings`: `vlm_model`, `llm_model`, `llm_api_key` (env-only), `max_tokens`, `temperature`
- [x] Add `JobSettings`: `max_concurrent_jobs`, `job_timeout_seconds`, `result_ttl_seconds`
- [x] Add per-environment YAML configs (`dev.yaml`, `staging.yaml`, `production.yaml`)
- [x] Add new env vars to `.env.example` with comments on separate lines
- [x] Write unit tests for config validation (fast-fail on invalid corpus_dir, missing GPU settings)

### 1.3 Dependency Setup
- [x] Add ML dependencies to `pyproject.toml` under `[project.optional-dependencies.ml]`: `insightface`, `onnxruntime-gpu`, `faiss-gpu` (or `faiss-cpu`), `ultralytics` (YOLOv8), `transformers`, `Pillow`, `piexif`, `geopy`
- [x] Add narrative dependencies: `anthropic` (Claude API), or `vllm`/`transformers` for local LLM
- [x] Add web dependencies: create `web/package.json` with React, Tailwind, OpenAPI codegen
- [x] Create `scripts/download_models.sh` for downloading face detection and embedding model weights
- [x] Update `.gitignore` for model weights, ONNX files, FAISS index files, corpus data (REQ-SEC-009)
- [x] Run `uv sync --extra dev --extra ml` and verify installation

**Acceptance criteria**: Project builds, existing tests pass, new config fields load correctly, models downloadable via script.

---

## Phase 2: Data Layer — EXIF Extraction & Metadata Store

Build the corpus scanner and metadata extraction pipeline.

### 2.1 Corpus Scanner
- [x] Create `src/ingest/scanner.py`: recursive directory walker supporting JPEG, PNG, HEIC
- [x] Support configurable file extensions via `settings.corpus.supported_formats`
- [x] Yield `ImageFile` pydantic models: `path`, `format`, `size_bytes`, `discovered_at`
- [x] Skip unreadable/corrupt files with structured logging (REQ-LOG-001)
- [x] Support incremental scanning: track processed files in metadata DB, skip already-indexed
- [x] Write unit tests with fixture directory containing valid/corrupt/mixed images

### 2.2 EXIF Metadata Extraction
- [x] Create `src/ingest/metadata.py`: extract EXIF from images using `Pillow` + `piexif`
- [x] Extract: datetime_original, gps_latitude, gps_longitude, orientation, camera_make, camera_model
- [x] Handle HEIC format (use `pillow-heif` or convert to JPEG)
- [x] Create `ImageMetadata` pydantic model with all extracted fields + `has_gps`, `has_timestamp` flags
- [x] Handle missing EXIF gracefully: return model with None fields, log warning
- [x] Normalize GPS coordinates to decimal degrees
- [x] Handle timezone extraction from GPS data
- [x] Write unit tests with real EXIF-tagged test images and stripped-EXIF images

### 2.3 Metadata Store
- [x] Create `src/ingest/store.py`: SQLite-backed metadata store
- [x] Schema: `images` table (id, path, format, size, indexed_at) + `metadata` table (image_id, timestamp, lat, lng, camera, orientation)
- [x] Schema: `faces` table (id, image_id, subject_type, bbox_x, bbox_y, bbox_w, bbox_h, embedding_id, confidence)
- [x] CRUD operations: `add_image`, `get_image`, `list_images`, `search_by_date_range`, `search_by_location`
- [x] Support bulk inserts for indexing performance
- [x] Write unit tests for all CRUD operations

### 2.4 Reverse Geocoding
- [x] Create `src/ingest/geocoder.py`: GPS coordinates to human-readable location
- [x] Use `geopy` with Nominatim (offline) or a local geocoding database
- [x] Cache results with TTL to avoid re-geocoding same coordinates (REQ-ERR-004)
- [x] Return `LocationInfo` pydantic model: `neighborhood`, `city`, `state`, `country`, `venue_type`
- [x] Handle missing/invalid GPS gracefully
- [x] Write unit tests with known coordinates

**Acceptance criteria**: Can scan a directory, extract EXIF from all supported formats, store metadata in SQLite, reverse-geocode GPS coordinates. All operations logged with structlog.

---

## Phase 3: Human Face Detection & Embedding

### 3.1 Human Face Detector
- [x] Create `src/embeddings/base.py`: abstract `FaceDetector` and `FaceEmbedder` protocols
- [x] Define `DetectedFace` pydantic model: `bbox`, `confidence`, `subject_type`, `landmarks`, `aligned_image`
- [x] Create `src/embeddings/human_detector.py`: `InsightFaceDetector` implementing `FaceDetector`
- [x] Use RetinaFace via `insightface` for detection + alignment
- [x] Support configurable confidence threshold from `settings.detection.min_face_confidence`
- [x] Handle images with 0, 1, or multiple faces
- [x] Write unit tests with fixture images (faces, no faces, multiple faces)

### 3.2 Human Face Embedder
- [x] Create `src/embeddings/human_embedder.py`: `ArcFaceEmbedder` implementing `FaceEmbedder`
- [x] Compute 512-dim normalized face embeddings via `insightface` ArcFace
- [x] Accept aligned face crops from detector
- [x] Return `FaceEmbedding` model: `vector` (numpy), `model_name`, `model_version`
- [x] Support GPU acceleration (detect available device)
- [x] Write unit tests verifying embedding dimensions, normalization, and determinism

### 3.3 Mock Backends for Testing
- [x] Create `src/embeddings/mock_detector.py`: returns canned detections from fixture data
- [x] Create `src/embeddings/mock_embedder.py`: returns random normalized vectors
- [x] Register via `settings.detection.human_model = "mock"` for test isolation (REQ-TST-051)
- [x] Write tests verifying mock/real switching via config

**Acceptance criteria**: Given an image, detect all human faces, align them, compute embeddings. Works with GPU and CPU. Mock backend for testing without ML models.

---

## Phase 4: Pet Face Detection & Embedding

### 4.1 Pet Face Detector
- [x] Create `src/embeddings/pet_detector.py`: `PetFaceDetector` implementing `FaceDetector`
- [x] Use fine-tuned YOLOv8 for pet face/body detection (or fallback to general object detection + filtering)
- [x] Support cats, dogs as primary species; extensible to other pets
- [x] Handle pet-specific challenges: variable poses, fur patterns, partial occlusion
- [x] Tag detections with `subject_type = "pet"`
- [x] Write unit tests with pet fixture images

### 4.2 Pet Face Embedder
- [x] Create `src/embeddings/pet_embedder.py`: `PetEmbedder` implementing `FaceEmbedder`
- [x] Use DINOv2 for general visual similarity embeddings (robust to pose/angle variation)
- [x] Alternative: SigLIP-2 for multimodal comparison capability
- [x] Normalize embeddings to unit sphere for cosine similarity
- [x] Write unit tests verifying embedding dimensions and normalization

### 4.3 Unified Detection Pipeline
- [x] Create `src/embeddings/pipeline.py`: runs both human and pet detectors on each image
- [x] Return combined list of `DetectedFace` objects, each tagged with `subject_type`
- [x] Support configurable detector selection via settings
- [x] Log detection counts per type (REQ-LOG-001)
- [x] Write integration test: image with human + pet -> both detected and tagged correctly

**Acceptance criteria**: Given an image, detect both human and pet faces, compute type-specific embeddings. Unified pipeline handles mixed-subject images.

---

## Phase 5: Vector Index Construction & Search

### 5.1 FAISS Index Manager
- [x] Create `src/index/manager.py`: `IndexManager` class
- [x] Build separate FAISS indices for human and pet embeddings (prevent cross-contamination)
- [x] Support `IndexFlatIP` for exact search (development) and `IndexIVFFlat` for approximate search (production, ~1M scale)
- [x] Store mapping: FAISS internal ID -> `face_id` in metadata DB
- [x] Support incremental additions without full rebuild
- [x] Persist indices to disk (`settings.index.faiss_index_path`)
- [x] Log index stats: total vectors, index type, memory usage (REQ-LOG-001)
- [x] Write unit tests for add, search, persist, reload

### 5.2 Search Interface
- [x] Create `src/index/search.py`: `search_index(query_vector, k, threshold, subject_type) -> list[Match]`
- [x] `Match` pydantic model: `face_id`, `image_id`, `image_path`, `similarity_score`, `subject_type`, `bbox`, `metadata`
- [x] Filter by `subject_type` before search (query only the correct index)
- [x] Apply similarity threshold post-search
- [x] Support configurable top-k from `settings.index.default_top_k`
- [x] Write unit tests with synthetic embeddings and known nearest neighbors

### 5.3 Batch Indexing Pipeline
- [x] Create `src/index/batch.py`: orchestrates scan -> detect -> embed -> index for full corpus
- [x] Support resumable processing (checkpoint after each batch of N images)
- [x] Progress logging: images processed, faces found (human/pet), time elapsed, ETA
- [x] Error handling: skip failed images, log errors, continue (REQ-ERR-002)
- [x] Create `scripts/index_corpus.sh`: wrapper script for batch indexing
- [x] Write integration test on small fixture corpus

**Acceptance criteria**: Build FAISS indices from corpus, search by type-filtered query, resume interrupted indexing. Index ~1M images in hours on GPU.

---

## Phase 6: Reference Photo Query API

### 6.1 Detection Endpoint
- [x] Create `POST /api/v1/detect` endpoint
- [x] Accept multipart image upload
- [x] Run both human and pet detectors
- [x] Return: list of detected faces with bounding boxes, types, confidence scores
- [x] Return image dimensions for UI overlay rendering
- [x] Response schema: `DetectionResponse` pydantic model
- [x] Write integration tests

### 6.2 Query Endpoint
- [x] Create `POST /api/v1/query` endpoint
- [x] Accept: image file, `subject_type`, optional `face_bbox`, `threshold`, `top_k`, `date_from`, `date_to`
- [x] If `face_bbox` provided: crop face from image at those coordinates
- [x] Embed the face using type-appropriate embedder
- [x] Search the type-filtered FAISS index
- [x] Enrich results with metadata from SQLite store
- [x] For async (large corpus): return job ID immediately, process in background
- [x] For sync (small corpus): return results directly
- [x] Response schema: `QueryResponse` with `session_id` and paginated `results`
- [x] Write integration tests for both sync and async paths

### 6.3 Results Endpoint
- [x] Create `GET /api/v1/query/{session_id}/results` endpoint
- [x] Cursor-based pagination: `?cursor=xxx&limit=20`
- [x] Return: image URLs (via `/media/`), similarity scores, metadata, bounding boxes
- [x] Write integration tests for pagination

### 6.4 Media Serving
- [x] Create `GET /api/v1/media/{path}` endpoint
- [x] Serve images from corpus directory by relative path
- [x] Validate path stays within `settings.corpus.corpus_dir` (prevent traversal, REQ-SEC-004)
- [x] Support optional query param `?size=thumb` for thumbnail generation
- [x] Cache thumbnails on disk
- [x] Write security tests for path traversal attempts

**Acceptance criteria**: Upload reference photo, get detected faces, run type-filtered retrieval, paginate results. Images served via URL.

---

## Phase 7: Timeline Construction

### 7.1 Timeline Builder
- [x] Create `src/narrative/timeline.py`: `build_timeline(matches: list[Match]) -> Timeline`
- [x] `Timeline` model: `date_range`, `total_days`, `active_days`, `entries: list[TimelineEntry]`
- [x] `TimelineEntry`: `date`, `time`, `location`, `image_path`, `image_url`, `confidence`, `scene_label`
- [x] Sort by timestamp; group by calendar day
- [x] Handle timezone normalization from GPS coordinates
- [x] Handle missing timestamps: infer from GPS proximity or leave unplaced
- [x] Write unit tests with synthetic timeline data

### 7.2 Day Grouping
- [x] Create `src/narrative/grouping.py`: `group_by_day(timeline) -> dict[date, list[TimelineEntry]]`
- [x] Within each day, cluster photos into "scenes" (< 30 min gap = same scene)
- [x] Label scenes with time-of-day context: "morning", "midday", "afternoon", "evening", "night"
- [x] Detect and flag multi-day gaps
- [x] Write unit tests

### 7.3 Pattern Detection
- [x] Create `src/narrative/patterns.py`: `detect_patterns(day_groups) -> list[Pattern]`
- [x] `Pattern` model: `pattern_type` (recurring_location, daily_routine, weekly_pattern), `description`, `confidence`, `evidence`
- [x] Detect recurring locations (same GPS cluster across multiple days)
- [x] Detect time-based routines (similar times on multiple days)
- [x] Write unit tests with multi-day fixture data containing known patterns

**Acceptance criteria**: Retrieved photos ordered chronologically, grouped by day, with detected cross-day patterns. Handles missing metadata gracefully.

---

## Phase 8: Dossier Narrative Generation

### 8.1 Photo Description (VLM)
- [x] Create `src/narrative/describer.py`: `describe_photo(image, metadata, subject_type) -> str`
- [x] Use Qwen-2.5-VL (or LLaVA) to describe visual content of each photo
- [x] Prompt template: include subject type context (human vs. pet), metadata hints (time, location)
- [x] Set explicit `max_tokens` on every call (REQ-ERR-007)
- [x] Handle VLM errors gracefully: fallback to metadata-only description
- [x] Log prompt, response, latency, token usage (REQ-LOG-004, REQ-LOG-005)
- [x] Write unit tests with mock VLM

### 8.2 Dossier Generator (LLM)
- [x] Create `src/narrative/generator.py`: `generate_dossier(descriptions, timeline, subject_type) -> Dossier`
- [x] `Dossier` model: `executive_summary`, `date_range`, `subject_type`, `days: list[DossierDay]`, `patterns: list[Pattern]`, `confidence_notes`
- [x] `DossierDay`: `date`, `entries: list[DossierEntry]`, `day_summary`
- [x] `DossierEntry`: `time`, `location`, `description`, `image_url`, `confidence`
- [x] Prompt template for LLM:
  - Input: ordered photo descriptions with timestamps, locations, patterns
  - Output format: structured JSON matching `Dossier` model
  - Subject-type-specific language (human vs. pet)
  - Uncertainty language for low-confidence entries
- [x] Support streaming output for long dossiers
- [x] Set explicit `max_tokens` (REQ-ERR-007)
- [x] Log full prompt and response at DEBUG level only (REQ-LOG-009)
- [x] Write unit tests with mock LLM
- [x] Write integration tests with real LLM (separate test category)

### 8.3 Dossier API Endpoints
- [x] Create `POST /api/v1/dossier` endpoint: generate dossier from retrieval session
- [x] Returns job ID for async generation
- [x] Create `GET /api/v1/dossier/{session_id}` endpoint: retrieve generated dossier
- [x] Support `?format=json` (default) and `?format=markdown`
- [x] Write integration tests

**Acceptance criteria**: Photos described by VLM, narrative generated by LLM, structured as multi-day dossier with executive summary, per-day entries, and cross-day patterns. Subject-type-appropriate language.

---

## Phase 9: Async Job System

### 9.1 Job Queue
- [x] Create `src/jobs/manager.py`: in-memory job queue with background workers
- [x] `Job` model: `id`, `type` (index, query, dossier), `status` (pending, running, completed, failed), `progress`, `result`, `error`, `created_at`, `updated_at`
- [x] Support configurable max concurrent jobs from `settings.jobs.max_concurrent_jobs`
- [x] Job result TTL: auto-cleanup after `settings.jobs.result_ttl_seconds`
- [x] Write unit tests

### 9.2 Job API Endpoints
- [x] Create `GET /api/v1/jobs/{job_id}` endpoint: job status and progress (polling)
- [x] Create `GET /api/v1/jobs/{job_id}/stream` endpoint: SSE stream for real-time progress
- [x] Write integration tests for both polling and SSE

### 9.3 Wire Existing Endpoints to Job System
- [x] Connect `POST /query` to job queue for large corpus queries
- [x] Connect `POST /dossier` to job queue for narrative generation
- [x] Add progress callbacks to batch indexing pipeline
- [x] Write integration tests for async query -> poll -> results flow

**Acceptance criteria**: Long-running operations return job ID immediately. Clients can poll or stream progress. Jobs auto-cleanup after TTL.

---

## Phase 10: Ground-Truth Evaluation

### 10.1 Manifest Format
- [x] Define ground-truth manifest schema: JSON with `subjects: [{id, name, subject_type, reference_photo, photos: [filename]}]`
- [x] Create `src/evaluation/manifest.py`: load and validate manifest files
- [x] Write unit tests

### 10.2 Evaluation Runner
- [x] Create `src/evaluation/runner.py`: `evaluate(manifest, index_manager) -> EvaluationReport`
- [x] For each subject: run retrieval using reference photo, compare against ground-truth photo list
- [x] Compute per-subject: precision, recall, F1
- [x] Compute aggregates: overall, human-only, pet-only
- [x] Identify false positives and false negatives with image paths
- [x] Detect cross-type confusion (human detected as pet, vice versa)
- [x] Write unit tests with synthetic manifest and mock index

### 10.3 Evaluation API Endpoints
- [x] Create `POST /api/v1/evaluate` endpoint: run evaluation for a subject
- [x] Create `GET /api/v1/evaluate/summary` endpoint: aggregate evaluation results
- [x] Write integration tests

### 10.4 Evaluation Script
- [x] Create `scripts/evaluate_all.sh`: batch evaluation across all subjects in manifest
- [x] Output: per-subject report + aggregate summary (JSON + human-readable)
- [x] Update `docs/app_cheatsheet.md` with evaluation commands

**Acceptance criteria**: Run evaluation against ground-truth manifest. Per-subject and aggregate precision/recall/F1. Separate human vs. pet metrics. Human recall >= 80%, pet recall >= 70%.

---

## Phase 11: Web Frontend (React SPA)

### 11.1 Project Setup
- [x] Initialize Vite + React + TypeScript project in `web/`
- [x] Configure Tailwind CSS
- [x] Generate typed API client from backend OpenAPI schema
- [x] Configure dev proxy to backend API
- [x] Create base layout, routing, error boundaries

### 11.2 Reference Photo Upload & Auto-Detection
- [x] Build `UploadPage` component: drag-drop zone + file browser
- [x] On upload: call `POST /detect`, render bounding box overlay on image
- [x] Color-code boxes: blue (human), green (pet)
- [x] Show confidence score on each box
- [x] Click-to-select face: highlight selected, dim others
- [x] Type override toggle on bounding box
- [x] Manual bounding box drawing for no-detection fallback
- [x] "Search" button triggers `POST /query`

### 11.3 Results View
- [x] Build `ResultsPage` component: photo grid with lazy loading
- [x] Show similarity scores, timestamps, locations, subject type badges
- [x] Cursor-based pagination (infinite scroll)
- [x] Date range filter controls
- [x] Progress indicator for async queries (poll `GET /jobs/{id}`)

### 11.4 Timeline View
- [x] Build `TimelinePage` component: chronological photo strip grouped by day
- [x] Calendar heat map showing photo density per day
- [x] Day-level drill-down
- [x] Gap annotations ("no photos March 8-10")

### 11.5 Dossier View
- [x] Build `DossierPage` component: rendered narrative with inline photo thumbnails
- [x] Executive summary section
- [x] Per-day collapsible sections
- [x] Cross-day patterns section
- [x] Confidence indicators (color-coded)
- [x] Download buttons: PDF, Markdown

### 11.6 Evaluation Panel
- [x] Build `EvaluationPanel` component (shown when ground-truth manifest loaded)
- [x] Per-subject precision/recall/F1 table
- [x] Aggregate metrics with human/pet breakdown
- [x] False positive/negative image gallery

### 11.7 Responsive Design
- [x] Ensure all views are functional on mobile screen sizes
- [x] Touch-friendly interactions for face selection
- [x] Collapsible panels for small screens

**Acceptance criteria**: Fully functional web SPA. Upload photo, auto-detect faces, select subject, view results, browse timeline, read dossier, export PDF. Responsive on mobile browsers.

---

## Phase 12: Upload & Photo Contribution API

### 12.1 Standard Upload
- [x] Create `POST /api/v1/photos/upload` endpoint
- [x] Accept multipart form with image + optional metadata JSON
- [x] Extract EXIF server-side; prefer client-provided metadata if present
- [x] Accept JPEG, PNG, HEIC; normalize to JPEG/PNG for processing
- [x] Max file size: 20MB
- [x] Return photo IDs and extracted metadata
- [x] Write integration tests

### 12.2 Resumable Upload (Mobile-Ready)
- [x] Create `POST /api/v1/photos/upload/init` endpoint: initiate upload session
- [x] Create `PATCH /api/v1/photos/upload/{session_id}` endpoint: send chunks with `Content-Range`
- [x] Create `GET /api/v1/photos/upload/{session_id}/status` endpoint: check progress
- [x] Assemble chunks on completion, trigger processing
- [x] Write integration tests for chunked upload flow

**Acceptance criteria**: Photos uploadable via standard multipart or resumable chunks. EXIF preserved. HEIC handled.

---

## Phase 13: Observability & Monitoring

### 13.1 Structured Logging Enhancements
- [x] Add AI-specific fields to all LLM/VLM calls: `model`, `temperature`, `max_tokens`, `latency_ms`, `input_tokens`, `output_tokens` (REQ-LOG-003)
- [x] Add request correlation IDs to all API requests (REQ-LOG-002)
- [x] Separate prompt analytics logs from operational logs (REQ-LOG-007)
- [x] Guard expensive debug logs with level checks (REQ-LOG-010)

### 13.2 Metrics & Health
- [x] Extend `/health` with readiness check (is index loaded? are models ready?) (REQ-RUN-011)
- [x] Create `GET /api/v1/index/stats` endpoint: total images, faces, human count, pet count, index size
- [x] Log retrieval latency, dossier generation latency as metrics
- [x] Track and log job queue depth and processing times

### 13.3 Prompt Logging
- [x] Create dedicated prompt log store (JSONL or SQLite) (REQ-LOG-004)
- [x] Log: prompt text, response text, model, parameters, latency, token counts
- [x] Redact any PII from logged prompts (REQ-LOG-006)
- [x] Configurable: full logging at DEBUG, metadata-only at INFO (REQ-LOG-009)

**Acceptance criteria**: All LLM calls logged with full metadata. Correlation IDs on all requests. Health/readiness endpoints differentiated. Prompt logs in dedicated store.

---

## Phase 14: Security Hardening

### 14.1 Input Validation
- [x] Validate all uploaded files: check magic bytes match declared type (REQ-SEC-002)
- [x] Enforce file size limits server-side
- [x] Sanitize filenames in upload paths
- [x] Path traversal prevention on media serving endpoint (REQ-SEC-004)

### 14.2 LLM Safety
- [x] Implement prompt injection defenses for dossier generation (REQ-SEC-003)
- [x] System prompt isolation: narrative prompts don't include raw user input
- [x] Output validation: check generated dossier for PII leaks, harmful content
- [x] Set explicit `max_tokens` on all LLM calls (REQ-ERR-007)

### 14.3 Rate Limiting
- [x] Add rate limiting to public API endpoints (REQ-SEC-007)
- [x] Configure via settings: requests per minute per IP
- [x] Return `429 Too Many Requests` with `Retry-After` header

### 14.4 Authentication
- [x] Implement JWT-based authentication for API access (stateless, mobile-ready)
- [x] Admin endpoints continue to use `X-Admin-Secret` header
- [x] Write security integration tests

**Acceptance criteria**: All uploads validated. Prompt injection defenses in place. Rate limiting active. JWT auth functional.

---

## Phase 15: Documentation & Finalization

### 15.1 Architecture & Design Docs
- [x] Create `docs/architecture/architecture_overview.md` with C4 diagrams (Mermaid)
- [x] Create `docs/design/design_specification.md` with module interfaces and data models
- [x] Create `docs/design/api_contract.md` with full API specification

### 15.2 Operational Docs
- [x] Create `docs/runbook/deployment_runbook.md` (REQ-DOC-003)
- [x] Create `docs/runbook/model_update_runbook.md`
- [x] Create `docs/runbook/index_rebuild_runbook.md`
- [x] Create participant photo collection guide
- [x] Create pet photo collection guide

### 15.3 README & Cheatsheet
- [x] Write `README.md` from template (REQ-AGT-001)
- [x] Update `docs/app_cheatsheet.md` with all new endpoints, scripts, config vars
- [x] Update `.env.example` with all new variables

### 15.4 Final Quality
- [x] Run `bash scripts/check_all.sh` (lint + typecheck + tests)
- [x] Run security review agent
- [x] Run code simplifier agent
- [x] Verify all acceptance criteria from project_requirements_v2.md

**Acceptance criteria**: All documentation produced per REQ-ADO-001 through REQ-ADO-006. README complete. Cheatsheet current. All quality checks pass.

---

## Phase Dependencies

```
Phase 1 (Structure + Config)
  |
  v
Phase 2 (Data Layer)
  |
  +---> Phase 3 (Human Detection) --+
  |                                  |
  +---> Phase 4 (Pet Detection) ----+
                                     |
                                     v
                              Phase 5 (Index)
                                     |
                                     v
                              Phase 6 (Query API) ---------> Phase 9 (Jobs)
                                     |                            |
                                     v                            v
                              Phase 7 (Timeline) ---------> Phase 11 (Web UI)
                                     |
                                     v
                              Phase 8 (Narrative)
                                     |
                              Phase 10 (Evaluation)
                              Phase 12 (Upload API)
                              Phase 13 (Observability)
                              Phase 14 (Security)
                              Phase 15 (Documentation)

Phase 8 (Narrative) ---------> Phase 16 (VLM + Scripts + Env)
```

Phases 3 and 4 can run in parallel. Phases 10, 12, 13, 14 can run in parallel after Phase 6. Phase 16 can run independently. Phase 15 runs last.

---

## Phase 16: VLM Service, Operational Scripts & Environment Config

Deploy the VLM inference service on the 7810 node's second GPU, create missing operational scripts, and update the environment template.

### 16.1 vLLM VLM Service on 7810 GPU 1
- [x] Install vLLM on 7810 node with Qwen2.5-VL-7B-Instruct support
- [x] Create `dossier-inference/start_vlm.sh` script on 7810: starts vLLM on GPU 1 (`CUDA_VISIBLE_DEVICES=1`), port 8011, OpenAI-compatible API
- [x] Configure model loading: `Qwen/Qwen2.5-VL-7B-Instruct` (or AWQ quantized variant if VRAM constrained on 12GB 3060)
- [x] Add `--max-model-len` and `--gpu-memory-utilization` flags tuned for 12GB VRAM
- [x] Create `scripts/start_vlm.sh` on this machine: SSH wrapper to start/stop VLM on 7810 (mirrors `scripts/start_inference.sh` pattern)
- [x] Poll for readiness via `http://100.111.31.125:8011/v1/models` endpoint
- [x] Verify end-to-end: `PhotoDescriber.describe()` → VLM on 7810 → description returned
- [x] Update `scripts/start_inference.sh` to optionally start both services (detection + VLM)
- [x] Update `docs/app_cheatsheet.md` with VLM service commands

### 16.2 Operational Scripts
- [x] Create `scripts/download_models.sh`: download InsightFace, YOLOv8, DINOv2 weights to 7810; download Qwen2.5-VL-7B and Qwen2.5-14B-Instruct-AWQ model files
- [x] Create `scripts/evaluate_all.sh`: run evaluation across all subjects in a ground-truth manifest, output per-subject + aggregate JSON report
- [x] Make both scripts executable and add project root resolution (`SCRIPT_DIR` / `PROJECT_ROOT` pattern)
- [x] Update `docs/app_cheatsheet.md` with new script documentation

### 16.3 Environment Configuration Template
- [x] Update `.env.example` with all Dossier-specific variables (requires disabling file protection hook or user override):
  - `CORPUS__CORPUS_DIR`, `CORPUS__SUPPORTED_FORMATS`, `CORPUS__MAX_IMAGE_SIZE_MB`
  - `INFERENCE__BASE_URL`, `INFERENCE__TIMEOUT`
  - `INDEX__FAISS_INDEX_DIR`, `INDEX__METADATA_DB_PATH`, `INDEX__HUMAN_SIMILARITY_THRESHOLD`, `INDEX__PET_SIMILARITY_THRESHOLD`
  - `NARRATIVE__LLM_BASE_URL`, `NARRATIVE__LLM_MODEL`, `NARRATIVE__VLM_BASE_URL`, `NARRATIVE__VLM_MODEL`, `NARRATIVE__MAX_TOKENS`, `NARRATIVE__TEMPERATURE`
  - `JOBS__MAX_CONCURRENT_JOBS`, `JOBS__RESULT_TTL_SECONDS`
  - `UPLOAD__UPLOAD_DIR`, `UPLOAD__MAX_FILE_SIZE_MB`
- [x] Add descriptive comments on separate lines above each variable (REQ-CFG-006)
- [x] Verify `settings` loads correctly from `.env.example` defaults

**Acceptance criteria**: VLM service running on 7810 GPU 1, photo descriptions working end-to-end. All operational scripts created and documented. `.env.example` has every config variable with comments.

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pet face detection accuracy significantly lower than human | Reduced pet retrieval recall | Fallback to DINOv2 whole-body embeddings instead of face-only |
| ~1M image indexing exceeds available GPU memory | Cannot build index | Use batched indexing with disk-backed FAISS; consider IVF index with training subset |
| VLM/LLM latency makes dossier generation slow | Poor UX | Async job system with streaming; cache photo descriptions |
| HEIC format support inconsistent across libraries | Some photos unprocessable | Convert HEIC to JPEG at ingest time; log conversion failures |
| Reverse geocoding rate limits (Nominatim) | Slow metadata enrichment | Use local geocoding database or cache aggressively |
| Cross-type confusion (human <-> pet) | False positives | Separate indices per type; never cross-search |

---

## Estimated Effort by Phase

| Phase | Size | Notes |
|-------|------|-------|
| 1. Restructure + Config | Medium | One-time restructuring cost |
| 2. Data Layer | Medium | EXIF parsing + SQLite store |
| 3. Human Detection | Medium | Integrating insightface |
| 4. Pet Detection | Large | Less mature tooling; more R&D |
| 5. Index | Medium | FAISS is well-documented |
| 6. Query API | Medium | Standard FastAPI work |
| 7. Timeline | Small | Data manipulation, no ML |
| 8. Narrative | Large | VLM + LLM integration, prompt engineering |
| 9. Jobs | Medium | Async patterns |
| 10. Evaluation | Small | Metrics computation |
| 11. Web UI | Large | Full React SPA |
| 12. Upload API | Small | Standard file handling |
| 13. Observability | Medium | Cross-cutting concern |
| 14. Security | Medium | Multiple hardening areas |
| 15. Documentation | Medium | Multiple documents |
| 16. VLM + Scripts + Env | Medium | 7810 GPU 1 setup, 2 scripts, .env.example |
