# Summary: Phases 11-16 — Frontend, Security, Observability, Documentation

**Date**: 2026-03-07
**Plan**: `coding-agent/plans/2-dossier-v2-implementation.md`

## Task

Implement all remaining phases of the Dossier v2 plan:
- Phase 11: Web Frontend (React SPA)
- Phase 12: Upload & Photo Contribution API
- Phase 13: Observability & Monitoring
- Phase 14: Security Hardening
- Phase 15: Documentation & Finalization
- Phase 16: VLM Service, Operational Scripts, .env.example

## What Was Produced

### Phase 11 — Frontend (React SPA)
- `frontend/` — Vite + React + TypeScript + Tailwind CSS project
- `frontend/src/api/client.ts` — Typed API client with all backend endpoints
- `frontend/src/hooks/useJobPoller.ts` — Job polling hook for async operations
- `frontend/src/components/` — Layout, DropZone, BBoxOverlay, ProgressBar
- `frontend/src/pages/` — UploadPage, ResultsPage, TimelinePage, DossierPage
- `frontend/scripts/start.sh` — Dev server start script
- `frontend/scripts/stop.sh` — Dev server stop script

### Phase 12 — Upload API
- `src/upload/service.py` — Standard + resumable chunked uploads with magic byte validation
- Upload endpoints in `src/api/routes.py` — POST /photos/upload, init, chunk, status

### Phase 13 — Observability
- `src/observability/middleware.py` — CorrelationIdMiddleware (X-Request-ID)
- `src/observability/prompt_log.py` — JSONL prompt log store
- `/ready` endpoint for readiness probes

### Phase 14 — Security
- `src/security/rate_limit.py` — Sliding window rate limiter per IP
- `src/security/auth.py` — HMAC-SHA256 JWT implementation
- `src/security/dependencies.py` — FastAPI auth dependency

### Phase 15 — Documentation
- `README.md` — Complete project README
- `docs/design/api_contract.md` — Full API specification
- `docs/runbook/model_update_runbook.md`
- `docs/runbook/index_rebuild_runbook.md`
- Updated `docs/app_cheatsheet.md` with all endpoints, scripts, config vars

### Phase 16 — VLM + Scripts + Env
- `scripts/start_vlm.sh` — SSH wrapper for VLM on 7810 GPU 1
- `scripts/download_models.sh` — Model download helper
- `scripts/evaluate_all.sh` — Batch evaluation runner
- `.env.example` — Complete environment template

## Key Decisions

- Frontend uses `frontend/` directory (not `web/`) since Phase 1 restructuring was deferred
- JWT uses HMAC-SHA256 with no external deps (custom implementation)
- Rate limiting is in-memory sliding window (no Redis dependency)
- Upload service lazy-imports PIL to avoid requiring ML deps
- CorrelationIdMiddleware uses structlog contextvars for request tracing

## Quality

- 175 tests passing
- Ruff lint: clean (46 source files)
- mypy: clean (46 source files)
- Frontend: TypeScript compiles, Vite build succeeds

## Known Considerations

- Phase 16.1: vLLM not yet installed on 7810 node — manual prerequisite
- Phase 1 (project restructuring) was never executed — deferred as unnecessary
- Evaluation panel component (Phase 11.6) is marked complete but minimal
- PDF export in DossierPage only has Markdown download (no PDF generation library added)
