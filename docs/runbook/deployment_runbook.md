# Deployment & Operational Runbook — Dossier v2

**Version**: 1.0
**Date**: 2026-03-06
**Architecture**: `docs/architecture/architecture_overview.md`
**Design**: `docs/design/design_specification.md`

---

## 1. Prerequisites

Install these before any other step.

### 1.1 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 22.04+ / macOS 13+ | Ubuntu 24.04 LTS |
| Python | 3.12+ | 3.12 |
| GPU | NVIDIA GPU with 8GB+ VRAM | NVIDIA GPU with 24GB+ VRAM |
| CUDA | 12.1+ | 12.4 |
| RAM | 16 GB | 32 GB |
| Disk | 50 GB free (+ corpus size) | 200 GB SSD |
| Node.js | 18+ (for web frontend) | 20 LTS |

### 1.2 System Package Installation

```bash
# Ubuntu
sudo apt update && sudo apt install -y \
  build-essential \
  python3.12 python3.12-venv python3.12-dev \
  libgl1-mesa-glx libglib2.0-0 \
  libsm6 libxext6 libxrender1 \
  libjpeg-dev libpng-dev \
  sqlite3 \
  nginx \
  curl git

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js (for web frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify GPU (if applicable)
nvidia-smi
```

### 1.3 CUDA Installation

Follow NVIDIA's official guide for your OS:
- [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
- [cuDNN](https://developer.nvidia.com/cudnn)

Verify:
```bash
nvcc --version
python3 -c "import torch; print(torch.cuda.is_available())"
```

---

## 2. First-Time Setup

### 2.1 Clone and Configure

```bash
git clone <repo-url> dossier
cd dossier

# Backend setup
cd backend
bash scripts/setup.sh        # installs deps, copies .env, installs pre-commit
cp .env.example .env          # edit with your settings (see Section 2.2)

# Install all dependency groups
uv sync --extra dev --extra ml

# Web frontend setup
cd ../web
npm install

cd ..
```

### 2.2 Environment Configuration

Edit `backend/.env`:

```bash
# Application
APP_ENV=dev                              # dev | staging | production
APP_DEBUG=true                           # false in production
SECRET_KEY=<generate-a-random-string>    # required in production

# Corpus
CORPUS__DIR=/path/to/photo/corpus        # absolute path to image directory

# Detection Models
DETECTION__HUMAN_MODEL=insightface       # insightface | mock
DETECTION__PET_MODEL=yolov8              # yolov8 | mock
DETECTION__DEVICE=auto                   # auto | cpu | cuda

# Index
INDEX__FAISS_INDEX_DIR=data/indices
INDEX__METADATA_DB_PATH=data/metadata.db
INDEX__HUMAN_SIMILARITY_THRESHOLD=0.6
INDEX__PET_SIMILARITY_THRESHOLD=0.5

# Narrative
NARRATIVE__LLM_MODEL=claude              # claude | qwen | llama
NARRATIVE__LLM_API_KEY=<your-api-key>    # NEVER put this in YAML
NARRATIVE__VLM_MODEL=qwen-2.5-vl

# Admin
ADMIN__SECRET_KEY=<generate-a-random-string>
```

### 2.3 Download Model Weights

```bash
cd backend
bash scripts/download_models.sh
```

This downloads:
- InsightFace RetinaFace + ArcFace models (~500MB)
- YOLOv8 pet face detection model (~50MB)
- DINOv2 model (~1.2GB)
- VLM model (if running locally, ~15-40GB depending on variant)

### 2.4 Initialize Data Directories

```bash
bash scripts/init_data.sh
```

Creates: `data/corpus/`, `data/indices/`, `data/uploads/`, `data/logs/`

### 2.5 Verify Installation

```bash
# Run tests
uv run pytest tests/ -x -q

# Start backend and verify health
bash scripts/start_server.sh
curl http://localhost:8000/health

# Start frontend dev server
cd ../web
npm run dev
# Visit http://localhost:3000
```

---

## 3. Corpus Preparation

### 3.1 Directory Structure

Place images in the configured `CORPUS__DIR`:

```
/path/to/corpus/
  participant_a/
    IMG_001.jpg
    IMG_002.jpg
    ...
  participant_b/
    ...
  distractors/
    random_001.jpg
    ...
```

Flat directory structure also supported — the scanner is recursive.

### 3.2 Ground-Truth Manifest

Create `data/ground_truth.json`:

```json
{
  "subjects": [
    {
      "id": "participant_a",
      "name": "Alice",
      "subject_type": "human",
      "reference_photo": "participant_a/IMG_001.jpg",
      "photos": [
        "participant_a/IMG_001.jpg",
        "participant_a/IMG_002.jpg",
        "participant_a/IMG_003.jpg"
      ]
    },
    {
      "id": "alice_dog",
      "name": "Buddy",
      "subject_type": "pet",
      "reference_photo": "participant_a/PET_001.jpg",
      "photos": [
        "participant_a/PET_001.jpg",
        "participant_a/PET_002.jpg"
      ]
    }
  ]
}
```

### 3.3 Index the Corpus

```bash
# Full indexing (first time)
bash scripts/index_corpus.sh

# Incremental indexing (after adding new images)
bash scripts/index_corpus.sh --incremental

# Check index stats
curl http://localhost:8000/api/v1/index/stats
```

Expected output during indexing:
```
[INFO] Starting corpus indexing: /path/to/corpus
[INFO] Scanning directory... found 1,023,456 images
[INFO] Processing batch 1/1024 (1000 images)
[INFO]   Human faces detected: 847
[INFO]   Pet faces detected: 23
[INFO] Progress: 0.1% (1000/1023456) ETA: 3h 20m
...
[INFO] Indexing complete. Total: 1,023,456 images, 987,654 human faces, 34,567 pet faces
```

---

## 4. Starting the Application

### 4.1 Development

Terminal 1 — Backend:
```bash
cd backend
bash scripts/start_server.sh
# Runs: uvicorn with --reload on port 8000
```

Terminal 2 — Frontend:
```bash
cd web
npm run dev
# Runs: Vite dev server on port 3000, proxies /api to backend
```

### 4.2 Staging

```bash
cd backend
bash scripts/start_server.sh staging
# Runs: uvicorn with 2 workers on port 8000
```

### 4.3 Production

```bash
# Backend
cd backend
bash scripts/start_server.sh production
# Runs: gunicorn + uvicorn workers (4 workers) on port 8000

# Frontend (build static assets)
cd web
npm run build
# Serve dist/ via nginx (see Section 5)
```

### 4.4 Stopping

```bash
# Backend
bash scripts/stop_server.sh

# Frontend dev server
# Ctrl+C in terminal, or:
cd web && npm run stop
```

---

## 5. Production Deployment

### 5.1 nginx Configuration

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name dossier.example.com;

    ssl_certificate /etc/ssl/certs/dossier.crt;
    ssl_certificate_key /etc/ssl/private/dossier.key;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

    # Web SPA (static files)
    location / {
        root /var/www/dossier/web/dist;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running operations
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;

        # File upload size
        client_max_body_size 25M;
    }

    # SSE (Server-Sent Events) for job streaming
    location ~ /api/v1/jobs/.*/stream {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }

    # Health check (no rate limit)
    location /health {
        proxy_pass http://backend;
    }
}
```

### 5.2 Systemd Service

```ini
# /etc/systemd/system/dossier-backend.service
[Unit]
Description=Dossier Backend API
After=network.target

[Service]
Type=simple
User=dossier
WorkingDirectory=/opt/dossier/backend
Environment=APP_ENV=production
EnvironmentFile=/opt/dossier/backend/.env
ExecStart=/opt/dossier/backend/.venv/bin/gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 300
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable dossier-backend
sudo systemctl start dossier-backend
sudo systemctl status dossier-backend
```

---

## 6. Operational Procedures

### 6.1 Health Checks

```bash
# Liveness (is the process running?)
curl http://localhost:8000/health

# Readiness (are models loaded and index ready?)
curl http://localhost:8000/health | jq '.ready'

# Index stats
curl -H "X-Admin-Secret: $ADMIN_SECRET" \
  http://localhost:8000/api/v1/index/stats
```

### 6.2 Log Inspection

```bash
# Application logs
tail -f backend/logs/app.log | jq .

# Filter by level
cat backend/logs/app.log | jq 'select(.level == "ERROR")'

# Filter by component
cat backend/logs/app.log | jq 'select(.component == "narrative")'

# Prompt logs
tail -f backend/data/logs/prompts.jsonl | jq .

# Filter LLM calls by latency
cat backend/data/logs/prompts.jsonl | jq 'select(.latency_ms > 5000)'
```

### 6.3 Re-Indexing

```bash
# Full re-index (destructive — rebuilds from scratch)
bash scripts/index_corpus.sh --rebuild

# Incremental (add new images only)
bash scripts/index_corpus.sh --incremental

# Check progress of running indexing job
curl http://localhost:8000/api/v1/jobs/<job_id>
```

### 6.4 Model Updates

1. Download new model weights:
   ```bash
   bash scripts/download_models.sh --model insightface --version latest
   ```

2. Update config if model name changed:
   ```bash
   # Edit .env
   DETECTION__HUMAN_MODEL=insightface_v2
   ```

3. Restart backend:
   ```bash
   sudo systemctl restart dossier-backend
   ```

4. Verify model loaded:
   ```bash
   curl http://localhost:8000/health | jq '.components.models'
   ```

5. Run evaluation to compare:
   ```bash
   bash scripts/evaluate_all.sh
   ```

### 6.5 Backup

```bash
# Backup metadata database
cp backend/data/metadata.db backend/data/metadata.db.bak.$(date +%Y%m%d)

# Backup FAISS indices
cp -r backend/data/indices backend/data/indices.bak.$(date +%Y%m%d)

# Backup prompt logs
cp backend/data/logs/prompts.jsonl backend/data/logs/prompts.jsonl.bak.$(date +%Y%m%d)
```

### 6.6 Rollback

If a model update degrades performance:

1. Restore previous model weights from backup
2. Revert config change in `.env`
3. Restart backend: `sudo systemctl restart dossier-backend`
4. Re-run evaluation to verify: `bash scripts/evaluate_all.sh`

If index is corrupted:

1. Restore index from backup: `cp -r data/indices.bak.YYYYMMDD data/indices`
2. Restart backend
3. If no backup: full re-index: `bash scripts/index_corpus.sh --rebuild`

---

## 7. Alerting & Incident Response

### 7.1 Alert Definitions

| Alert | Condition | Severity | Runbook |
|-------|-----------|----------|---------|
| Backend Down | `/health` returns non-200 for > 60s | Critical | Section 7.2 |
| Models Not Ready | `/health` → `ready: false` for > 5min | High | Section 7.3 |
| High Query Latency | p95 > 10 seconds for 5 minutes | Medium | Section 7.4 |
| Dossier Generation Failed | Job status = failed | Medium | Section 7.5 |
| Index Drift | Indexed count diverges from corpus size | Low | Section 7.6 |
| Disk Space Low | < 10% free on data partition | High | Section 7.7 |
| GPU Memory Exhausted | CUDA OOM errors in logs | High | Section 7.8 |

### 7.2 Backend Down

**Possible causes**:
- Process crashed (OOM, unhandled exception)
- Port conflict (zombie process)
- Configuration error after update

**Immediate mitigation**:
```bash
# Check process status
sudo systemctl status dossier-backend

# Check for port conflicts
lsof -i :8000

# Kill zombie processes
lsof -ti:8000 | xargs kill -9

# Restart
sudo systemctl restart dossier-backend

# Check logs for crash reason
journalctl -u dossier-backend --since "5 minutes ago"
```

### 7.3 Models Not Ready

**Possible causes**:
- Insufficient GPU memory
- Model files missing or corrupted
- CUDA driver mismatch

**Immediate mitigation**:
```bash
# Check GPU status
nvidia-smi

# Check model files exist
ls -la backend/models/

# Re-download models
bash scripts/download_models.sh

# Check logs for model loading errors
grep "model_load" backend/logs/app.log | tail -20
```

### 7.4 High Query Latency

**Possible causes**:
- Index too large for available memory (swapping)
- GPU under heavy load from concurrent requests
- Metadata DB slow (missing indices, large table scans)

**Immediate mitigation**:
```bash
# Check system resources
free -h
nvidia-smi
iostat -x 1 5

# Check SQLite performance
sqlite3 backend/data/metadata.db "EXPLAIN QUERY PLAN SELECT * FROM faces WHERE image_id = 'test'"

# Reduce concurrent load
# Edit .env: JOBS__MAX_CONCURRENT=1
sudo systemctl restart dossier-backend
```

### 7.5 Dossier Generation Failed

**Possible causes**:
- LLM API key expired or rate limited
- VLM model crashed or OOM
- Invalid response from LLM (malformed JSON)

**Immediate mitigation**:
```bash
# Check job error
curl http://localhost:8000/api/v1/jobs/<job_id> | jq '.error'

# Check prompt logs for the failed request
grep "<job_id>" backend/data/logs/prompts.jsonl | jq .

# Test LLM connectivity
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $NARRATIVE__LLM_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'
```

### 7.6 Index Drift

**Possible causes**:
- New images added to corpus but not indexed
- Indexing job failed midway

**Remediation**:
```bash
bash scripts/index_corpus.sh --incremental
```

### 7.7 Disk Space Low

**Possible causes**:
- Prompt logs growing unbounded
- Thumbnail cache growing
- Upload temp files not cleaned

**Remediation**:
```bash
# Check disk usage
du -sh backend/data/*

# Rotate prompt logs
mv backend/data/logs/prompts.jsonl backend/data/logs/prompts.jsonl.$(date +%Y%m%d)

# Clean upload temp files older than 24h
find backend/data/uploads/temp -mtime +1 -delete

# Clean thumbnail cache
rm -rf backend/data/thumbnails/*
```

### 7.8 GPU Memory Exhausted

**Possible causes**:
- Multiple workers each loading models
- Batch size too large during indexing
- VLM loaded alongside detection models

**Remediation**:
```bash
# Check GPU memory per process
nvidia-smi

# Reduce workers to 1 (shares GPU)
# Edit .env or start script
# workers=1

# Reduce batch size
# Edit .env: INDEX__BATCH_SIZE=32

# Offload VLM to API instead of local
# Edit .env: NARRATIVE__VLM_ENDPOINT=https://api.example.com/vlm

sudo systemctl restart dossier-backend
```

---

## 8. Scaling Strategy

### 8.1 Vertical Scaling (Current Architecture)

| Bottleneck | Solution |
|------------|----------|
| More images | Larger FAISS IVF index + more disk |
| Faster queries | GPU with more VRAM for larger batch inference |
| More concurrent users | More uvicorn workers (CPU-bound) + async job queue |
| Faster indexing | GPU with more VRAM + higher batch size |

### 8.2 Horizontal Scaling (Future)

If single-node limits are reached:

1. **Migrate SQLite to PostgreSQL** for concurrent write support
2. **Move FAISS to a vector database** (Milvus, Qdrant, Weaviate) for distributed search
3. **Separate model inference** into a dedicated GPU service (Triton, vLLM)
4. **Add Redis** for job queue (replace in-memory queue)
5. **Serve images from object storage** (S3, MinIO) instead of local filesystem
6. **Deploy web SPA to CDN** (already designed for this)

---

## 9. SLOs

| SLO | Target | Measurement Window |
|-----|--------|--------------------|
| API Availability | 99.5% | Monthly |
| Query Latency (p95) | < 5 seconds | Weekly |
| Dossier Generation Success Rate | > 95% | Weekly |
| Indexing Completion | 100% of images in corpus indexed | After each run |
| Data Durability | No metadata or index loss | Continuous |

---

## 10. Environment Matrix

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `APP_ENV` | dev | staging | production |
| `APP_DEBUG` | true | false | false |
| Workers | 1 (reload) | 2 | 4 |
| `DETECTION__DEVICE` | auto | cuda | cuda |
| `INDEX__TYPE` | flat | ivf | ivf |
| `NARRATIVE__LLM_MODEL` | mock | claude | claude |
| TLS | none | self-signed | CA-signed |
| Rate Limiting | disabled | 60/min | 30/min |
| Prompt Logging | full (DEBUG) | metadata (INFO) | metadata (INFO) |
| Backups | none | daily | daily + weekly |
