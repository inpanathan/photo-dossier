# Photo Dossier

Given a reference photo of a person or pet, retrieve all matching photos from a large image corpus and generate a multi-day narrative dossier with timeline, patterns, and photo descriptions.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [API](#api)
- [Evaluation](#evaluation)
- [Contributing](#contributing)
- [License](#license)

## Overview

Photo Dossier is an end-to-end system for visual re-identification and narrative generation. Given a single reference photo, it:

1. **Detects** human and pet faces using InsightFace (ArcFace) and YOLOv8 + DINOv2
2. **Retrieves** all matching photos from a corpus using FAISS vector search
3. **Builds a timeline** grouping matches by date, time, and location using EXIF metadata
4. **Generates a narrative dossier** using VLM photo descriptions and LLM narrative synthesis

The system supports both human and pet subjects with type-specific detection, embedding, and similarity thresholds.

### Key Technologies

- **Backend**: Python 3.12, FastAPI, structlog, Pydantic
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Detection**: InsightFace (RetinaFace + ArcFace), YOLOv8, DINOv2
- **Search**: FAISS (flat and IVF indices)
- **Narrative**: Qwen2.5-VL-7B (photo descriptions), Qwen2.5-14B (dossier generation) via vLLM
- **Storage**: SQLite (metadata), filesystem (corpus + indices)

## Features

- Upload a reference photo and auto-detect all faces (human and pet)
- Click-to-select a face for corpus-wide retrieval
- Chronological timeline with calendar heatmap and gap detection
- AI-generated narrative dossier with per-day summaries and cross-day pattern detection
- Async job system with SSE streaming for long-running operations
- Resumable chunked uploads (mobile-ready)
- JWT authentication and per-IP rate limiting
- Structured logging with correlation IDs and dedicated prompt logging
- Ground-truth evaluation framework with per-subject precision/recall/F1

## Architecture

```
┌─────────────┐     ┌──────────────────────────┐     ┌───────────────────┐
│  React SPA  │────▶│  FastAPI Backend          │────▶│  7810 GPU Node    │
│  (Vite)     │     │  (Local, RTX 3090)        │     │  (2x RTX 3060)    │
│             │     │                            │     │                    │
│  Upload     │     │  /api/v1/detect            │     │  GPU 0: Detection  │
│  Results    │     │  /api/v1/query             │     │    InsightFace     │
│  Timeline   │     │  /api/v1/pipeline          │     │    YOLOv8+DINOv2   │
│  Dossier    │     │  /api/v1/dossier           │     │                    │
│             │     │  /api/v1/jobs              │     │  GPU 1: VLM        │
│             │     │                            │     │    Qwen2.5-VL-7B   │
│             │     │  vLLM (Qwen2.5-14B, GPU)   │     │                    │
└─────────────┘     └──────────────────────────┘     └───────────────────┘
                           │
                    ┌──────┴──────┐
                    │  SQLite DB  │
                    │  FAISS Index│
                    │  Corpus Dir │
                    └─────────────┘
```

See `docs/architecture/architecture_overview.md` for detailed C4 diagrams.

## Project Structure

```
├── main.py                      # FastAPI entry point
├── src/
│   ├── api/routes.py            # API endpoints (mounted at /api/v1)
│   ├── admin/                   # Admin console for static file mounts
│   ├── embeddings/              # Detection & embedding (InsightFace, YOLOv8, DINOv2)
│   ├── index/                   # FAISS index manager & batch indexer
│   ├── ingest/                  # Corpus scanner, EXIF extraction, metadata store
│   ├── jobs/                    # Async job queue with background workers
│   ├── models/                  # Pydantic data models
│   ├── narrative/               # Timeline, patterns, VLM describer, LLM generator
│   ├── observability/           # Correlation IDs, prompt logging
│   ├── retrieval/               # Search orchestration
│   ├── security/                # JWT auth, rate limiting
│   ├── upload/                  # Photo upload (standard + resumable)
│   └── utils/                   # Config, logging, error handling
├── frontend/                    # React SPA (Vite + TypeScript + Tailwind)
│   ├── src/
│   │   ├── api/client.ts        # Typed API client
│   │   ├── components/          # Layout, DropZone, BBoxOverlay, ProgressBar
│   │   └── pages/               # Upload, Results, Timeline, Dossier
│   └── scripts/                 # start.sh, stop.sh
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # API integration tests
│   ├── evaluation/              # Model evaluation tests
│   └── safety/                  # Security tests
├── configs/                     # Per-environment YAML configs
├── scripts/                     # Operational scripts
├── docs/                        # Architecture, design, runbooks
└── data/                        # Corpus, indices, uploads (gitignored)
```

## Installation

### Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend)
- NVIDIA GPU with CUDA 12.1+ (for ML inference)
- [uv](https://docs.astral.sh/uv/) package manager

### Quick Start

```bash
# 1. Clone
git clone https://github.com/inpanathan/photo-dossier.git
cd photo-dossier

# 2. Backend setup
bash scripts/setup.sh           # installs deps, copies .env.example to .env
cp .env.example .env            # edit with your settings

# 3. Install with ML dependencies
uv sync --extra dev --extra ml

# 4. Download model weights
bash scripts/download_models.sh

# 5. Create data directories
mkdir -p data/{corpus,indices,uploads}

# 6. Start the backend
bash scripts/start_server.sh

# 7. Start the frontend (separate terminal)
bash frontend/scripts/start.sh

# 8. Open http://localhost:5173
```

### GPU Node Setup (7810)

The detection and VLM services run on a separate GPU node:

```bash
# Start detection service (GPU 0)
bash scripts/start_inference.sh

# Start VLM service (GPU 1)
bash scripts/start_vlm.sh
```

See `docs/runbook/deployment_runbook.md` for detailed setup instructions.

## Usage

### Web Interface

1. Open `http://localhost:5173`
2. Upload or drag-drop a reference photo
3. The system detects all faces — click the one you want to search for
4. Select "Human" or "Pet" and click "Search Corpus"
5. View results as a photo grid, chronological timeline, or narrative dossier
6. Export the dossier as Markdown

### API

```bash
# Detect faces in an image
curl -X POST http://localhost:8000/api/v1/detect \
  -F "image=@reference.jpg"

# Search corpus for matches
curl -X POST http://localhost:8000/api/v1/query \
  -F "image=@reference.jpg" \
  -F "subject_type=human"

# Run full pipeline (query + timeline + dossier)
curl -X POST http://localhost:8000/api/v1/pipeline \
  -F "image=@reference.jpg" \
  -F "subject_type=human"

# Check job progress
curl http://localhost:8000/api/v1/jobs/{job_id}
```

See `docs/design/api_contract.md` for the full API specification.

### Index the Corpus

```bash
# Place images in data/corpus/, then:
bash scripts/index_corpus.sh

# Check stats
curl http://localhost:8000/api/v1/index/stats
```

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and edit:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `dev` | Environment (dev, staging, production) |
| `CORPUS__CORPUS_DIR` | `data/corpus` | Photo corpus directory |
| `INFERENCE__BASE_URL` | `http://100.111.31.125:8010` | Detection service URL |
| `NARRATIVE__LLM_BASE_URL` | `http://localhost:8001/v1` | LLM service URL |
| `NARRATIVE__VLM_BASE_URL` | `http://100.111.31.125:8011/v1` | VLM service URL |
| `INDEX__HUMAN_SIMILARITY_THRESHOLD` | `0.6` | Min similarity for human matches |
| `INDEX__PET_SIMILARITY_THRESHOLD` | `0.5` | Min similarity for pet matches |

See `.env.example` for all variables with descriptions.

## Evaluation

Create a ground-truth manifest at `data/ground_truth.json` (see `docs/runbook/deployment_runbook.md#corpus-preparation`) and run:

```bash
bash scripts/evaluate_all.sh
```

This computes per-subject and aggregate precision, recall, and F1 with separate human vs. pet breakdowns.

## Development

```bash
# Run tests
uv run pytest tests/ -x -q

# Lint and typecheck
uv run ruff check src/ tests/ --fix
uv run mypy src/ --ignore-missing-imports

# Full quality check
bash scripts/check_all.sh
```

## Documentation

- [Architecture Overview](docs/architecture/architecture_overview.md) — C4 diagrams
- [Design Specification](docs/design/design_specification.md) — Module interfaces
- [API Contract](docs/design/api_contract.md) — Full API reference
- [Deployment Runbook](docs/runbook/deployment_runbook.md) — Setup and operations
- [Model Update Runbook](docs/runbook/model_update_runbook.md)
- [Index Rebuild Runbook](docs/runbook/index_rebuild_runbook.md)
- [App Cheatsheet](docs/app_cheatsheet.md) — Quick reference for URLs, commands, config
- [Troubleshooting](docs/troubleshooting.md)

## License

MIT
