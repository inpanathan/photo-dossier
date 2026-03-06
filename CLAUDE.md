# AI/ML Project Template

## Commands

```bash
# Dev server
uv run python main.py

# Tests (prefer running single test files, not the full suite)
uv run pytest tests/ -x -q                          # all tests
uv run pytest tests/unit/ -x -q                     # unit only
uv run pytest tests/integration/ -x -q              # integration only
uv run pytest tests/unit/test_foo.py -x -q           # single file
uv run pytest tests/unit/test_foo.py::test_bar -x -q # single test

# Lint and typecheck
uv run ruff check src/ tests/                       # lint
uv run ruff check src/ tests/ --fix                 # lint + autofix
uv run ruff format src/ tests/                      # format
uv run mypy src/ --ignore-missing-imports            # typecheck

# Full quality check (run before committing)
bash scripts/check_all.sh                            # lint + format + typecheck + tests
bash scripts/check_all.sh --fix                      # same, but auto-fix lint/format first

# Dependencies
uv sync --extra dev                                  # install dev deps
uv sync --extra dev --extra ml                       # install dev + ML deps
uv add <package>                                     # add a dependency

# Requirements sync
bash scripts/sync_requirements.sh                    # sync requirement controllers
bash scripts/sync_requirements.sh --dry-run          # preview changes
```

## Code style

- Python 3.12+, use modern syntax (`type X = ...`, `X | Y` unions, `StrEnum`)
- Line length: 100 characters
- Use `from __future__ import annotations` in every module
- ES-style imports: `from src.utils.config import settings` (not relative)
- Ruff rules: E, F, W, I, N, UP, B, SIM, T20 — no `print()` in src/ (use structlog)
- Type hints on all function signatures; use `TYPE_CHECKING` for import-only types
- Pydantic models for all data structures that cross boundaries (API, config, serialization)

## Architecture

- **Entry point**: `main.py` — creates FastAPI app, mounts routes at `/api/v1`
- **Config**: `src/utils/config.py` — layered: defaults < `configs/{APP_ENV}.yaml` < env vars. Import `settings` singleton
- **Logging**: `src/utils/logger.py` — structlog. Use `get_logger(__name__)`, log with `logger.info("event_name", key=value)`
- **Errors**: `src/utils/errors.py` — raise `AppError(code=ErrorCode.X, message="...", context={...})`
- **Routes**: `src/api/routes.py` — add endpoints to `router`, they mount at `/api/v1`
- **Source modules**: `src/data/`, `src/models/`, `src/features/`, `src/pipelines/`, `src/evaluation/`

## Patterns to follow

- New endpoints: add to `src/api/routes.py`, follow existing FastAPI patterns, include request/response Pydantic models
- New config values: add to `Settings` or a nested `*Settings` class in `src/utils/config.py`, then use via `settings.x`
- Error handling: raise `AppError` with an `ErrorCode`, never return raw dicts with error info
- Logging: always use structlog, never `print()`. Use event-style names: `logger.info("model_loaded", model_id=...)`
- Tests: mirror src/ structure in tests/. Use `pytest.fixture()` for shared setup. Integration tests get a `client` fixture from `TestClient`

## Lessons learned (apply to all work)

These are hard-won lessons from real implementation sessions. Violating them causes real bugs.

### Configuration gotchas
- **YAML constructor kwargs override env vars** in pydantic-settings. Never store secrets in YAML — env vars must be the final authority for sensitive values
- **Never inline comments in `.env` files** — parsers include comment text as part of the value
- **Use `__` (double underscore) for nested env vars** — e.g., `MONITOR__LLM_API_KEY` maps to `settings.monitor.llm_api_key`

### Deployment & scripts
- **Idempotent != safe to re-run** — sentinel files prevent step re-execution but don't detect downstream state. Check for running services before destructive operations
- **Head-first sequential start for distributed systems** — start head node, poll readiness, then start workers. Don't start all nodes simultaneously
- **Kill zombie processes before port binding** — `lsof -ti:<PORT> | xargs kill` before starting services. Prevents `EADDRINUSE`
- **Scripts must resolve project root** — scripts in `scripts/` must `cd` to project root before invoking tools that expect root-relative paths

### Testing
- **Dev and test Docker stacks use different ports** — never share ports between dev and test infrastructure
- **Test doubles subclass real clients** — override network methods, not the entire class. Keeps tests close to production behavior
- **Adding global handlers/middleware breaks tests** — new middleware can change handler counts or ordering. Always verify existing tests after adding globals
- **Optional service missing key = runtime error, not startup crash** — apps should work without optional services (e.g., LLM). Only fail when the optional feature is actually invoked

### Resilience patterns
- **Multi-level graceful fallback** — when multiple data sources exist, cascade through them: primary → secondary → static → default. Never crash from missing data
- **TTL caches for all external data** — always define TTL; never cache forever. Prevents hammering external services
- **In-memory state is session-scoped** — document what doesn't persist across restarts. Config defaults are the fallback

## Workflow

- Use `uv` for all Python operations, never `pip` or `pip install`
- Run lint + typecheck + tests before committing
- Write tests for new functionality — at minimum, one happy-path test per endpoint or public function
- When compacting, preserve: list of modified files, failing test output, current task progress, architectural decisions made
- Before ending a session on a long task, write progress to `.claude/scratchpad/<branch-name>.md`
- Use subagents for broad codebase exploration to keep main context clean
- Pre-commit hooks run ruff (lint+format) and mypy automatically on commit
- **Lessons learned**: After resolving a non-trivial debugging session, document problem, root cause, and solution in `docs/troubleshooting.md` with the commands used (REQ-AGT-004)
- **Cheatsheet maintenance**: When creating new scripts, commands, API endpoints, or config variables, update `docs/app_cheatsheet.md` before the task is complete
- **Runbook maintenance**: When adding alert types, operational procedures, or failure modes, create/update the corresponding runbook in `docs/runbook/`
- **Parallel sessions**: For independent tasks, use `claude --worktree <name>` to run isolated sessions with separate git worktrees. Each session gets its own copy of the repo — no merge conflicts
- **Model selection**: Use Opus for complex multi-file architectural work. Subagents default to Sonnet (fast, cost-effective). Use Haiku for exploration-only agents
- **Verification**: After implementation, use the `verify-app` agent or `/run-checks` to validate before committing. Give Claude a way to verify its work — this 2-3x the quality of results
- **Post-implementation cleanup**: Use the `code-simplifier` agent after completing a feature to reduce complexity before the PR
- **Autonomous mode**: When the user says "run autonomously", "run this autonomously", or similar, operate without asking permission for routine read-only operations. This includes: reading files, grepping/searching code, listing directories, running tests, running lint/typecheck, git status/log/diff, and exploring the codebase with subagents. Only pause for confirmation on **destructive or irreversible actions** (deleting files, git push, modifying shared infrastructure, dropping data) or **ambiguous design decisions** where multiple valid approaches exist. The goal is uninterrupted flow — don't ask "shall I look at X?" just look at it.
- **Task summaries**: After completing any non-trivial task, write a summary to `coding-agent/summaries/<NNN>-<short-name>.md` where `<NNN>` is the next sequential number (zero-padded to 3 digits). The summary must include: date, task description, what was produced (files/artifacts), key decisions made, and any known considerations or follow-ups. This provides a searchable history of all work done on the project

## Project structure

```
├── main.py                  # FastAPI entry point
├── src/
│   ├── api/routes.py        # API endpoints (mounted at /api/v1)
│   ├── data/                # Data loading and processing
│   ├── models/              # ML model wrappers
│   ├── features/            # Feature engineering
│   ├── pipelines/           # Orchestration logic
│   ├── evaluation/          # Model evaluation
│   └── utils/
│       ├── config.py        # Layered config (Settings singleton)
│       ├── logger.py        # Structured logging setup
│       └── errors.py        # AppError + ErrorCode enum
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # API/integration tests
│   ├── evaluation/          # Model evaluation tests
│   ├── safety/              # Safety and security tests
│   └── fixtures/            # Shared test data
├── configs/                 # Per-environment YAML configs
├── scripts/                 # Setup, deployment, utility scripts
├── docs/                    # Requirements, ADRs, runbooks
├── data/                    # raw/, interim/, processed/, uploads/
└── models/                  # Saved model artifacts
```

## Available skills

- `/run-checks` — full quality pipeline (lint, format, typecheck, tests)
- `/fix-issue 123` — end-to-end GitHub issue fix with tests and PR
- `/add-endpoint GET /items list items` — scaffold endpoint + models + tests
- `/review-code src/api/` — security and quality review (runs in isolated context)
- `/review-pr` — review current branch changes against main
- `/spec feature-name` — interview-driven feature spec to `docs/specs/`
- `/explain-code src/utils/config.py` — visual explanation with diagrams
- `/sync-requirements` — sync requirement controller JSONs from markdown

## Requirements-driven development

All requirements files under `docs/requirements/` are authoritative sources for what must be implemented:

- `docs/requirements/common_requirements.md` — cross-cutting standards (logging, observability, testing, security, config, errors, CI/CD, data management, documentation)

When implementing any feature, consult the relevant requirements files and their controller JSONs (`*_controller.json`). Only requirements with `"implement": "Y"` and `"enable": "Y"` in the controller are in scope. Ensure the implementation satisfies the requirement text, not just the summary.

## Planning rule

**Always create a plan before any implementation work.** This is mandatory, no exceptions.

1. **Create the plan first**: Before writing any code, produce a detailed implementation plan with numbered steps, sub-steps, files to create/modify, and acceptance criteria. Write the plan to `coding-agent/plans/<N>-<feature-or-branch-name>.md`, where `<N>` is the next sequential number (check existing files to determine the next number, starting from 1). This numbered sequence provides a clear history of all plans followed in the project.
2. **Get user approval**: Present the plan to the user and wait for explicit approval before proceeding. Do not start implementation until the user confirms.
3. **Maintain status**: As implementation progresses, update the plan file with status markers against each step:
   - `[ ]` — not started
   - `[~]` — in progress
   - `[x]` — completed
   - `[!]` — blocked (include reason)
4. **Report progress**: When resuming work or after completing a major step, summarize current plan status to the user.
5. **Plan changes**: If the plan needs to change mid-implementation (new requirements, blockers, design pivots), update the plan, highlight what changed, and get user re-approval before continuing.

## Key references

See @pyproject.toml for dependencies and tool config.
See @docs/app_cheatsheet.md for dev URLs, credentials, and operational commands.
See @docs/requirements/common_requirements.md for project standards.
See @docs/lessons-learned.md for consolidated lessons from implementation sessions.
