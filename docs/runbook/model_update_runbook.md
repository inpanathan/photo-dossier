# Model Update Runbook

**When to use**: Updating detection models (InsightFace, YOLOv8, DINOv2) or narrative models (Qwen2.5-VL, Qwen2.5-14B).

---

## Pre-Update Checklist

- [ ] Backup current model weights
- [ ] Run baseline evaluation: `bash scripts/evaluate_all.sh > eval_before.json`
- [ ] Note current index stats: `curl http://localhost:8000/api/v1/index/stats`
- [ ] Ensure no active jobs: `curl http://localhost:8000/api/v1/jobs`

---

## 1. Detection Model Update (InsightFace / YOLOv8 / DINOv2)

These run on the 7810 node (`100.111.31.125`).

### 1.1 Download New Weights

```bash
# Download to 7810 node
bash scripts/download_models.sh

# Or manually on 7810:
ssh 100.111.31.125
cd ~/dossier-inference/models/
# Download new model files here
```

### 1.2 Update Configuration

If the model name or path changed, update `.env`:

```bash
# Example: update detection model
INFERENCE__BASE_URL=http://100.111.31.125:8010
```

No config change needed if the model files are replaced in-place.

### 1.3 Restart Inference Service

```bash
# Stop and restart inference on 7810
bash scripts/start_inference.sh --stop
bash scripts/start_inference.sh

# Wait for readiness
curl http://100.111.31.125:8010/health
```

### 1.4 Verify

```bash
# Quick smoke test — upload a test image
curl -X POST http://localhost:8000/api/v1/detect \
  -F "image=@test_photo.jpg"

# Run full evaluation
bash scripts/evaluate_all.sh > eval_after.json

# Compare metrics
diff eval_before.json eval_after.json
```

### 1.5 Re-Index Decision

If the embedding model changed (ArcFace version, DINOv2 version), the existing FAISS index is **incompatible** with new embeddings. You must rebuild:

```bash
bash scripts/index_corpus.sh --full
```

If only the detector changed (e.g., better face bounding boxes), re-indexing improves accuracy but isn't strictly required.

---

## 2. VLM Update (Qwen2.5-VL on 7810 GPU 1)

### 2.1 Download New Model

```bash
ssh 100.111.31.125
# Download new model (e.g., updated quantization)
huggingface-cli download Qwen/Qwen2.5-VL-7B-Instruct --local-dir ~/models/Qwen2.5-VL-7B-Instruct
```

### 2.2 Restart VLM Service

```bash
bash scripts/start_vlm.sh --stop
bash scripts/start_vlm.sh

# Verify
curl http://100.111.31.125:8011/v1/models
```

### 2.3 Verify

```bash
# Test photo description
curl http://100.111.31.125:8011/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-VL-7B-Instruct",
    "messages": [{"role": "user", "content": "Describe this image."}],
    "max_tokens": 100
  }'
```

---

## 3. LLM Update (Qwen2.5-14B on Local GPU)

### 3.1 Download New Model

```bash
huggingface-cli download Qwen/Qwen2.5-14B-Instruct-AWQ --local-dir ~/models/Qwen2.5-14B-Instruct-AWQ
```

### 3.2 Update Config (if model name changed)

```bash
# .env
NARRATIVE__LLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
```

### 3.3 Restart

```bash
# If using vLLM for local LLM
# Restart the vLLM process

# Restart backend
bash scripts/start_server.sh
```

---

## Rollback Procedure

If evaluation metrics degrade after update:

1. **Restore model weights**: Copy backed-up weights back to the model directory
2. **Revert config**: Undo any `.env` changes
3. **Restart services**:
   ```bash
   bash scripts/start_inference.sh --stop && bash scripts/start_inference.sh
   bash scripts/start_vlm.sh --stop && bash scripts/start_vlm.sh
   ```
4. **Re-index** (if embedder changed): `bash scripts/index_corpus.sh --full`
5. **Re-evaluate**: `bash scripts/evaluate_all.sh`

---

## Metrics to Compare

| Metric | Acceptable Regression |
|--------|----------------------|
| Human recall | No more than 2% drop |
| Pet recall | No more than 5% drop |
| Human precision | No more than 3% drop |
| Detection latency (p95) | No more than 50% increase |
| VLM description quality | Subjective review of 10 samples |
