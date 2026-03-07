# Implementation Plan: Dossier v2 — The Needle in a Haystack

**Date**: 2026-03-06
**Source requirements**: `docs/requirements/project_requirements_v2.md`, `docs/requirements/common_requirements.md`, `docs/requirements/documentation_requirements.md`
**Status**: In progress — Phases 2-10 backend modules + integration tests complete. Phase 1 deferred (no restructuring needed yet). Phase 11+ not started.

---

## Overview

Implement the Dossier v2 system: given a reference photo of a human or pet, retrieve all matching photos from a ~1M image corpus and generate a multi-day timeline narrative (dossier). The system follows an API-first architecture with a React SPA frontend (v1) designed for future mobile app support (v2).

The existing codebase provides: FastAPI app factory, layered config, structured logging, error handling, admin console, and test infrastructure. All new work builds on these foundations.

---

## Phase 1: Project Restructuring & Configuration

Restructure the project for the decoupled backend/web architecture and extend configuration for Dossier-specific settings.

### 1.1 Project Structure Migration
- [ ] Move existing `main.py`, `src/`, `configs/`, `scripts/`, `tests/` under a `backend/` directory
- [ ] Create `web/` directory with React SPA scaffolding (Vite + React + TypeScript + Tailwind)
- [ ] Create `mobile/` placeholder directory with README
- [ ] Update all import paths and script references for the new structure
- [ ] Update `CLAUDE.md`, `pyproject.toml`, and CI config for new paths
- [ ] Verify all existing tests pass after restructure

### 1.2 Configuration Extensions
- [ ] Add `CorpusSettings` to `config.py`: `corpus_dir`, `supported_formats`, `max_image_size_mb`
- [ ] Add `IndexSettings`: `faiss_index_path`, `metadata_db_path`, `human_similarity_threshold`, `pet_similarity_threshold`, `default_top_k`
- [ ] Add `DetectionSettings`: `human_model` (insightface/deepface), `pet_model` (yolov8/dinov2), `min_face_confidence`, `min_pet_confidence`
- [ ] Add `NarrativeSettings`: `vlm_model`, `llm_model`, `llm_api_key` (env-only), `max_tokens`, `temperature`
- [ ] Add `JobSettings`: `max_concurrent_jobs`, `job_timeout_seconds`, `result_ttl_seconds`
- [ ] Add per-environment YAML configs (`dev.yaml`, `staging.yaml`, `production.yaml`)
- [ ] Add new env vars to `.env.example` with comments on separate lines
- [ ] Write unit tests for config validation (fast-fail on invalid corpus_dir, missing GPU settings)

### 1.3 Dependency Setup
- [ ] Add ML dependencies to `pyproject.toml` under `[project.optional-dependencies.ml]`: `insightface`, `onnxruntime-gpu`, `faiss-gpu` (or `faiss-cpu`), `ultralytics` (YOLOv8), `transformers`, `Pillow`, `piexif`, `geopy`
- [ ] Add narrative dependencies: `anthropic` (Claude API), or `vllm`/`transformers` for local LLM
- [ ] Add web dependencies: create `web/package.json` with React, Tailwind, OpenAPI codegen
- [ ] Create `scripts/download_models.sh` for downloading face detection and embedding model weights
- [ ] Update `.gitignore` for model weights, ONNX files, FAISS index files, corpus data (REQ-SEC-009)
- [ ] Run `uv sync --extra dev --extra ml` and verify installation

**Acceptance criteria**: Project builds, existing tests pass, new config fields load correctly, models downloadable via script.

---

## Phase 2: Data Layer — EXIF Extraction & Metadata Store

Build the corpus scanner and metadata extraction pipeline.

### 2.1 Corpus Scanner
- [ ] Create `src/ingest/scanner.py`: recursive directory walker supporting JPEG, PNG, HEIC
- [ ] Support configurable file extensions via `settings.corpus.supported_formats`
- [ ] Yield `ImageFile` pydantic models: `path`, `format`, `size_bytes`, `discovered_at`
- [ ] Skip unreadable/corrupt files with structured logging (REQ-LOG-001)
- [ ] Support incremental scanning: track processed files in metadata DB, skip already-indexed
- [ ] Write unit tests with fixture directory containing valid/corrupt/mixed images

### 2.2 EXIF Metadata Extraction
- [ ] Create `src/ingest/metadata.py`: extract EXIF from images using `Pillow` + `piexif`
- [ ] Extract: datetime_original, gps_latitude, gps_longitude, orientation, camera_make, camera_model
- [ ] Handle HEIC format (use `pillow-heif` or convert to JPEG)
- [ ] Create `ImageMetadata` pydantic model with all extracted fields + `has_gps`, `has_timestamp` flags
- [ ] Handle missing EXIF gracefully: return model with None fields, log warning
- [ ] Normalize GPS coordinates to decimal degrees
- [ ] Handle timezone extraction from GPS data
- [ ] Write unit tests with real EXIF-tagged test images and stripped-EXIF images

### 2.3 Metadata Store
- [ ] Create `src/ingest/store.py`: SQLite-backed metadata store
- [ ] Schema: `images` table (id, path, format, size, indexed_at) + `metadata` table (image_id, timestamp, lat, lng, camera, orientation)
- [ ] Schema: `faces` table (id, image_id, subject_type, bbox_x, bbox_y, bbox_w, bbox_h, embedding_id, confidence)
- [ ] CRUD operations: `add_image`, `get_image`, `list_images`, `search_by_date_range`, `search_by_location`
- [ ] Support bulk inserts for indexing performance
- [ ] Write unit tests for all CRUD operations

### 2.4 Reverse Geocoding
- [ ] Create `src/ingest/geocoder.py`: GPS coordinates to human-readable location
- [ ] Use `geopy` with Nominatim (offline) or a local geocoding database
- [ ] Cache results with TTL to avoid re-geocoding same coordinates (REQ-ERR-004)
- [ ] Return `LocationInfo` pydantic model: `neighborhood`, `city`, `state`, `country`, `venue_type`
- [ ] Handle missing/invalid GPS gracefully
- [ ] Write unit tests with known coordinates

**Acceptance criteria**: Can scan a directory, extract EXIF from all supported formats, store metadata in SQLite, reverse-geocode GPS coordinates. All operations logged with structlog.

---

## Phase 3: Human Face Detection & Embedding

### 3.1 Human Face Detector
- [ ] Create `src/embeddings/base.py`: abstract `FaceDetector` and `FaceEmbedder` protocols
- [ ] Define `DetectedFace` pydantic model: `bbox`, `confidence`, `subject_type`, `landmarks`, `aligned_image`
- [ ] Create `src/embeddings/human_detector.py`: `InsightFaceDetector` implementing `FaceDetector`
- [ ] Use RetinaFace via `insightface` for detection + alignment
- [ ] Support configurable confidence threshold from `settings.detection.min_face_confidence`
- [ ] Handle images with 0, 1, or multiple faces
- [ ] Write unit tests with fixture images (faces, no faces, multiple faces)

### 3.2 Human Face Embedder
- [ ] Create `src/embeddings/human_embedder.py`: `ArcFaceEmbedder` implementing `FaceEmbedder`
- [ ] Compute 512-dim normalized face embeddings via `insightface` ArcFace
- [ ] Accept aligned face crops from detector
- [ ] Return `FaceEmbedding` model: `vector` (numpy), `model_name`, `model_version`
- [ ] Support GPU acceleration (detect available device)
- [ ] Write unit tests verifying embedding dimensions, normalization, and determinism

### 3.3 Mock Backends for Testing
- [ ] Create `src/embeddings/mock_detector.py`: returns canned detections from fixture data
- [ ] Create `src/embeddings/mock_embedder.py`: returns random normalized vectors
- [ ] Register via `settings.detection.human_model = "mock"` for test isolation (REQ-TST-051)
- [ ] Write tests verifying mock/real switching via config

**Acceptance criteria**: Given an image, detect all human faces, align them, compute embeddings. Works with GPU and CPU. Mock backend for testing without ML models.

---

## Phase 4: Pet Face Detection & Embedding

### 4.1 Pet Face Detector
- [ ] Create `src/embeddings/pet_detector.py`: `PetFaceDetector` implementing `FaceDetector`
- [ ] Use fine-tuned YOLOv8 for pet face/body detection (or fallback to general object detection + filtering)
- [ ] Support cats, dogs as primary species; extensible to other pets
- [ ] Handle pet-specific challenges: variable poses, fur patterns, partial occlusion
- [ ] Tag detections with `subject_type = "pet"`
- [ ] Write unit tests with pet fixture images

### 4.2 Pet Face Embedder
- [ ] Create `src/embeddings/pet_embedder.py`: `PetEmbedder` implementing `FaceEmbedder`
- [ ] Use DINOv2 for general visual similarity embeddings (robust to pose/angle variation)
- [ ] Alternative: SigLIP-2 for multimodal comparison capability
- [ ] Normalize embeddings to unit sphere for cosine similarity
- [ ] Write unit tests verifying embedding dimensions and normalization

### 4.3 Unified Detection Pipeline
- [ ] Create `src/embeddings/pipeline.py`: runs both human and pet detectors on each image
- [ ] Return combined list of `DetectedFace` objects, each tagged with `subject_type`
- [ ] Support configurable detector selection via settings
- [ ] Log detection counts per type (REQ-LOG-001)
- [ ] Write integration test: image with human + pet -> both detected and tagged correctly

**Acceptance criteria**: Given an image, detect both human and pet faces, compute type-specific embeddings. Unified pipeline handles mixed-subject images.

---

## Phase 5: Vector Index Construction & Search

### 5.1 FAISS Index Manager
- [ ] Create `src/index/manager.py`: `IndexManager` class
- [ ] Build separate FAISS indices for human and pet embeddings (prevent cross-contamination)
- [ ] Support `IndexFlatIP` for exact search (development) and `IndexIVFFlat` for approximate search (production, ~1M scale)
- [ ] Store mapping: FAISS internal ID -> `face_id` in metadata DB
- [ ] Support incremental additions without full rebuild
- [ ] Persist indices to disk (`settings.index.faiss_index_path`)
- [ ] Log index stats: total vectors, index type, memory usage (REQ-LOG-001)
- [ ] Write unit tests for add, search, persist, reload

### 5.2 Search Interface
- [ ] Create `src/index/search.py`: `search_index(query_vector, k, threshold, subject_type) -> list[Match]`
- [ ] `Match` pydantic model: `face_id`, `image_id`, `image_path`, `similarity_score`, `subject_type`, `bbox`, `metadata`
- [ ] Filter by `subject_type` before search (query only the correct index)
- [ ] Apply similarity threshold post-search
- [ ] Support configurable top-k from `settings.index.default_top_k`
- [ ] Write unit tests with synthetic embeddings and known nearest neighbors

### 5.3 Batch Indexing Pipeline
- [ ] Create `src/index/batch.py`: orchestrates scan -> detect -> embed -> index for full corpus
- [ ] Support resumable processing (checkpoint after each batch of N images)
- [ ] Progress logging: images processed, faces found (human/pet), time elapsed, ETA
- [ ] Error handling: skip failed images, log errors, continue (REQ-ERR-002)
- [ ] Create `scripts/index_corpus.sh`: wrapper script for batch indexing
- [ ] Write integration test on small fixture corpus

**Acceptance criteria**: Build FAISS indices from corpus, search by type-filtered query, resume interrupted indexing. Index ~1M images in hours on GPU.

---

## Phase 6: Reference Photo Query API

### 6.1 Detection Endpoint
- [ ] Create `POST /api/v1/detect` endpoint
- [ ] Accept multipart image upload
- [ ] Run both human and pet detectors
- [ ] Return: list of detected faces with bounding boxes, types, confidence scores
- [ ] Return image dimensions for UI overlay rendering
- [ ] Response schema: `DetectionResponse` pydantic model
- [ ] Write integration tests

### 6.2 Query Endpoint
- [ ] Create `POST /api/v1/query` endpoint
- [ ] Accept: image file, `subject_type`, optional `face_bbox`, `threshold`, `top_k`, `date_from`, `date_to`
- [ ] If `face_bbox` provided: crop face from image at those coordinates
- [ ] Embed the face using type-appropriate embedder
- [ ] Search the type-filtered FAISS index
- [ ] Enrich results with metadata from SQLite store
- [ ] For async (large corpus): return job ID immediately, process in background
- [ ] For sync (small corpus): return results directly
- [ ] Response schema: `QueryResponse` with `session_id` and paginated `results`
- [ ] Write integration tests for both sync and async paths

### 6.3 Results Endpoint
- [ ] Create `GET /api/v1/query/{session_id}/results` endpoint
- [ ] Cursor-based pagination: `?cursor=xxx&limit=20`
- [ ] Return: image URLs (via `/media/`), similarity scores, metadata, bounding boxes
- [ ] Write integration tests for pagination

### 6.4 Media Serving
- [ ] Create `GET /api/v1/media/{path}` endpoint
- [ ] Serve images from corpus directory by relative path
- [ ] Validate path stays within `settings.corpus.corpus_dir` (prevent traversal, REQ-SEC-004)
- [ ] Support optional query param `?size=thumb` for thumbnail generation
- [ ] Cache thumbnails on disk
- [ ] Write security tests for path traversal attempts

**Acceptance criteria**: Upload reference photo, get detected faces, run type-filtered retrieval, paginate results. Images served via URL.

---

## Phase 7: Timeline Construction

### 7.1 Timeline Builder
- [ ] Create `src/narrative/timeline.py`: `build_timeline(matches: list[Match]) -> Timeline`
- [ ] `Timeline` model: `date_range`, `total_days`, `active_days`, `entries: list[TimelineEntry]`
- [ ] `TimelineEntry`: `date`, `time`, `location`, `image_path`, `image_url`, `confidence`, `scene_label`
- [ ] Sort by timestamp; group by calendar day
- [ ] Handle timezone normalization from GPS coordinates
- [ ] Handle missing timestamps: infer from GPS proximity or leave unplaced
- [ ] Write unit tests with synthetic timeline data

### 7.2 Day Grouping
- [ ] Create `src/narrative/grouping.py`: `group_by_day(timeline) -> dict[date, list[TimelineEntry]]`
- [ ] Within each day, cluster photos into "scenes" (< 30 min gap = same scene)
- [ ] Label scenes with time-of-day context: "morning", "midday", "afternoon", "evening", "night"
- [ ] Detect and flag multi-day gaps
- [ ] Write unit tests

### 7.3 Pattern Detection
- [ ] Create `src/narrative/patterns.py`: `detect_patterns(day_groups) -> list[Pattern]`
- [ ] `Pattern` model: `pattern_type` (recurring_location, daily_routine, weekly_pattern), `description`, `confidence`, `evidence`
- [ ] Detect recurring locations (same GPS cluster across multiple days)
- [ ] Detect time-based routines (similar times on multiple days)
- [ ] Write unit tests with multi-day fixture data containing known patterns

**Acceptance criteria**: Retrieved photos ordered chronologically, grouped by day, with detected cross-day patterns. Handles missing metadata gracefully.

---

## Phase 8: Dossier Narrative Generation

### 8.1 Photo Description (VLM)
- [ ] Create `src/narrative/describer.py`: `describe_photo(image, metadata, subject_type) -> str`
- [ ] Use Qwen-2.5-VL (or LLaVA) to describe visual content of each photo
- [ ] Prompt template: include subject type context (human vs. pet), metadata hints (time, location)
- [ ] Set explicit `max_tokens` on every call (REQ-ERR-007)
- [ ] Handle VLM errors gracefully: fallback to metadata-only description
- [ ] Log prompt, response, latency, token usage (REQ-LOG-004, REQ-LOG-005)
- [ ] Write unit tests with mock VLM

### 8.2 Dossier Generator (LLM)
- [ ] Create `src/narrative/generator.py`: `generate_dossier(descriptions, timeline, subject_type) -> Dossier`
- [ ] `Dossier` model: `executive_summary`, `date_range`, `subject_type`, `days: list[DossierDay]`, `patterns: list[Pattern]`, `confidence_notes`
- [ ] `DossierDay`: `date`, `entries: list[DossierEntry]`, `day_summary`
- [ ] `DossierEntry`: `time`, `location`, `description`, `image_url`, `confidence`
- [ ] Prompt template for LLM:
  - Input: ordered photo descriptions with timestamps, locations, patterns
  - Output format: structured JSON matching `Dossier` model
  - Subject-type-specific language (human vs. pet)
  - Uncertainty language for low-confidence entries
- [ ] Support streaming output for long dossiers
- [ ] Set explicit `max_tokens` (REQ-ERR-007)
- [ ] Log full prompt and response at DEBUG level only (REQ-LOG-009)
- [ ] Write unit tests with mock LLM
- [ ] Write integration tests with real LLM (separate test category)

### 8.3 Dossier API Endpoints
- [ ] Create `POST /api/v1/dossier` endpoint: generate dossier from retrieval session
- [ ] Returns job ID for async generation
- [ ] Create `GET /api/v1/dossier/{session_id}` endpoint: retrieve generated dossier
- [ ] Support `?format=json` (default) and `?format=markdown`
- [ ] Write integration tests

**Acceptance criteria**: Photos described by VLM, narrative generated by LLM, structured as multi-day dossier with executive summary, per-day entries, and cross-day patterns. Subject-type-appropriate language.

---

## Phase 9: Async Job System

### 9.1 Job Queue
- [ ] Create `src/jobs/manager.py`: in-memory job queue with background workers
- [ ] `Job` model: `id`, `type` (index, query, dossier), `status` (pending, running, completed, failed), `progress`, `result`, `error`, `created_at`, `updated_at`
- [ ] Support configurable max concurrent jobs from `settings.jobs.max_concurrent_jobs`
- [ ] Job result TTL: auto-cleanup after `settings.jobs.result_ttl_seconds`
- [ ] Write unit tests

### 9.2 Job API Endpoints
- [ ] Create `GET /api/v1/jobs/{job_id}` endpoint: job status and progress (polling)
- [ ] Create `GET /api/v1/jobs/{job_id}/stream` endpoint: SSE stream for real-time progress
- [ ] Write integration tests for both polling and SSE

### 9.3 Wire Existing Endpoints to Job System
- [ ] Connect `POST /query` to job queue for large corpus queries
- [ ] Connect `POST /dossier` to job queue for narrative generation
- [ ] Add progress callbacks to batch indexing pipeline
- [ ] Write integration tests for async query -> poll -> results flow

**Acceptance criteria**: Long-running operations return job ID immediately. Clients can poll or stream progress. Jobs auto-cleanup after TTL.

---

## Phase 10: Ground-Truth Evaluation

### 10.1 Manifest Format
- [ ] Define ground-truth manifest schema: JSON with `subjects: [{id, name, subject_type, reference_photo, photos: [filename]}]`
- [ ] Create `src/evaluation/manifest.py`: load and validate manifest files
- [ ] Write unit tests

### 10.2 Evaluation Runner
- [ ] Create `src/evaluation/runner.py`: `evaluate(manifest, index_manager) -> EvaluationReport`
- [ ] For each subject: run retrieval using reference photo, compare against ground-truth photo list
- [ ] Compute per-subject: precision, recall, F1
- [ ] Compute aggregates: overall, human-only, pet-only
- [ ] Identify false positives and false negatives with image paths
- [ ] Detect cross-type confusion (human detected as pet, vice versa)
- [ ] Write unit tests with synthetic manifest and mock index

### 10.3 Evaluation API Endpoints
- [ ] Create `POST /api/v1/evaluate` endpoint: run evaluation for a subject
- [ ] Create `GET /api/v1/evaluate/summary` endpoint: aggregate evaluation results
- [ ] Write integration tests

### 10.4 Evaluation Script
- [ ] Create `scripts/evaluate_all.sh`: batch evaluation across all subjects in manifest
- [ ] Output: per-subject report + aggregate summary (JSON + human-readable)
- [ ] Update `docs/app_cheatsheet.md` with evaluation commands

**Acceptance criteria**: Run evaluation against ground-truth manifest. Per-subject and aggregate precision/recall/F1. Separate human vs. pet metrics. Human recall >= 80%, pet recall >= 70%.

---

## Phase 11: Web Frontend (React SPA)

### 11.1 Project Setup
- [ ] Initialize Vite + React + TypeScript project in `web/`
- [ ] Configure Tailwind CSS
- [ ] Generate typed API client from backend OpenAPI schema
- [ ] Configure dev proxy to backend API
- [ ] Create base layout, routing, error boundaries

### 11.2 Reference Photo Upload & Auto-Detection
- [ ] Build `UploadPage` component: drag-drop zone + file browser
- [ ] On upload: call `POST /detect`, render bounding box overlay on image
- [ ] Color-code boxes: blue (human), green (pet)
- [ ] Show confidence score on each box
- [ ] Click-to-select face: highlight selected, dim others
- [ ] Type override toggle on bounding box
- [ ] Manual bounding box drawing for no-detection fallback
- [ ] "Search" button triggers `POST /query`

### 11.3 Results View
- [ ] Build `ResultsPage` component: photo grid with lazy loading
- [ ] Show similarity scores, timestamps, locations, subject type badges
- [ ] Cursor-based pagination (infinite scroll)
- [ ] Date range filter controls
- [ ] Progress indicator for async queries (poll `GET /jobs/{id}`)

### 11.4 Timeline View
- [ ] Build `TimelinePage` component: chronological photo strip grouped by day
- [ ] Calendar heat map showing photo density per day
- [ ] Day-level drill-down
- [ ] Gap annotations ("no photos March 8-10")

### 11.5 Dossier View
- [ ] Build `DossierPage` component: rendered narrative with inline photo thumbnails
- [ ] Executive summary section
- [ ] Per-day collapsible sections
- [ ] Cross-day patterns section
- [ ] Confidence indicators (color-coded)
- [ ] Download buttons: PDF, Markdown

### 11.6 Evaluation Panel
- [ ] Build `EvaluationPanel` component (shown when ground-truth manifest loaded)
- [ ] Per-subject precision/recall/F1 table
- [ ] Aggregate metrics with human/pet breakdown
- [ ] False positive/negative image gallery

### 11.7 Responsive Design
- [ ] Ensure all views are functional on mobile screen sizes
- [ ] Touch-friendly interactions for face selection
- [ ] Collapsible panels for small screens

**Acceptance criteria**: Fully functional web SPA. Upload photo, auto-detect faces, select subject, view results, browse timeline, read dossier, export PDF. Responsive on mobile browsers.

---

## Phase 12: Upload & Photo Contribution API

### 12.1 Standard Upload
- [ ] Create `POST /api/v1/photos/upload` endpoint
- [ ] Accept multipart form with image + optional metadata JSON
- [ ] Extract EXIF server-side; prefer client-provided metadata if present
- [ ] Accept JPEG, PNG, HEIC; normalize to JPEG/PNG for processing
- [ ] Max file size: 20MB
- [ ] Return photo IDs and extracted metadata
- [ ] Write integration tests

### 12.2 Resumable Upload (Mobile-Ready)
- [ ] Create `POST /api/v1/photos/upload/init` endpoint: initiate upload session
- [ ] Create `PATCH /api/v1/photos/upload/{session_id}` endpoint: send chunks with `Content-Range`
- [ ] Create `GET /api/v1/photos/upload/{session_id}/status` endpoint: check progress
- [ ] Assemble chunks on completion, trigger processing
- [ ] Write integration tests for chunked upload flow

**Acceptance criteria**: Photos uploadable via standard multipart or resumable chunks. EXIF preserved. HEIC handled.

---

## Phase 13: Observability & Monitoring

### 13.1 Structured Logging Enhancements
- [ ] Add AI-specific fields to all LLM/VLM calls: `model`, `temperature`, `max_tokens`, `latency_ms`, `input_tokens`, `output_tokens` (REQ-LOG-003)
- [ ] Add request correlation IDs to all API requests (REQ-LOG-002)
- [ ] Separate prompt analytics logs from operational logs (REQ-LOG-007)
- [ ] Guard expensive debug logs with level checks (REQ-LOG-010)

### 13.2 Metrics & Health
- [ ] Extend `/health` with readiness check (is index loaded? are models ready?) (REQ-RUN-011)
- [ ] Create `GET /api/v1/index/stats` endpoint: total images, faces, human count, pet count, index size
- [ ] Log retrieval latency, dossier generation latency as metrics
- [ ] Track and log job queue depth and processing times

### 13.3 Prompt Logging
- [ ] Create dedicated prompt log store (JSONL or SQLite) (REQ-LOG-004)
- [ ] Log: prompt text, response text, model, parameters, latency, token counts
- [ ] Redact any PII from logged prompts (REQ-LOG-006)
- [ ] Configurable: full logging at DEBUG, metadata-only at INFO (REQ-LOG-009)

**Acceptance criteria**: All LLM calls logged with full metadata. Correlation IDs on all requests. Health/readiness endpoints differentiated. Prompt logs in dedicated store.

---

## Phase 14: Security Hardening

### 14.1 Input Validation
- [ ] Validate all uploaded files: check magic bytes match declared type (REQ-SEC-002)
- [ ] Enforce file size limits server-side
- [ ] Sanitize filenames in upload paths
- [ ] Path traversal prevention on media serving endpoint (REQ-SEC-004)

### 14.2 LLM Safety
- [ ] Implement prompt injection defenses for dossier generation (REQ-SEC-003)
- [ ] System prompt isolation: narrative prompts don't include raw user input
- [ ] Output validation: check generated dossier for PII leaks, harmful content
- [ ] Set explicit `max_tokens` on all LLM calls (REQ-ERR-007)

### 14.3 Rate Limiting
- [ ] Add rate limiting to public API endpoints (REQ-SEC-007)
- [ ] Configure via settings: requests per minute per IP
- [ ] Return `429 Too Many Requests` with `Retry-After` header

### 14.4 Authentication
- [ ] Implement JWT-based authentication for API access (stateless, mobile-ready)
- [ ] Admin endpoints continue to use `X-Admin-Secret` header
- [ ] Write security integration tests

**Acceptance criteria**: All uploads validated. Prompt injection defenses in place. Rate limiting active. JWT auth functional.

---

## Phase 15: Documentation & Finalization

### 15.1 Architecture & Design Docs
- [x] Create `docs/architecture/architecture_overview.md` with C4 diagrams (Mermaid)
- [x] Create `docs/design/design_specification.md` with module interfaces and data models
- [ ] Create `docs/design/api_contract.md` with full API specification

### 15.2 Operational Docs
- [ ] Create `docs/runbook/deployment_runbook.md` (REQ-DOC-003)
- [ ] Create `docs/runbook/model_update_runbook.md`
- [ ] Create `docs/runbook/index_rebuild_runbook.md`
- [ ] Create participant photo collection guide
- [ ] Create pet photo collection guide

### 15.3 README & Cheatsheet
- [ ] Write `README.md` from template (REQ-AGT-001)
- [ ] Update `docs/app_cheatsheet.md` with all new endpoints, scripts, config vars
- [ ] Update `.env.example` with all new variables

### 15.4 Final Quality
- [ ] Run `bash scripts/check_all.sh` (lint + typecheck + tests)
- [ ] Run security review agent
- [ ] Run code simplifier agent
- [ ] Verify all acceptance criteria from project_requirements_v2.md

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
```

Phases 3 and 4 can run in parallel. Phases 10, 12, 13, 14 can run in parallel after Phase 6. Phase 15 runs last.

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
