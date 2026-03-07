# Plan: Admin Console for Static File Serving

## Context

The project has a FastAPI server but no static file serving or admin console. The user wants an admin console (API + UI) to manage static file mounts — configure which folders are served, at what URL prefixes, and with what access restrictions.

---

## Status

- [x] Phase 1: Data Layer — Static mount config model + JSON persistence
- [x] Phase 2: Admin API — CRUD endpoints for managing static file mounts
- [x] Phase 3: Dynamic Mounting — Apply/remove StaticFiles mounts at runtime
- [x] Phase 4: Access Control — Optional auth middleware per mount
- [x] Phase 5: Admin UI — HTML admin console served at `/admin`
- [x] Phase 6: Tests
- [x] Phase 7: Documentation updates

---

## Design Decisions

1. **Persistence**: JSON file (`data/static_mounts.json`) — no database needed for this config. Loaded at startup, written on changes.
2. **Dynamic mounting**: FastAPI supports adding routes at runtime. We remount all StaticFiles on each config change (simple, reliable).
3. **Access control**: Three levels — `public` (no auth), `token` (Bearer token in query/header), `admin` (requires admin secret from settings).
4. **Admin UI**: Server-rendered HTML (Jinja2 template) at `/admin/static-files` — no frontend framework needed for a simple admin page.
5. **Security**: Folder paths are validated against an allowed base directory (`data/` by default) to prevent path traversal. Admin endpoints require the admin secret.

---

## Changes Summary

| # | File | Action |
|---|------|--------|
| 1 | `src/admin/__init__.py` | Create |
| 2 | `src/admin/models.py` | Create — Pydantic models for static mount config |
| 3 | `src/admin/repository.py` | Create — JSON file persistence |
| 4 | `src/admin/service.py` | Create — Business logic + mount management |
| 5 | `src/admin/routes.py` | Create — Admin API endpoints |
| 6 | `src/admin/templates/static_files.html` | Create — Admin UI template |
| 7 | `src/utils/errors.py` | Modify — Add MOUNT_FAILED, MOUNT_NOT_FOUND error codes |
| 8 | `src/utils/config.py` | Modify — Add AdminSettings |
| 9 | `main.py` | Modify — Mount admin routes, load saved mounts on startup |
| 10 | `tests/unit/test_static_mount_repository.py` | Create |
| 11 | `tests/integration/test_admin_api.py` | Create |
| 12 | `docs/app_cheatsheet.md` | Modify — Add admin endpoints |

**9 new files, 3 modifications.**

---

## Phase 1: Data Layer

### 1. `src/admin/__init__.py` — Empty

### 2. `src/admin/models.py` — Pydantic models

```python
class AccessLevel(StrEnum):
    PUBLIC = "public"
    TOKEN = "token"
    ADMIN = "admin"

class StaticMount(BaseModel):
    id: str                    # UUID, auto-generated
    folder_path: str           # Absolute or relative to PROJECT_ROOT
    url_prefix: str            # e.g., "/static", "/files"
    access_level: AccessLevel  # public | token | admin
    access_token: str | None   # Required when access_level == "token"
    enabled: bool              # Can be disabled without deleting
    created_at: datetime
    updated_at: datetime

class StaticMountCreate(BaseModel):
    folder_path: str
    url_prefix: str
    access_level: AccessLevel = AccessLevel.PUBLIC
    access_token: str | None = None
    enabled: bool = True

class StaticMountUpdate(BaseModel):
    folder_path: str | None = None
    url_prefix: str | None = None
    access_level: AccessLevel | None = None
    access_token: str | None = None
    enabled: bool | None = None
```

### 3. `src/admin/repository.py` — JSON file read/write

- `load() -> list[StaticMount]` — read from `data/static_mounts.json`
- `save(mounts: list[StaticMount])` — write to JSON file
- `get(mount_id: str) -> StaticMount | None`
- `add(mount: StaticMount)` — append and save
- `update(mount_id: str, data: StaticMountUpdate) -> StaticMount`
- `delete(mount_id: str)`

---

## Phase 2: Admin API

### 4. `src/admin/routes.py` — CRUD endpoints at `/api/v1/admin/static-mounts`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/static-mounts` | List all mounts |
| `POST` | `/admin/static-mounts` | Create a mount |
| `GET` | `/admin/static-mounts/{id}` | Get one mount |
| `PATCH` | `/admin/static-mounts/{id}` | Update a mount |
| `DELETE` | `/admin/static-mounts/{id}` | Delete a mount |
| `POST` | `/admin/static-mounts/{id}/toggle` | Enable/disable a mount |
| `POST` | `/admin/static-mounts/reload` | Re-apply all mounts |

All admin endpoints require `X-Admin-Secret` header matching `settings.admin.secret_key`.

---

## Phase 3: Dynamic Mounting

### 5. `src/admin/service.py` — Mount manager

- Validates folder exists and is under allowed base dirs
- Validates url_prefix doesn't conflict with existing API routes
- `apply_mounts(app: FastAPI)` — clears old static mounts, adds new ones from config
- Uses `FastAPI.mount(prefix, StaticFiles(directory=path))` for each enabled mount
- For token/admin access levels, wraps with a middleware sub-app that checks auth

---

## Phase 4: Access Control

In `service.py`, when `access_level != public`:
- Wrap `StaticFiles` in a small ASGI middleware that checks:
  - `token`: Bearer token in `Authorization` header or `?token=` query param
  - `admin`: `X-Admin-Secret` header matching `settings.admin.secret_key`
- Returns 401 if auth fails

---

## Phase 5: Admin UI

### 6. `src/admin/templates/static_files.html`

- Served at `/admin/static-files` (HTML GET endpoint in admin routes)
- Simple HTML + vanilla JS (no framework)
- Table listing all mounts with status, folder, prefix, access level
- Forms to create/edit/delete mounts
- Toggle enable/disable buttons
- Calls the admin API endpoints via `fetch()`

---

## Phase 6: Tests

### 7. `tests/unit/test_static_mount_repository.py`
- Test CRUD operations on the JSON repository
- Test loading from empty/missing file
- Test duplicate url_prefix detection

### 8. `tests/integration/test_admin_api.py`
- Test all CRUD endpoints
- Test auth requirement (missing/wrong secret returns 401)
- Test path traversal prevention
- Test that created mount actually serves files
- Test enable/disable toggle

---

## Phase 7: Documentation

### 9. Update `docs/app_cheatsheet.md`
- Add admin endpoints table
- Add `ADMIN__SECRET_KEY` env var
- Add `ADMIN__ALLOWED_BASE_DIRS` env var

### 10. Update `src/utils/config.py`
- Add `AdminSettings` with `secret_key`, `allowed_base_dirs`, `mounts_file`

### 11. Update `src/utils/errors.py`
- Add `MOUNT_FAILED`, `MOUNT_NOT_FOUND`, `MOUNT_CONFLICT` error codes

---

## Implementation Order

1. Phase 1 (models + repository) — foundation
2. Phase 3 (service) — depends on models
3. Phase 2 (API routes) — depends on service
4. Phase 4 (access control) — enhancement to service
5. Phase 5 (admin UI) — depends on API
6. Phase 6 (tests) — after all code is in place
7. Phase 7 (docs) — final
