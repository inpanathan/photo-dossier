# 001 — Dossier Backend Modules + Integration Tests

**Date**: 2026-03-06
**Task**: Build complete Dossier v2 backend (phases 2-10) and integration test suite

## What was produced

### Source modules (all in `src/`)
- `models/__init__.py` — 25+ domain models (Subject, Detection, Index, Timeline, Narrative, Job, Evaluation)
- `ingest/scanner.py` — recursive corpus directory walker
- `ingest/metadata.py` — EXIF extraction (timestamp, GPS, camera info)
- `ingest/store.py` — SQLite metadata store (images, faces, metadata tables, WAL mode)
- `embeddings/client.py` — HTTP client for 7810 inference service (InsightFace + YOLOv8 + DINOv2)
- `index/manager.py` — FAISS IndexFlatIP manager (separate human 512-dim / pet 768-dim indices)
- `index/batch.py` — batch indexing pipeline (scan → detect → embed → index)
- `retrieval/service.py` — query orchestrator (embed query → search index → enrich metadata)
- `narrative/timeline.py` — timeline builder (day groups, scene clustering, gap detection)
- `narrative/patterns.py` — pattern detection (recurring locations, daily routines, weekly patterns)
- `narrative/describer.py` — VLM photo describer (Qwen2.5-VL via OpenAI API)
- `narrative/generator.py` — LLM dossier generator (Qwen2.5-14B, structured JSON output)
- `jobs/manager.py` — async job manager (semaphore concurrency, TTL cleanup, progress callbacks)
- `evaluation/manifest.py` — ground-truth manifest loader
- `evaluation/runner.py` — evaluation runner (precision/recall/F1 per subject and aggregate)
- `api/routes.py` — 12 API endpoints (detect, query, pipeline, dossier, index, jobs, media)

### Tests
- `tests/unit/test_timeline.py` — timeline builder tests
- `tests/unit/test_patterns.py` — pattern detection tests
- `tests/unit/test_job_manager.py` — async job lifecycle tests
- `tests/unit/test_manifest.py` — manifest loader tests
- `tests/unit/test_metadata_store.py` — SQLite store CRUD tests
- `tests/integration/conftest.py` — mock service fixtures for API tests
- `tests/integration/test_dossier_api.py` — 14 endpoint integration tests

### Scripts
- `scripts/start_inference.sh` — start/stop inference service on 7810
- `scripts/index_corpus.sh` — batch corpus indexing with health check

### Infrastructure (7810 node)
- InsightFace GPU detection running on port 8010
- L2 normalization fix for ArcFace embeddings
- Hatchling build fix for editable installs

## Key decisions
- Separate FAISS indices for human (512-dim) and pet (768-dim) to prevent cross-type confusion
- In-memory job queue (not Redis) — sufficient for single-node deployment
- Mock services injected via `set_services()` for integration tests — no ML deps required
- `datetime.utcnow()` → `datetime.now(tz=UTC)` across all modules (Python 3.12 deprecation)

## Quality
- 99 tests passing (85 unit + 14 integration)
- Ruff lint: 0 errors
- mypy: 0 errors

## Known follow-ups
- `.env.example` update blocked by file protection hook
- vLLM setup on 7810 GPU 1 (Qwen2.5-VL-7B on port 8011) not yet done
- Frontend (Phase 11) not started
- `scripts/evaluate_all.sh` and `scripts/download_models.sh` not created
- README.md not updated from template
