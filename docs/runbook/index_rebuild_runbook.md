# Index Rebuild Runbook

**When to use**: FAISS index is corrupted, embedding model changed, or corpus significantly modified.

---

## When to Rebuild vs. Incremental

| Scenario | Action |
|----------|--------|
| New images added to corpus | Incremental (`bash scripts/index_corpus.sh`) |
| Images removed from corpus | Full rebuild |
| Embedding model changed (ArcFace, DINOv2 version) | Full rebuild |
| Index file corrupted or missing | Full rebuild |
| Metadata DB corrupted | Full rebuild with DB reset |
| Threshold tuning only | No rebuild needed — config change only |

---

## Pre-Rebuild Checklist

- [ ] Backup existing index: `cp -r data/indices data/indices.bak.$(date +%Y%m%d)`
- [ ] Backup metadata DB: `cp data/metadata.db data/metadata.db.bak.$(date +%Y%m%d)`
- [ ] Check disk space: `df -h data/` (need ~2x current index size during rebuild)
- [ ] Note current stats: `curl http://localhost:8000/api/v1/index/stats`
- [ ] Ensure inference service is running: `curl http://100.111.31.125:8010/health`

---

## Incremental Index

Adds new images without re-processing existing ones.

```bash
bash scripts/index_corpus.sh
```

Or via API:
```bash
curl -X POST http://localhost:8000/api/v1/index \
  -H "Content-Type: application/json" \
  -d '{"incremental": true}'
```

Monitor progress:
```bash
# Get job ID from the POST response, then:
curl http://localhost:8000/api/v1/jobs/{job_id}
```

---

## Full Rebuild

Re-processes all images from scratch.

```bash
bash scripts/index_corpus.sh --full
```

Or via API:
```bash
curl -X POST http://localhost:8000/api/v1/index \
  -H "Content-Type: application/json" \
  -d '{"incremental": false}'
```

### Expected Duration

| Corpus Size | GPU | Approximate Time |
|-------------|-----|-----------------|
| 10K images | RTX 3060 | ~15 minutes |
| 100K images | RTX 3060 | ~2.5 hours |
| 1M images | RTX 3060 | ~25 hours |

### During Rebuild

- The application remains responsive for health checks
- Queries against the old index continue to work until the new index replaces it
- Monitor GPU utilization: `ssh 100.111.31.125 nvidia-smi -l 5`
- Monitor progress: `curl http://localhost:8000/api/v1/jobs/{job_id}`

---

## Index with Custom Corpus Directory

```bash
bash scripts/index_corpus.sh /path/to/alternate/corpus
```

Or via API:
```bash
curl -X POST http://localhost:8000/api/v1/index \
  -H "Content-Type: application/json" \
  -d '{"corpus_dir": "/path/to/alternate/corpus", "incremental": false}'
```

---

## Post-Rebuild Verification

```bash
# 1. Check index stats
curl http://localhost:8000/api/v1/index/stats

# 2. Run evaluation
bash scripts/evaluate_all.sh

# 3. Smoke test — query a known subject
curl -X POST http://localhost:8000/api/v1/query \
  -F "image=@data/ground_truth/reference_photo.jpg" \
  -F "subject_type=human"
```

---

## Troubleshooting

### Build fails with CUDA OOM

```bash
# Reduce batch size in config
# Edit .env:
INDEX__BATCH_SIZE=32   # default is 64

# Or free GPU memory by stopping other services
bash scripts/start_vlm.sh --stop
```

### Index file not found after rebuild

```bash
# Check index directory
ls -la data/indices/

# Verify config points to correct path
uv run python -c "from src.utils.config import settings; print(settings.index.faiss_index_dir)"
```

### Metadata DB locked during rebuild

```bash
# Check for stale locks
fuser data/metadata.db

# If another process holds the lock, stop it first
# The backend and indexer share the same SQLite file
```

---

## Rollback

If the rebuild produces worse results:

```bash
# Restore from backup
cp data/indices.bak.YYYYMMDD/* data/indices/
cp data/metadata.db.bak.YYYYMMDD data/metadata.db

# Restart backend to reload index
bash scripts/start_server.sh
```
