# API Contract — Dossier v2

**Base URL**: `/api/v1`
**Auth**: JWT Bearer token (optional in dev mode). Admin endpoints require `X-Admin-Secret` header.

---

## Authentication

### POST /auth/token

Issue a JWT token.

**Request** (JSON):
```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

**Response** `200`:
```json
{
  "token": "eyJ...",
  "expires_in": 86400
}
```

**Errors**: `401 UNAUTHORIZED`

---

### GET /auth/verify

Verify a JWT token.

**Query params**: `authorization` (required) — the token string.

**Response** `200`:
```json
{
  "valid": true,
  "payload": { "user_id": "user@example.com", "role": "user", "exp": 1741315200 }
}
```

**Errors**: `401 UNAUTHORIZED` (expired or invalid token)

---

## Detection

### POST /detect

Detect human and pet faces in an uploaded image.

**Request**: `multipart/form-data`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | yes | Image file (JPEG, PNG, HEIC) |

**Response** `200` — `DetectionResult`:
```json
{
  "faces": [
    {
      "subject_type": "human",
      "confidence": 0.97,
      "bbox": { "x": 120, "y": 80, "width": 200, "height": 250 }
    }
  ],
  "image_width": 1920,
  "image_height": 1080
}
```

**Errors**: `503 INFERENCE_SERVICE_UNAVAILABLE`

---

## Query / Retrieval

### POST /query

Query the corpus for matching faces.

**Request**: `multipart/form-data`
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `image` | file | yes | — | Reference photo |
| `subject_type` | string | no | `human` | `human` or `pet` |
| `bbox_x` | float | no | — | Bounding box X (if selecting a specific face) |
| `bbox_y` | float | no | — | Bounding box Y |
| `bbox_w` | float | no | — | Bounding box width |
| `bbox_h` | float | no | — | Bounding box height |
| `threshold` | float | no | config | Minimum similarity threshold |
| `top_k` | int | no | config | Max results to return |

**Response** `200` — `QueryResponse`:
```json
{
  "session_id": "sess_abc123",
  "total_results": 42,
  "results": [
    {
      "face_id": "f_001",
      "image_id": "img_001",
      "image_path": "participant_a/IMG_001.jpg",
      "similarity_score": 0.94,
      "subject_type": "human",
      "bbox": { "x": 100, "y": 50, "width": 180, "height": 220 },
      "metadata": {
        "timestamp": "2026-01-15T09:30:00",
        "location_name": "Central Park",
        "camera_model": "iPhone 15 Pro"
      }
    }
  ]
}
```

**Errors**: `503 INFERENCE_SERVICE_UNAVAILABLE`

---

## Pipeline

### POST /pipeline

Run the full pipeline: detect → query → timeline → dossier. Returns a job ID.

**Request**: `multipart/form-data` — same fields as `/query` plus:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `generate_narrative` | bool | no | `true` | Whether to generate the LLM narrative |

**Response** `200`:
```json
{
  "job_id": "job_xyz789",
  "status": "pending"
}
```

Poll `/jobs/{job_id}` or subscribe to `/jobs/{job_id}/stream` for progress. The final job result contains:
```json
{
  "session_id": "sess_abc123",
  "total_results": 42,
  "timeline": { "..." },
  "patterns": [ "..." ],
  "dossier": { "..." }
}
```

---

## Dossier

### POST /dossier

Generate a dossier from a previous query session. Returns a job ID.

**Request** (JSON):
```json
{
  "session_id": "sess_abc123",
  "subject_type": "human"
}
```

**Response** `200`:
```json
{
  "job_id": "job_xyz789",
  "status": "pending"
}
```

---

## Indexing

### POST /index

Start batch indexing of the photo corpus. Returns a job ID.

**Request** (JSON):
```json
{
  "corpus_dir": null,
  "incremental": true
}
```

- `corpus_dir`: Override default corpus directory (optional).
- `incremental`: Skip already-indexed images (default `true`).

**Response** `200`:
```json
{
  "job_id": "job_idx001",
  "status": "pending"
}
```

---

### GET /index/stats

Get index statistics.

**Response** `200`:
```json
{
  "total_images": 102345,
  "total_faces": 98765,
  "human_faces": 87654,
  "pet_faces": 11111,
  "human_vectors": 87654,
  "pet_vectors": 11111,
  "index_type": "flat"
}
```

**Errors**: `503 INDEX_NOT_LOADED`

---

## Jobs

### GET /jobs

List all jobs with optional filters.

**Query params**:
| Param | Type | Description |
|-------|------|-------------|
| `job_type` | string | Filter by type: `index`, `query`, `dossier` |
| `status` | string | Filter by status: `pending`, `running`, `completed`, `failed`, `cancelled` |

**Response** `200`:
```json
{
  "jobs": [
    {
      "id": "job_xyz789",
      "type": "dossier",
      "status": "running",
      "progress": 0.5,
      "message": "Describing photos with VLM...",
      "created_at": "2026-03-07T10:00:00Z",
      "updated_at": "2026-03-07T10:01:30Z"
    }
  ]
}
```

---

### GET /jobs/{job_id}

Get job status and progress.

**Response** `200` — `Job`:
```json
{
  "id": "job_xyz789",
  "type": "dossier",
  "status": "completed",
  "progress": 1.0,
  "message": "Done",
  "result": { "..." },
  "error": null,
  "created_at": "2026-03-07T10:00:00Z",
  "updated_at": "2026-03-07T10:02:00Z"
}
```

**Errors**: `404 JOB_NOT_FOUND`

---

### GET /jobs/{job_id}/stream

Stream job progress via Server-Sent Events (SSE).

**Response** `200` — `text/event-stream`:
```
data: {"status": "running", "progress": 0.3, "message": "Building timeline..."}

data: {"status": "running", "progress": 0.8, "message": "Generating narrative dossier..."}

data: {"status": "completed", "progress": 1.0, "result": {...}, "error": null}
```

**Errors**: `404 JOB_NOT_FOUND`

---

### POST /jobs/{job_id}/cancel

Cancel a running job.

**Response** `200`:
```json
{
  "job_id": "job_xyz789",
  "status": "cancelled"
}
```

**Errors**: `404 JOB_NOT_FOUND` (not found or already completed)

---

## Media

### GET /media/{path}

Serve images from the corpus directory. Path traversal is prevented.

**Response** `200`: Binary image file with appropriate `Content-Type`.

**Errors**: `400 VALIDATION_ERROR` (path traversal attempt), `404 NOT_FOUND`

---

## Photo Upload

### POST /photos/upload

Standard single-file upload.

**Request**: `multipart/form-data`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | yes | Image file (JPEG, PNG, HEIC, max 20MB) |
| `metadata_json` | string | no | JSON string with client-provided metadata |

**Response** `200`:
```json
{
  "photo_id": "ph_abc123",
  "filename": "IMG_001.jpg",
  "size_bytes": 4523000,
  "content_type": "image/jpeg",
  "metadata": { "timestamp": "2026-01-15T09:30:00", "has_gps": true }
}
```

**Errors**: `400 UNSUPPORTED_IMAGE_FORMAT`, `400 IMAGE_TOO_LARGE`

---

### POST /photos/upload/init

Initialize a resumable upload session for large files or mobile uploads.

**Request** (JSON):
```json
{
  "filename": "IMG_001.jpg",
  "total_size": 15000000,
  "content_type": "image/jpeg"
}
```

**Response** `200`:
```json
{
  "session_id": "up_sess_abc123",
  "filename": "IMG_001.jpg",
  "total_size": 15000000,
  "received_bytes": 0,
  "complete": false
}
```

---

### PATCH /photos/upload/{session_id}

Upload a chunk for a resumable session.

**Request**: `multipart/form-data`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chunk` | file | yes | Chunk data |
| `offset` | int | yes | Byte offset for this chunk |

**Response** `200`:
```json
{
  "session_id": "up_sess_abc123",
  "received_bytes": 5000000,
  "complete": false
}
```

When the final chunk completes (`received_bytes == total_size`):
```json
{
  "session_id": "up_sess_abc123",
  "received_bytes": 15000000,
  "complete": true,
  "photo_id": "ph_abc123"
}
```

**Errors**: `404 UPLOAD_SESSION_NOT_FOUND`, `400 UPLOAD_CHUNK_INVALID`

---

### GET /photos/upload/{session_id}/status

Check resumable upload progress.

**Response** `200`:
```json
{
  "session_id": "up_sess_abc123",
  "received_bytes": 5000000,
  "total_size": 15000000,
  "complete": false
}
```

**Errors**: `404 UPLOAD_SESSION_NOT_FOUND`

---

## Health & Readiness

### GET /health

Liveness probe. Always returns `200` if the process is running.

```json
{
  "status": "ok",
  "env": "dev",
  "version": "0.1.0"
}
```

### GET /ready

Readiness probe. Returns whether ML services are initialized.

```json
{
  "ready": true,
  "services": {
    "inference_client": true,
    "index_manager": true
  },
  "env": "dev"
}
```

---

## Error Response Format

All errors follow a consistent structure:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable description",
  "context": {}
}
```

### Error Codes → HTTP Status Mapping

| Error Code | HTTP Status |
|------------|-------------|
| `VALIDATION_ERROR` | 400 |
| `UNSUPPORTED_IMAGE_FORMAT` | 400 |
| `IMAGE_TOO_LARGE` | 400 |
| `UPLOAD_CHUNK_INVALID` | 400 |
| `UPLOAD_SIZE_EXCEEDED` | 400 |
| `UNAUTHORIZED` | 401 |
| `NOT_FOUND` | 404 |
| `SESSION_NOT_FOUND` | 404 |
| `JOB_NOT_FOUND` | 404 |
| `UPLOAD_SESSION_NOT_FOUND` | 404 |
| `SESSION_EXPIRED` | 410 |
| `NO_FACE_DETECTED` | 422 |
| `RATE_LIMITED` | 429 |
| `INDEX_NOT_LOADED` | 503 |
| `INFERENCE_SERVICE_UNAVAILABLE` | 503 |
| `VLM_UNAVAILABLE` | 503 |
| `LLM_UNAVAILABLE` | 503 |
| `JOB_TIMEOUT` | 504 |

---

## Data Models

### SubjectType (enum)
`"human"` | `"pet"`

### BoundingBox
```json
{ "x": 120, "y": 80, "width": 200, "height": 250 }
```

### Match
```json
{
  "face_id": "string",
  "image_id": "string",
  "image_path": "string",
  "similarity_score": 0.94,
  "subject_type": "human",
  "bbox": { "x": 100, "y": 50, "width": 180, "height": 220 },
  "metadata": { "timestamp": "...", "location_name": "...", "camera_model": "..." }
}
```

### Timeline
```json
{
  "days": [
    {
      "date": "2026-01-15",
      "entries": [ "..." ],
      "scenes": [ { "label": "morning", "entries": ["..."] } ]
    }
  ],
  "gaps": [ { "start": "2026-01-16", "end": "2026-01-18", "gap_days": 2 } ],
  "total_entries": 42,
  "active_days": 5
}
```

### Dossier
```json
{
  "executive_summary": "...",
  "date_range": "Jan 15 - Jan 20, 2026",
  "subject_type": "human",
  "days": [
    {
      "date": "2026-01-15",
      "day_summary": "...",
      "entries": [
        {
          "time": "09:30",
          "location": "Central Park",
          "description": "...",
          "image_url": "/api/v1/media/participant_a/IMG_001.jpg",
          "confidence": 0.94
        }
      ]
    }
  ],
  "patterns": [
    {
      "pattern_type": "recurring_location",
      "description": "Subject visits Central Park most mornings",
      "confidence": 0.85
    }
  ]
}
```

### Job
```json
{
  "id": "job_xyz789",
  "type": "dossier",
  "status": "completed",
  "progress": 1.0,
  "message": "Done",
  "result": {},
  "error": null,
  "created_at": "2026-03-07T10:00:00Z",
  "updated_at": "2026-03-07T10:02:00Z"
}
```

### JobType (enum)
`"index"` | `"query"` | `"dossier"`

### JobStatus (enum)
`"pending"` | `"running"` | `"completed"` | `"failed"` | `"cancelled"`
