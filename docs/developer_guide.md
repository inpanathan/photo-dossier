# Developer Guide: Using the AI/ML Project Template

This guide walks you through creating a new AI/ML project from this template and developing it following the established requirements and conventions.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Creating Your Project](#2-creating-your-project)
3. [Writing Project Requirements](#3-writing-project-requirements)
4. [Building Features](#4-building-features)
5. [Configuration](#5-configuration)
6. [API Development](#6-api-development)
7. [Data and Models](#7-data-and-models)
8. [Testing](#8-testing)
9. [Logging and Observability](#9-logging-and-observability)
10. [Error Handling](#10-error-handling)
11. [Security](#11-security)
12. [Scripts and Automation](#12-scripts-and-automation)
13. [CI/CD and Quality Gates](#13-cicd-and-quality-gates)
14. [Documentation](#14-documentation)
15. [Requirements Checklist Reference](#15-requirements-checklist-reference)

---

## 1. Quick Start

```bash
# 1. Clone the template into your new project
git clone <template-repo-url> my-project
cd my-project

# 2. Run first-time setup (installs deps, copies .env, installs pre-commit hooks, runs tests)
bash scripts/setup.sh

# 3. Start the dev server
bash scripts/start_server.sh

# 4. Verify it works
curl http://localhost:8000/health
# Open http://localhost:8000/docs for Swagger UI
```

**What `setup.sh` does:**
- Installs Python dependencies via `uv sync --extra dev`
- Copies `.env.example` to `.env` (if `.env` doesn't exist)
- Installs pre-commit hooks
- Creates the `data/` directory structure
- Runs the test suite to verify everything works

---

## 2. Creating Your Project

### Step 1: Initialize from the template

After cloning, update these files with your project's identity:

| File | What to change |
|------|---------------|
| `pyproject.toml` | `name`, `description`, `version`, and any project-specific dependencies |
| `.env.example` / `.env` | Project-specific environment variables |
| `configs/dev.yaml` | Development-specific settings (ports, log levels) |
| `README.md` | Replace with your project README (use `docs/templates/README_template.md` as a base) |

### Step 2: Write your project requirements

Before writing any code, create a project requirements document. See [Section 3](#3-writing-project-requirements).

### Step 3: Set up the requirements controller

After writing requirements, sync the controller JSON that tracks implementation status:

```bash
# Preview what will be generated
bash scripts/sync_requirements.sh --dry-run

# Generate the controller files
bash scripts/sync_requirements.sh
```

This creates `docs/requirements/*_controller.json` files where you track which requirements are implemented (`"Y"`) or not yet (`"N"`).

### Step 4: Build iteratively

Follow the feature development workflow in [Section 4](#4-building-features) to implement your project incrementally.

---

## 3. Writing Project Requirements

Requirements are the backbone of this template. They live in `docs/requirements/` and drive what you build, test, and document.

### The requirements files

| File | Purpose |
|------|---------|
| `common_requirements.md` | **Universal standards** — logging, observability, testing, security, config, error handling, CI/CD, data management. These apply to every project. |
| `documentation_requirements.md` | **Documentation standards** — what documents to produce, content standards, review practices. |
| `project_requirements_v1.md` | **Your project-specific spec** — what your application does, its features, data, models, and APIs. |

### Creating your project specification

Use the template at `docs/templates/project_requirements_template.md` to write your project spec. The template has 15 sections:

```
1.  Goal                — One-sentence summary + problem statement
2.  Deliverables        — Concrete outputs (API, CLI, models, etc.)
3.  High-Level Reqs     — Core flows, main features, v1 must-haves vs nice-to-haves
4.  Functional Reqs     — Feature-by-feature: inputs, outputs, behavior, edge cases
5.  Non-Functional Reqs — Performance, security, reliability, maintainability
6.  Tech Stack          — Languages, frameworks, dependencies, infra constraints
7.  Project Structure   — Directory layout, naming conventions
8.  Data and Models     — Data sources, schemas, model families, training constraints
9.  Example Scenarios   — Concrete input/output examples (few-shot specs)
10. Interfaces & APIs   — HTTP endpoints, CLI commands, library APIs
11. Testing             — Tools, test types, coverage, acceptance criteria
12. Code Style          — Linting, formatting, docstring style
13. Workflow            — How to operate (plan first, small changes, etc.)
14. Out of Scope        — Explicit exclusions and boundaries
15. Output Format       — How responses/artifacts should be formatted
```

**Tips for writing good requirements:**

- Be specific about inputs and outputs for each feature
- Include concrete example scenarios — these become test cases later
- Separate v1 must-haves from nice-to-haves
- Define measurable acceptance criteria (latency targets, accuracy thresholds)
- List what is explicitly out of scope to prevent scope creep

### Tracking requirement implementation

Each requirements markdown file has a corresponding `*_controller.json` that tracks implementation status. After editing requirements:

```bash
# Sync controllers (preserves existing "Y" flags)
bash scripts/sync_requirements.sh

# Preview changes first
bash scripts/sync_requirements.sh --dry-run

# Sync a single file
bash scripts/sync_requirements.sh --file common
```

Mark requirements as implemented by setting `"implement": "Y"` in the controller JSON as you complete them.

---

## 4. Building Features

### Workflow overview

The template enforces a **plan-first, incremental** development workflow per `REQ-AGT-002`:

```
1. Write requirements  →  docs/requirements/project_requirements_v1.md
2. Plan feature         →  docs/specs/<feature-name>.md
3. Implement            →  src/, tests/
4. Test                 →  uv run pytest
5. Quality check        →  bash scripts/check_all.sh
6. Commit               →  git commit (pre-commit hooks run automatically)
```

### Writing feature specs

For any non-trivial feature, create a spec before coding. Use the template at `docs/templates/spec_template.md`:

```bash
# If using Claude Code, the /spec skill runs an interview to generate one:
/spec my-feature-name
```

The spec template covers:

```
Summary          — What and why
Goals            — What success looks like
Non-goals        — What's explicitly excluded
User stories     — As a [role], I want [action] so that [benefit]
Technical design — API changes, data models, config changes, dependencies
Implementation   — Step-by-step build plan
Edge cases       — Error scenarios and handling
Testing strategy — Unit, integration, manual verification
Open questions   — Unresolved decisions
```

### Adding a new endpoint

The standard pattern for adding API endpoints:

**1. Define request/response models** in `src/api/routes.py` (or a dedicated models file):

```python
from __future__ import annotations

from pydantic import BaseModel


class ItemCreate(BaseModel):
    name: str
    description: str | None = None


class ItemResponse(BaseModel):
    id: str
    name: str
    description: str | None
```

**2. Add the endpoint** to `src/api/routes.py`:

```python
from src.utils.errors import AppError, ErrorCode
from src.utils.logger import get_logger

logger = get_logger(__name__)


@router.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(body: ItemCreate) -> ItemResponse:
    """Create a new item."""
    logger.info("item_create_requested", name=body.name)
    # ... implementation ...
    return ItemResponse(id="generated-id", name=body.name, description=body.description)
```

**3. Write tests** in `tests/unit/` and `tests/integration/`:

```python
# tests/integration/test_items_api.py
from fastapi.testclient import TestClient
from main import create_app


def test_create_item():
    client = TestClient(create_app())
    resp = client.post("/api/v1/items", json={"name": "Widget"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Widget"
```

**4. Run checks** before committing:

```bash
bash scripts/check_all.sh
```

If using Claude Code, the `/add-endpoint` skill scaffolds all of this automatically:

```bash
/add-endpoint POST /items create item
```

### Adding configuration

When your feature needs new config values:

**1. Add to `Settings`** in `src/utils/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    my_feature_enabled: bool = False
    my_feature_timeout: int = 30
```

**2. Add to `.env.example`**:

```bash
# Enable the my-feature functionality
MY_FEATURE_ENABLED=false
# Timeout in seconds for my-feature operations
MY_FEATURE_TIMEOUT=30
```

**3. Add to environment YAML** if the default differs per environment:

```yaml
# configs/dev.yaml
my_feature_enabled: true
```

**4. Use via the settings singleton**:

```python
from src.utils.config import settings

if settings.my_feature_enabled:
    # ...
```

**Config precedence** (highest wins): Environment variables > YAML config > hardcoded defaults.

**Important rules** (from `REQ-CFG-006`, `REQ-CFG-007`):
- Never use inline comments in `.env` files — parsers include the comment text as part of the value
- Never store secrets in YAML — use environment variables or a secrets manager
- Never have redundant config flags controlling the same behavior (`REQ-CFG-008`)

---

## 5. Configuration

### Layered config system

The template uses a three-layer configuration system (`src/utils/config.py`):

```
Layer 3 (highest priority): Environment variables (from .env or system)
Layer 2: Environment-specific YAML (configs/{APP_ENV}.yaml)
Layer 1 (lowest priority): Hardcoded defaults in Settings class
```

### Key environment variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `APP_ENV` | `dev`, `staging`, `production`, `test` | `dev` | Active environment |
| `APP_DEBUG` | `true`, `false` | `true` | Debug mode (must be `false` in production) |
| `MODEL_BACKEND` | `mock`, `local`, `cloud` | `mock` | Which model backend to use |
| `SECRET_KEY` | any string | — | Required in production |
| `LOGGING__LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `DEBUG` | Log verbosity |
| `LOGGING__FORMAT` | `console`, `json` | `console` | Log output format |

### Environment-specific configs

| File | Log format | Log level | Workers | Mocks |
|------|-----------|-----------|---------|-------|
| `configs/dev.yaml` | console | DEBUG | 1 (reload) | enabled |
| `configs/staging.yaml` | json | INFO | 2 | disabled |
| `configs/production.yaml` | json | WARNING | 4 | disabled |

### Startup validation

Settings are validated at startup. The application will fail fast on:
- Invalid `APP_ENV` or `MODEL_BACKEND` values
- Production environment with `APP_DEBUG=true`
- Production environment without `SECRET_KEY`

---

## 6. API Development

### Architecture

```
main.py (FastAPI app)
  └── /health            — Health check (direct)
  └── /api/v1/*          — All business endpoints (from src/api/routes.py)
```

All business endpoints are defined in `src/api/routes.py` using a FastAPI `APIRouter`, which is mounted at `/api/v1` in `main.py`.

### Conventions (from common_requirements.md)

| Rule | Requirement |
|------|-------------|
| Request/response models must be Pydantic | `REQ-ERR-001` |
| Errors raised as `AppError`, never raw dicts | `REQ-ERR-001` |
| All endpoints documented with docstrings | `REQ-DOC-001` |
| Validate and sanitize all external inputs | `REQ-SEC-002` |
| Rate limiting on public endpoints | `REQ-SEC-007` |
| Explicit timeouts for external calls | `REQ-ERR-003` |

### Error responses

All errors go through the `AppError` exception handler in `main.py`, producing consistent JSON:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Name field is required",
    "context": {"field": "name"}
  }
}
```

Use the `ErrorCode` enum from `src/utils/errors.py`:

```python
from src.utils.errors import AppError, ErrorCode

raise AppError(
    code=ErrorCode.VALIDATION_ERROR,
    message="Name field is required",
    context={"field": "name"},
)
```

Available error codes: `INTERNAL_ERROR`, `VALIDATION_ERROR`, `NOT_FOUND`, `UNAUTHORIZED`, `RATE_LIMITED`, `CONFIG_INVALID`, `CONFIG_MISSING`, `DATA_LOAD_FAILED`, `DATA_VALIDATION_FAILED`, `MODEL_LOAD_FAILED`, `MODEL_INFERENCE_FAILED`, `EXTERNAL_TIMEOUT`, `EXTERNAL_UNAVAILABLE`.

---

## 7. Data and Models

### Directory structure

```
data/
├── raw/          — Original, immutable data
├── interim/      — Intermediate transformed data
├── processed/    — Final data ready for modeling
└── uploads/      — User-uploaded files

models/           — Saved model artifacts (weights, checkpoints)
```

### Source modules

| Directory | Purpose |
|-----------|---------|
| `src/data/` | Data loading, cleaning, transformation pipelines |
| `src/features/` | Feature engineering and extraction |
| `src/models/` | ML model wrappers (load, predict, evaluate) |
| `src/pipelines/` | Orchestration — ties data, features, and models together |
| `src/evaluation/` | Model evaluation metrics and reporting |

### Key requirements for data/models

| Requirement | What to do |
|-------------|-----------|
| `REQ-DAT-001` | Version datasets using DVC or equivalent |
| `REQ-DAT-002` | Validate pipeline outputs at each stage |
| `REQ-DAT-004` | Store large artifacts in dedicated storage, not Git |
| `REQ-DAT-005` | Track end-to-end data lineage |
| `REQ-SEC-006` | Sign and verify model artifacts |
| `REQ-SEC-009` | Add model weights and binaries to `.gitignore` |
| `REQ-OBS-004` | Use a versioned model registry |
| `REQ-OBS-005–008` | Record training data, code version, hyperparameters, eval metrics per model |
| `REQ-ERR-007` | Set explicit `max_tokens` for every LLM generation call |

### Installing ML dependencies

The ML dependencies (PyTorch, transformers, scikit-learn, etc.) are in an optional extra:

```bash
uv sync --extra dev --extra ml
```

---

## 8. Testing

### Test structure

```
tests/
├── unit/           — Fast, isolated tests (mirrors src/ structure)
├── integration/    — API and cross-module tests
├── evaluation/     — Model quality and performance tests
├── safety/         — Security, adversarial inputs, compliance tests
└── fixtures/       — Shared test data files
```

### Running tests

```bash
# All tests
uv run pytest tests/ -x -q

# By category
uv run pytest tests/unit/ -x -q
uv run pytest tests/integration/ -x -q
uv run pytest tests/evaluation/ -x -q
uv run pytest tests/safety/ -x -q

# Single file
uv run pytest tests/unit/test_config.py -x -q

# Single test
uv run pytest tests/unit/test_config.py::test_defaults -x -q
```

### Testing conventions

- **Use `pytest.fixture()`** for shared setup, not `setUp`/`tearDown`
- **One assertion focus per test** — test one behavior at a time
- **Tests must be independent** — no shared mutable state between tests
- **Use `pytest.raises(AppError)`** for error cases
- **API tests** use a `client` fixture from `TestClient(create_app())`
- **Mirror src/ structure** — `src/data/loader.py` → `tests/unit/test_loader.py`
- **Write at minimum** one happy-path test per endpoint or public function

### Test environment isolation (`REQ-TST-051`)

Tests must be isolated from your `.env` and dev configuration. Override environment variables in your root `conftest.py`:

```python
# tests/conftest.py
import os

os.environ["APP_ENV"] = "test"
os.environ["APP_DEBUG"] = "true"
os.environ["MODEL_BACKEND"] = "mock"
```

Separate mock-calibrated thresholds from real model thresholds (`REQ-TST-052`). Unit tests run against mocks; real model integration tests should be in a separate category.

### What to test (by requirement category)

| Category | Requirements | What to cover |
|----------|-------------|--------------|
| Data/Schema | `REQ-TST-004–009` | Validate schemas, ranges, missing values, distribution drift |
| Unit | `REQ-TST-010–015` | Preprocessing, feature transforms, utilities, error handling |
| Integration | `REQ-TST-016–020` | Pipeline flows, API request/response, clear error messages |
| Model eval | `REQ-TST-021–025` | Target metrics, baseline regression, segment evaluation, invariance |
| GenAI/LLM | `REQ-TST-026–030` | Evaluation criteria, curated prompts, safety probes, regression |
| Performance | `REQ-TST-031–035` | Latency p50/p95/p99, throughput, graceful degradation, timeouts |
| Bias/Safety | `REQ-TST-036–039` | Protected group metrics, harmful failure modes |
| Regression | `REQ-TST-040–043` | Baseline metrics, CI integration, promotion criteria |

---

## 9. Logging and Observability

### Structured logging

The template uses `structlog` for structured logging. Never use `print()` in `src/`.

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Event-style log messages with key-value context
logger.info("model_loaded", model_id="bert-base", load_time_ms=1200)
logger.warning("high_latency", endpoint="/predict", latency_ms=3500)
logger.error("inference_failed", model_id="bert-base", error="OOM")
```

### Log output

- **Development** (`LOGGING__FORMAT=console`): Human-readable colored output
- **Staging/Production** (`LOGGING__FORMAT=json`): Machine-parseable JSON

### Key logging requirements

| Requirement | What to do |
|-------------|-----------|
| `REQ-LOG-001` | Use structured logs (JSON/key-value) with queryable fields |
| `REQ-LOG-002` | Include: timestamp, level, service/component, environment, correlation IDs |
| `REQ-LOG-003` | Add AI-specific fields: prompt_id, model, temperature, latency_ms, token counts |
| `REQ-LOG-004` | Log prompts/completions in a dedicated store for auditing |
| `REQ-LOG-006` | Redact/hash sensitive data before persistence |
| `REQ-LOG-008` | Use standard log levels consistently: DEBUG, INFO, WARN, ERROR |
| `REQ-LOG-009` | Full prompt/response bodies only at DEBUG or in non-prod |
| `REQ-LOG-012` | Centralize logging through the shared logger utility |

### Observability checklist

The common requirements define a comprehensive observability stack. Key areas to implement:

1. **Model registry and lineage** (`REQ-OBS-004–011`) — Track model versions, training data, code, hyperparameters
2. **Data observability** (`REQ-OBS-012–018`) — Schema validation, drift detection, freshness monitoring
3. **Model performance** (`REQ-OBS-019–026`) — Task metrics, business KPIs, latency percentiles, GenAI safety
4. **Distributed tracing** (`REQ-OBS-035–042`) — Trace requests across API, feature store, model server
5. **Alerting and runbooks** (`REQ-OBS-049–054`) — Thresholds for drift, performance drops, safety incidents

---

## 10. Error Handling

### Pattern

All errors use the `AppError` class with an `ErrorCode`:

```python
from src.utils.errors import AppError, ErrorCode

# Raise with context for debugging
raise AppError(
    code=ErrorCode.MODEL_INFERENCE_FAILED,
    message="Model timed out after 30s",
    context={"model_id": "bert-base", "timeout_ms": 30000},
)

# Wrap underlying exceptions
try:
    result = model.predict(input_data)
except TimeoutError as e:
    raise AppError(
        code=ErrorCode.EXTERNAL_TIMEOUT,
        message="Prediction timed out",
        context={"model_id": model.id},
        cause=e,
    )
```

### Rules from requirements

| Requirement | Rule |
|-------------|------|
| `REQ-ERR-001` | Consistent error response format across all APIs |
| `REQ-ERR-002` | Graceful degradation — fallback responses, cached results |
| `REQ-ERR-003` | Explicit timeouts for all external calls |
| `REQ-ERR-004` | Retries with exponential backoff and jitter |
| `REQ-ERR-005` | Log all exceptions with full context (stack trace, request ID) |
| `REQ-ERR-006` | Catch the narrowest exception type needed — no broad `except Exception` |
| `REQ-ERR-007` | Set explicit `max_tokens` for every LLM call |

---

## 11. Security

### Requirements checklist

| Requirement | What to do |
|-------------|-----------|
| `REQ-SEC-001` | Secrets in env vars or secrets manager — never in Git |
| `REQ-SEC-002` | Validate and sanitize all external inputs |
| `REQ-SEC-003` | Prompt injection defenses for LLM inputs (filtering, output validation, system prompt isolation) |
| `REQ-SEC-004` | Least-privilege access controls for services, APIs, data stores |
| `REQ-SEC-005` | Scan container images and dependencies for vulnerabilities |
| `REQ-SEC-006` | Sign and verify model artifacts |
| `REQ-SEC-007` | Rate limiting on public-facing endpoints |
| `REQ-SEC-008` | Periodic security reviews and penetration testing |
| `REQ-SEC-009` | Add model weights, binaries, recordings to `.gitignore` |

### Pre-commit protections

The pre-commit config already includes:
- `detect-private-key` — prevents committing secrets
- `check-added-large-files` — blocks files >1000KB (catches accidental model weight commits)
- `no-commit-to-branch` — prevents direct commits to `main`

---

## 12. Scripts and Automation

### Available scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/setup.sh` | First-time dev environment setup | `bash scripts/setup.sh` |
| `scripts/start_server.sh` | Start the application server | `bash scripts/start_server.sh [dev\|staging\|production]` |
| `scripts/check_all.sh` | Full quality gate (lint + format + typecheck + tests) | `bash scripts/check_all.sh [--fix]` |
| `scripts/git_push.sh` | Commit and push with optional test run | `./scripts/git_push.sh "message" --all [--test]` |
| `scripts/sync_requirements.sh` | Sync requirement controller JSONs | `bash scripts/sync_requirements.sh [--dry-run]` |

### Daily development commands

```bash
# Start coding
bash scripts/start_server.sh                    # Start dev server

# While developing
uv run pytest tests/unit/test_my_feature.py -x  # Run relevant tests frequently

# Before committing
bash scripts/check_all.sh                        # Full quality check
bash scripts/check_all.sh --fix                  # Auto-fix lint/format issues first

# Committing
./scripts/git_push.sh "Add item creation endpoint" --all --test
```

### Script requirements

Scripts must follow these conventions from `REQ-RUN-*`:

- **Resolve project root** before invoking tools (`REQ-RUN-004`)
- **Be idempotent** — detect and stop existing processes before starting (`REQ-RUN-005`)
- **Kill zombie processes** on the target port before binding (`REQ-RUN-009`)
- **Propagate exit codes** for batch jobs (`REQ-RUN-006`)

---

## 13. CI/CD and Quality Gates

### Pre-commit hooks

Installed automatically by `setup.sh`. Run on every commit:

1. **ruff** — Linting with auto-fix (rules: E, F, W, I, N, UP, B, SIM, T20)
2. **ruff-format** — Code formatting (100 char line length)
3. **mypy** — Type checking
4. **check-yaml** / **check-toml** — Config file validation
5. **end-of-file-fixer** / **trailing-whitespace** — Formatting hygiene
6. **check-added-large-files** — Prevents >1000KB files
7. **detect-private-key** — Prevents secret commits
8. **no-commit-to-branch** — Prevents direct commits to `main`

### CI pipeline requirements

From `REQ-CIC-*`:

| Requirement | What to implement |
|-------------|------------------|
| `REQ-CIC-001` | PR quality gates: linting, type checks, unit tests must pass before merge |
| `REQ-CIC-002` | Scheduled integration and evaluation tests (nightly/weekly) |
| `REQ-CIC-003` | Automated deployment to staging and production |
| `REQ-CIC-004` | Post-deploy smoke tests for critical paths |
| `REQ-CIC-005` | Pipelines as code (GitHub Actions, GitLab CI) |
| `REQ-CIC-006` | Pre-commit hooks for large file detection |

### Manual quality check

```bash
# Run everything the CI would check
bash scripts/check_all.sh

# Steps it runs:
# 1. ruff check src/ tests/           (lint)
# 2. ruff format --check src/ tests/  (format)
# 3. mypy src/                         (typecheck)
# 4. pytest tests/ -x -q              (tests)
```

---

## 14. Documentation

### Required documents (from documentation_requirements.md)

| Document | Purpose | Where |
|----------|---------|-------|
| **README.md** | Project anchor — links to all other docs | Project root |
| **Architecture Overview** | System purpose, components, data flows (C4-style) | `docs/architecture/` |
| **Design Specification** | Module responsibilities, interfaces, data models | `docs/design/` |
| **Deployment Runbook** | Environments, CI/CD, config, scaling, SLOs | `docs/runbook/` |
| **App Cheatsheet** | URLs, commands, credentials, config reference | `docs/app_cheatsheet.md` |
| **Feature Specs** | Per-feature design documents | `docs/specs/` |
| **ADRs** | Architecture Decision Records | `docs/adr/` |
| **Troubleshooting Guide** | Commands and procedures for common issues | `docs/` |

### Documentation standards

| Requirement | Standard |
|-------------|---------|
| `REQ-DOC-001` | Docstrings for all public modules, classes, and functions |
| `REQ-DOC-002` | Architecture document with components, data flow, integration points |
| `REQ-DOC-003` | Operational runbooks for deployment, rollback, incident response |
| `REQ-DOC-004` | Changelog with notable changes per release |
| `REQ-DOC-005` | API documentation via OpenAPI/Swagger (auto-generated at `/docs`) |
| `REQ-DOC-006` | Deployment runbook must start with prerequisite installation steps |
| `REQ-DOC-007` | `.env.example` with all required variables and descriptive comments |

### Creating the README

Use `docs/templates/README_template.md` as a starting point. It covers:

```
Overview, Features, Project Structure, Data, Models,
Installation, Usage, Training, Evaluation, Results,
Roadmap, Contributing, License, Contact, Acknowledgements
```

### Generation and review practices

From documentation_requirements.md:

1. **Plan-first** — Outline sections and assumptions before writing full prose
2. **Iterate** — Start coarse (context + containers), refine into components and details
3. **Human checkpoints** — Get review after each phase before proceeding
4. **Self-checks** — Include a Validation/Open Issues section in each document
5. **Traceability** — Map requirements to decisions; maintain traceability tables

---

## 15. Requirements Checklist Reference

This is a summary of all requirement categories from `common_requirements.md`. Use the controller JSONs to track implementation status.

| Category | IDs | Count | Key focus |
|----------|-----|-------|-----------|
| Agent Interaction | REQ-AGT-001–004 | 4 | Planning workflow, troubleshooting docs |
| Logging | REQ-LOG-001–018 | 18 | Structured logs, AI-specific fields, PII redaction |
| Observability | REQ-OBS-001–066 | 66 | Model registry, data quality, performance monitoring, tracing, alerting |
| Testing | REQ-TST-001–053 | 53 | Unit, integration, model eval, GenAI, performance, bias, CI/CD |
| Running the App | REQ-RUN-001–012 | 12 | Scripts, idempotency, zombie processes, readiness endpoints |
| Security | REQ-SEC-001–009 | 9 | Secrets, input validation, prompt injection, rate limiting |
| Configuration | REQ-CFG-001–009 | 9 | Layered config, env separation, startup validation |
| Error Handling | REQ-ERR-001–007 | 7 | Consistent format, graceful degradation, timeouts, retries |
| Dependencies | REQ-DEP-001–006 | 6 | Pinned versions, virtual envs, vulnerability scanning |
| Documentation | REQ-DOC-001–007 | 7 | Docstrings, architecture docs, runbooks, changelog |
| CI/CD | REQ-CIC-001–007 | 7 | Quality gates, scheduled tests, automated deployment |
| Data Management | REQ-DAT-001–005 | 5 | Versioning, validation, retention, artifact storage, lineage |

### Typical implementation order

A pragmatic order for implementing requirements when starting a new project:

1. **Configuration** (REQ-CFG) — Set up layered config, environment separation
2. **Logging** (REQ-LOG-001–003, 008, 012) — Structured logging with core fields
3. **Error Handling** (REQ-ERR) — Consistent error format, timeouts
4. **Security basics** (REQ-SEC-001–002, 009) — Secrets management, input validation, .gitignore
5. **Testing foundation** (REQ-TST-010–015, 051) — Unit tests, environment isolation
6. **API development** (REQ-DOC-005) — Endpoints with OpenAPI docs
7. **CI/CD** (REQ-CIC-001, 005, 006) — PR gates, pipeline as code, pre-commit hooks
8. **Integration tests** (REQ-TST-016–020) — Pipeline and API flow tests
9. **Data management** (REQ-DAT) — Versioning, validation, lineage
10. **Observability** (REQ-OBS) — Metrics, monitoring, alerting (iterative)
11. **Model evaluation** (REQ-TST-021–025) — Performance baselines and regression
12. **Documentation** (REQ-DOC) — Architecture, runbooks, changelog
13. **Advanced testing** (REQ-TST-026–050) — GenAI tests, performance, bias, safety
14. **Advanced observability** (REQ-OBS-035–066) — Tracing, explainability, compliance

---

## Appendix: Python Style Quick Reference

```python
from __future__ import annotations          # Always first import

from typing import TYPE_CHECKING            # Guard type-only imports
if TYPE_CHECKING:
    from fastapi import FastAPI

from collections.abc import Sequence        # Abstract types from here
from enum import StrEnum                    # String enums

type UserID = str                           # Type aliases with 'type'

def process(items: list[str] | None = None) -> dict[str, int]:  # X | Y unions
    """Process items and return counts."""                        # Docstrings on public API
    if items is None:                       # Early returns
        return {}
    # ... implementation
```

**Rules:**
- Line length: 100 characters
- No `print()` in `src/` — use `structlog` via `get_logger(__name__)`
- No bare `except:` — always catch specific exception types
- Use `pathlib.Path` for file paths, not `os.path`
- Use f-strings over `.format()` or `%`
- Use `uv` for all Python operations, never `pip`
