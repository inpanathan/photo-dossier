# App Cheatsheet

## Setup

```bash
# First-time project setup (installs deps, copies .env, installs pre-commit, runs tests)
bash scripts/setup.sh

# Or manual setup:
uv sync --extra dev
cp .env.example .env          # edit with your settings
uv run pre-commit install
```

## Server

```bash
# Start dev server (hot-reload, console logging)
./scripts/start_server.sh

# Start in staging/production mode
./scripts/start_server.sh staging
./scripts/start_server.sh production

# Or run directly
uv run python main.py
```

### URLs (dev mode)

| URL | Description |
|-----|-------------|
| http://localhost:8000/health | Health check |
| http://localhost:8000/docs | Swagger UI (debug only) |
| http://localhost:8000/redoc | ReDoc (debug only) |

## Testing

```bash
# Run all tests
uv run pytest tests/ -x -q

# Run specific test category
uv run pytest tests/unit/ -x -q
uv run pytest tests/integration/ -x -q
uv run pytest tests/safety/ -x -q

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

## Linting & Type Checking

```bash
# Lint (with auto-fix)
uv run ruff check src/ tests/ --fix

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/ --ignore-missing-imports
```

## Git Workflow

```bash
# Quick commit and push
./scripts/git_push.sh "your commit message" --all

# Commit with tests
./scripts/git_push.sh "your commit message" --all --test

# Just check status
./scripts/git_push.sh --status
```

## Requirements Sync

Syncs `docs/requirements/*_controller.json` from the corresponding `*_requirements.md` files. Preserves any `implement`/`enable` flags already set to `"Y"`.

```bash
# Preview changes (no files written)
./scripts/sync_requirements.sh --dry-run

# Apply changes (syncs both common + documentation)
./scripts/sync_requirements.sh

# Sync only one file
./scripts/sync_requirements.sh --file common
./scripts/sync_requirements.sh --file documentation
```
