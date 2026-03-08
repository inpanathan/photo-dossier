# Mobile Feasibility Analysis

Last updated: 2026-03-07
Status: Initial research — to be continued.

---

## Current Architecture (Server-Based)

| Component | Model / Tech | Resource Needs |
|-----------|-------------|----------------|
| Face detection + embedding | InsightFace (ONNX) | GPU, moderate |
| Pet detection | YOLOv8 (PyTorch) | GPU, moderate |
| Pet embedding | DINOv2 (ViT, 300M+ params) | GPU, heavy |
| Vector search | FAISS (CPU, in-memory) | RAM-dependent on index size |
| Image description | Qwen2.5-VL-7B | GPU, 14GB+ VRAM |
| Narrative generation | Qwen2.5-14B | GPU, 28GB+ VRAM |
| Metadata storage | SQLite | Trivial |
| EXIF extraction | piexif + geopy | Trivial |
| API layer | FastAPI + Uvicorn | Server process |

---

## Mobile Hardware Capabilities (2025-2026 Flagships)

### Apple (iPhone 15 Pro+, iPhone 16)
- **Neural Engine**: 17 TOPS (A17 Pro), runs Core ML models
- **On-device LLM**: Apple Intelligence uses a ~3B parameter model
- **RAM**: 8GB (Pro models)
- **Storage**: up to 1TB

### Android (Snapdragon 8 Gen 3+, Tensor G4)
- **Hexagon NPU**: 45+ TOPS (8 Gen 3)
- **On-device LLM**: Gemini Nano (~1.8B params)
- **RAM**: 12-16GB (flagships)
- **Storage**: up to 1TB

### Key Constraints
- Thermal throttling after ~30s sustained inference
- Battery drain during heavy ML workloads
- RAM pressure from large models + app + OS
- No discrete GPU — shared memory architecture

---

## Component-by-Component Feasibility

### Can Run On-Device

| Component | Mobile Runtime | Notes |
|-----------|---------------|-------|
| Face detection | Apple Vision Framework / Google ML Kit | Built-in, optimized, free. Better than running InsightFace. |
| Face embedding | Core ML / TFLite (MobileFaceNet) | Lightweight face embedding models exist (~5MB). |
| Pet detection | YOLOv8-nano (Core ML / TFLite) | Ultralytics supports export. Runs at 30fps. |
| EXIF extraction | Native APIs (Photos framework / ExifInterface) | Built into both platforms. |
| SQLite | Native | Built into both iOS and Android. |
| Timeline construction | App logic | Pure computation, no ML needed. |
| Small vector search | faiss-mobile / custom brute-force | Works for <100K vectors. Beyond that, needs optimization. |

### Cannot Run On-Device (Today)

| Component | Why Not | Minimum Requirement |
|-----------|---------|-------------------|
| DINOv2 (pet embedding) | 300M+ params ViT, ~1.2GB model | Could work with INT4 quantization (~300MB), but slow. Borderline. |
| Qwen2.5-VL-7B (VLM) | 7B params, needs ~4GB+ memory | Exceeds thermal/memory budget for sustained use. |
| Qwen2.5-14B (narrative LLM) | 14B params, needs ~8GB+ memory | Completely infeasible on-device. |

---

## Proposed Mobile Architecture

### Hybrid: On-Device Detection + Cloud/Server Narrative

```
Mobile Device (on-device)
├── Face detection ──────────── Apple Vision / ML Kit
├── Face embedding ──────────── MobileFaceNet (Core ML / TFLite)
├── Pet detection ───────────── YOLOv8-nano (Core ML / TFLite)
├── Pet embedding ───────────── MobileNetV3 or quantized DINOv2-small
├── EXIF / metadata ─────────── Native platform APIs
├── SQLite storage ──────────── Native
├── Vector search ───────────── faiss-mobile (small index)
├── Timeline construction ───── App logic
│
├── ── Network boundary ──────────────────────────────
│
├── VLM image description ───── Cloud API / home server
└── Narrative generation ────── Cloud API / home server
```

### Cloud/Server Options for Narrative Layer

| Option | Pros | Cons |
|--------|------|------|
| Self-hosted (home server) | Privacy, no recurring cost | Requires always-on server, user setup |
| OpenAI / Anthropic API | Best quality, easy integration | Per-token cost, data leaves device |
| Google Gemini API | Vision + text in one model | Per-token cost, data leaves device |
| On-device (future, ~2027?) | Full privacy | Waiting on hardware (20B+ on-phone) |

---

## Mobile Framework Options

### Native
- **Swift + Core ML** (iOS) — best performance, tightest hardware integration
- **Kotlin + ML Kit / NNAPI** (Android) — best Android experience

### Cross-Platform
- **React Native + ONNX Runtime** — JavaScript app shell, native ML modules
- **Flutter + TFLite** — Dart app shell, platform channels for ML
- **Kotlin Multiplatform** — shared business logic, native UI

### ML Runtimes
- **Core ML** (iOS only) — Apple's optimized runtime, automatic Neural Engine dispatch
- **TensorFlow Lite** (cross-platform) — well-supported, quantization tools
- **ONNX Runtime Mobile** (cross-platform) — can reuse existing ONNX models from server
- **llama.cpp** (cross-platform) — for on-device LLM if attempting small models (~1-3B)
- **MLX** (Apple Silicon only) — efficient inference, growing ecosystem

---

## Migration Path from Current Codebase

| Current (Python/Server) | Mobile Equivalent |
|------------------------|-------------------|
| InsightFace (ONNX) | MobileFaceNet (Core ML / TFLite) or platform Vision API |
| YOLOv8 (PyTorch) | YOLOv8-nano exported to Core ML / TFLite |
| DINOv2 (PyTorch) | Quantized DINOv2-small or MobileNetV3 + fine-tune |
| FAISS (faiss-cpu) | faiss-mobile or brute-force for small indices |
| SQLite (Python) | Native SQLite (both platforms) |
| Qwen2.5-VL | Cloud API call (OpenAI vision, Gemini, etc.) |
| Qwen2.5-14B | Cloud API call (Claude, GPT, Gemini, etc.) |
| FastAPI | Not needed — app is the client |

---

## Effort Estimate

| Phase | Scope | Complexity |
|-------|-------|------------|
| 1. Core detection + search | Face/pet detection, embedding, local search | Medium — platform APIs simplify this |
| 2. Photo import + metadata | EXIF, geo, timeline from device photo library | Medium — platform-specific APIs |
| 3. Cloud narrative integration | API client for VLM + LLM | Low — REST calls |
| 4. Self-hosted server option | Package existing Python backend for home server | Low — already built |
| 5. Offline-first sync | Index on-device, narrative when online | High — sync logic, queue management |

---

## Open Questions

- [ ] Which mobile platform first? (iOS has better ML tooling, Android has larger market)
- [ ] Can DINOv2-small (22M params) produce adequate pet embeddings after quantization?
- [ ] Photo library access: scan in background vs. on-demand? Battery/permission implications.
- [ ] Index size limit for on-device FAISS — benchmark at 10K, 50K, 100K, 500K vectors
- [ ] Business model: free with self-hosted server? Paid cloud narrative tier?
- [ ] App Store review: will Apple/Google approve a face-matching app? Privacy policy requirements.
