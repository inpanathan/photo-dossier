# Project Specification for AI Coding Agent — The Needle in a Haystack (Dossier v2)

## 1. Goal

- Build a system that, given a single reference photo of a person or pet, retrieves all other photos of that subject from a massive mixed corpus (~1M images) and generates a coherent timeline narrative ("dossier") of their activities over a period of time.
- Test the real-world limits of face-based retrieval and RAG architectures using ground-truth data contributed by participants documenting their daily lives and their pets' activities.

## 2. Deliverables

- A working pipeline for:
  - Ingesting and indexing a large mixed photo corpus (participant photos + ~1M random images) from a configurable local directory.
  - Human face and pet face detection, embedding, and nearest-neighbor retrieval against a reference photo.
  - Extracting metadata (geocoded coordinates, timestamps, EXIF data) from retrieved photos.
  - Generating a multi-day timeline narrative (dossier) from the retrieved photo set using an LLM/VLM.
- An interactive UI for submitting a reference photo, reviewing auto-detected faces, and viewing retrieved results + generated dossier.
- Evaluation tools to measure retrieval precision/recall against known ground-truth photo sets.
- Documentation:
  - README with setup, data preparation, and run instructions.
  - Design overview of the retrieval + narrative generation pipeline.
  - Participant guide for photo collection (requirements, metadata expectations, pet photo guidelines).

## 3. High-Level Requirements

- Participants each contribute 10+ geocoded, timestamped photos documenting a period of time — from a single day to weeks or months. Photos may include the participant themselves, their pet(s), or both.
- All participant photos are mixed into a shared local directory alongside ~1M random/distractor photos to form the "haystack."
- Given one reference photo of a subject (human or pet), the system must find all their other photos ("needles") in the haystack.
- The system extracts temporal and geospatial metadata from retrieved photos and orders them chronologically, grouping by day and identifying patterns across days.
- An LLM/VLM generates a coherent dossier — a timeline story reconstructing the subject's activities over the covered period, grounded in the retrieved photos and their metadata.
- **Architectural constraint**: The system must follow an API-first, frontend-agnostic architecture. All business logic, retrieval, and narrative generation are exposed exclusively through versioned REST APIs. The web UI is a standalone single-page application (SPA) that consumes these APIs. No business logic lives in the frontend. This ensures a mobile app (v2) can reuse the entire backend without modification.
- **v1 MUST include**: human and pet face-based retrieval, metadata extraction, multi-day timeline ordering, narrative generation, ground-truth evaluation.
- **v1 delivers**: Web SPA + backend API.
- **v2 adds**: Native mobile app (iOS/Android) consuming the same API, with native photo source integration — camera roll, Apple Photos (iOS), and Google Photos (Android) — for both reference photo selection and contributed photo uploads.
- **Nice-to-have**: clothing/context re-identification (non-face cues), pet breed/species classification, interactive map visualization, confidence-based narrative hedging, multi-person dossier comparison, cross-subject dossier linking (e.g., owner and pet appearing together).

## 4. Functional Requirements

### Feature 1: Photo Ingestion and Indexing

- Purpose:
  - Ingest all images from the local corpus, detect human and pet faces, compute embeddings, and build a searchable index.
- Inputs:
  - Local directory path to the photo corpus (~1M+ images). Configurable via `settings.corpus_dir`.
- Outputs:
  - A vector index of subject embeddings (human faces and pet faces) linked to source image paths.
  - Each indexed entry tagged with subject type: `human` or `pet`.
  - Extracted EXIF/metadata store (timestamp, GPS coordinates, camera info) per image.
- Detailed behavior:
  - Scan the corpus directory recursively for image files (JPEG, PNG, HEIC, etc.).
  - Run human face detection on each image; extract and align all detected faces.
  - Run pet/animal face detection on each image using a pet-specific detector (e.g., a fine-tuned YOLO or a pet face detection model). Extract and align detected pet faces.
  - Compute embeddings for each detected face (human or pet) using the appropriate model.
  - Store embeddings in a vector index (FAISS or similar) with mappings back to source images and subject type tags.
  - Parse and store EXIF metadata (datetime, GPS lat/lng, orientation) in a sidecar database or structured file.
  - Support incremental indexing (add new images without re-indexing the entire corpus).
- Edge cases:
  - Images with no detectable faces (human or pet): skip but log for audit.
  - Images with multiple faces of mixed types (humans and pets together): index each face separately with its type tag, all linked to the same source image.
  - Corrupt or unreadable images: log error and continue.
  - Missing EXIF/metadata: mark as unknown; still index the face embedding.
  - Pet faces with high variability (different angles, lighting, fur patterns): rely on embedding similarity rather than strict geometric alignment.

### Feature 2: Reference Photo Query and Face Retrieval

- Purpose:
  - Given a single reference photo of a person or pet, retrieve all images in the corpus containing that subject's face.
- Inputs:
  - One reference photo of the target subject.
  - Subject selection is handled via the auto-detection flow (see Feature 6). The API receives a confirmed subject type and face crop coordinates.
  - Configurable similarity threshold and max results (top-k).
- Outputs:
  - Ranked list of matching images with similarity scores, face bounding boxes, subject type, and metadata.
- Detailed behavior:
  - Receive the user-confirmed face region and subject type from the UI.
  - Embed the selected face using the model appropriate for the subject type.
  - Perform nearest-neighbor search against the type-filtered subset of the corpus index (search human embeddings for human queries, pet embeddings for pet queries).
  - Return top-k results above a configurable similarity threshold.
  - Support re-ranking or filtering by secondary signals (e.g., fur color/pattern for pets, clothing for humans, temporal clustering).
- Edge cases:
  - Reference photo contains multiple faces: prompt user to select which face to query.
  - Reference photo contains both a human and a pet: allow user to choose subject, or run both queries and link results.
  - No face detected in reference photo: return clear error.
  - Very few matches found: surface all matches with a low-confidence warning.
  - False positives (lookalikes): include similarity scores so users can inspect and filter.
  - Pet lookalikes (same breed, similar markings): especially common — surface confidence scores prominently.

### Feature 3: Metadata Extraction and Timeline Construction

- Purpose:
  - Order retrieved photos chronologically and geospatially to reconstruct the subject's activities over days, weeks, or months.
- Inputs:
  - Set of retrieved images with their EXIF metadata.
- Outputs:
  - Multi-day chronologically ordered sequence of photos with timestamps, locations, and derived context.
  - Day-level groupings with date headers.
  - Cross-day pattern annotations (e.g., "appears at this location every weekday morning").
- Detailed behavior:
  - Parse timestamps and GPS coordinates from each retrieved image.
  - Sort photos by timestamp to establish temporal sequence.
  - Group photos by calendar day to create day-level segments.
  - Identify recurring patterns across days: repeated locations, regular times, habitual activities.
  - Reverse-geocode GPS coordinates to human-readable locations (neighborhood, city, venue type).
  - Identify temporal gaps and cluster photos into "scenes" or "episodes" within each day.
  - Handle timezone normalization based on GPS data.
  - Detect multi-day gaps (no photos for N days) and note them as periods of no observation.
- Edge cases:
  - Photos with missing timestamps: attempt to infer position in sequence from GPS proximity to neighboring photos.
  - Photos with missing GPS: include in timeline with "unknown location."
  - Timestamp conflicts or out-of-order EXIF data: flag but include, let the narrative generator handle ambiguity.
  - Photos spanning multiple timezones (e.g., travel): detect timezone shifts from GPS and adjust narrative accordingly.
  - Very long time spans (months): summarize sparse periods rather than listing every gap.

### Feature 4: Dossier Narrative Generation

- Purpose:
  - Generate a coherent, readable timeline story of the subject's activities over the observed period from the retrieved and ordered photos.
- Inputs:
  - Multi-day ordered sequence of retrieved photos with metadata (timestamps, locations, scene descriptions).
  - Optionally, the reference photo for context.
  - Subject type (human or pet) to tailor narrative voice and vocabulary.
- Outputs:
  - A structured dossier document containing:
    - Executive summary (overview of the entire observation period — date range, key locations, activity patterns).
    - Per-day timeline entries with photo thumbnails, timestamps, locations, and narrative descriptions.
    - Cross-day analysis: detected routines, notable deviations, frequently visited locations.
    - Confidence indicators for uncertain retrievals or metadata gaps.
- Detailed behavior:
  - Use a vision-language model (VLM) to describe the visual content of each photo (activity, setting, companions, attire — or for pets: activity, environment, posture, companions).
  - Feed the ordered photo descriptions, timestamps, and locations into an LLM to generate a cohesive multi-day narrative.
  - Structure the dossier by day, with an overarching narrative thread connecting days.
  - The narrative should connect events logically within and across days (e.g., "On Tuesday the subject returned to the same cafe visited Monday morning, suggesting a daily routine").
  - For pet subjects, adapt language appropriately (e.g., "The dog was observed at the park" rather than "The subject arrived at the park").
  - Include uncertainty language where metadata is missing or retrieval confidence is low.
  - For long observation periods, include a summary section highlighting patterns before the detailed day-by-day timeline.
- Edge cases:
  - Very few photos retrieved (< 3): generate a partial dossier with explicit gaps noted.
  - Photos with ambiguous content: describe what is visible without speculation.
  - Conflicting metadata (e.g., impossible travel times between locations): flag as anomaly in the narrative.
  - Single-day observation: degrade gracefully to single-day dossier without cross-day analysis.
  - Pet photos with no clear activity (e.g., sleeping): still include with appropriate description.

### Feature 5: Ground-Truth Evaluation

- Purpose:
  - Measure retrieval quality against known ground-truth photo sets contributed by participants, for both human and pet subjects.
- Inputs:
  - Ground-truth manifest: mapping of subject ID (participant or pet) to list of their photo filenames and subject type.
  - Retrieval results for each subject's reference photo.
- Outputs:
  - Per-subject precision, recall, and F1 scores, broken down by subject type.
  - Aggregate statistics across all human subjects and all pet subjects separately, plus combined.
  - Confusion analysis: false positives (wrong subject retrieved) and false negatives (subject photo missed).
  - Cross-type confusion analysis: cases where the system confused a human for a pet or vice versa.
- Detailed behavior:
  - For each subject, run retrieval using their designated reference photo.
  - Compare retrieved set against ground-truth manifest.
  - Compute precision, recall, and F1.
  - Report metrics separately for human and pet categories to identify model-specific weaknesses.
  - Generate a summary report with per-subject breakdowns and aggregate metrics.
  - Optionally, visualize false positives and false negatives for qualitative analysis.
- Edge cases:
  - Subject photos where face is not visible (back turned, obscured): track separately as "non-face ground truth."
  - Near-duplicate distractor images: ensure evaluation handles exact-match vs. near-match correctly.
  - Pet photos where the pet is partially occluded by furniture, toys, etc.: track as separate difficulty category.

### Feature 6: Interactive UI

- Purpose:
  - Provide an interface for uploading a reference photo, reviewing auto-detected faces, viewing retrieved results, inspecting the multi-day timeline, and reading the generated dossier.
- Inputs:
  - Reference photo upload.
  - No manual subject type selector required — the system auto-detects.
  - Optional configuration (similarity threshold, max results, date range filter).
- Outputs:
  - Auto-detection overlay showing all detected faces with bounding boxes color-coded by type (e.g., blue for human, green for pet).
  - Retrieved photo grid with similarity scores and subject type badges.
  - Multi-day timeline view (chronological photo strip with metadata, grouped by day).
  - Generated dossier narrative.
  - Date range selector to filter or zoom into specific days.
- Detailed behavior:
  - **Step 1 — Upload**: User uploads or drops a reference photo.
  - **Step 2 — Auto-detect**: System runs both human and pet face detectors on the image. All detected faces are overlaid with labeled bounding boxes:
    - Each box shows the detected type (`Human` / `Pet`) and a confidence score.
    - Boxes are color-coded: blue for human, green for pet.
  - **Step 3 — Select subject**: Three possible outcomes:
    - **Single face detected**: Pre-selected and highlighted. User clicks "Search" to proceed, or can override the type label via a small toggle on the bounding box if the auto-classification is wrong.
    - **Multiple faces detected (any mix of human and pet)**: User clicks on the face they want to search for. The selected face is highlighted; others dim. User can override the type label before proceeding.
    - **No faces detected**: Error message displayed: "No human or pet faces detected. Try a different photo with a clearly visible face." User can optionally draw a manual bounding box and select a type to force a query.
  - **Step 4 — Results**: Retrieved photo grid displayed with thumbnails, scores, timestamps, locations, and subject type badges.
  - Calendar/date-range view showing which days have photos and photo density per day.
  - Timeline/map view showing the reconstructed multi-day story.
  - Dossier panel with the generated narrative, downloadable as PDF or Markdown.
  - Evaluation panel (if ground-truth manifest is loaded) showing precision/recall metrics.
- Edge cases:
  - Large result sets: paginate or lazy-load images.
  - Slow retrieval on large corpus: show progress indicator.
  - Very long timelines (months of photos): default to summary view with drill-down per day.
  - Photo contains both a person and their pet: both faces detected and shown — user picks which to search. Optionally offer "Search both" to run two queries and link results.
  - Auto-detection misclassifies type (e.g., labels a cat as human): user overrides via the type toggle on the bounding box. These overrides are logged to improve detection over time.
  - Very small or blurry faces: detected with low confidence — shown with a dashed bounding box and warning icon. User can still select them but is warned results may be poor.

### Feature 7: Photo Source Integration (v2, Mobile)

- Purpose:
  - Allow mobile users to select reference photos and contribute photos from their device's native photo sources, without requiring manual file export or transfer.
- Inputs:
  - User's selected photo source:
    - **Device camera** (capture a new reference photo on the spot).
    - **Local camera roll / gallery** (photos already on the device).
    - **Apple Photos library** (iOS — includes iCloud Photos, shared albums, smart albums).
    - **Google Photos** (Android — includes cloud-synced photos, shared albums, auto-organized collections).
- Outputs:
  - Selected image(s) uploaded to the backend API with preserved EXIF metadata (timestamps, GPS).
- Detailed behavior:
  - **Reference photo selection**: User picks a single photo of the subject (human or pet) from any available source. The photo is sent to `POST /detect` for auto-detection, then the standard UI flow continues.
  - **Photo contribution** (for building ground-truth sets): User selects multiple photos from a date range or album. The app extracts and preserves EXIF metadata before upload.
  - **Platform-specific integration**:
    - **iOS**: Use the native `PHPickerViewController` for camera roll / Apple Photos access. Supports iCloud Photos transparently (downloads on demand). Request `NSPhotoLibraryReadUsageDescription` permission.
    - **Android**: Use the `Photo Picker` (Android 13+) or `ACTION_PICK` intent for gallery / Google Photos access. Google Photos items are downloaded on selection. Request `READ_MEDIA_IMAGES` permission.
    - **Camera capture**: Use native camera APIs. Captured photos include GPS and timestamp from the device.
  - **Metadata preservation**: When selecting photos from cloud-backed sources (iCloud, Google Photos), ensure EXIF data (especially GPS and timestamp) is preserved during download. If the cloud service strips EXIF, fall back to the photo's metadata available via the platform API (creation date, location).
  - **Batch upload**: When contributing multiple photos, upload in background with progress tracking. Use chunked/resumable uploads for unreliable mobile networks.
- Edge cases:
  - **iCloud Photos not downloaded locally**: iOS fetches the full-resolution image on demand — handle the async download with a progress indicator. Fail gracefully if the device is offline.
  - **Google Photos cloud-only items**: Similar async download. Warn user if on cellular data and images are large.
  - **Permission denied**: Clear message explaining why photo access is needed, with a link to device settings.
  - **EXIF stripped by cloud service**: Use platform metadata APIs as fallback. Log when EXIF is missing so the timeline builder knows to expect gaps.
  - **HEIC/HEIF format (common on iOS)**: Convert to JPEG before upload, or ensure the backend accepts HEIC.
  - **Live Photos / motion photos**: Extract the still frame, discard the video component.
  - **Shared albums**: Photos from shared albums may lack GPS metadata (stripped for privacy by Apple/Google). Handle gracefully.

## 5. Non-Functional Requirements

- **Performance**:
  - Indexing: process the full ~1M image corpus in a reasonable batch timeframe (hours, not days) on available GPU hardware.
  - Retrieval: return results within seconds for a single reference query against the indexed corpus.
  - Narrative generation: complete dossier generation within 30 seconds for a single-day photo set; scale linearly for multi-day sets, with streaming output for long dossiers.
- **Scalability**:
  - Index must handle 1M+ images without degrading query performance.
  - Index supports both human and pet face embeddings without cross-contamination in search.
  - Support incremental re-indexing as new images are added.
- **Reliability**:
  - Graceful handling of corrupt images and model loading errors.
  - Pipeline should be resumable — if indexing is interrupted, it should resume from where it left off.
- **Privacy & Ethics**:
  - All participant photos are contributed voluntarily with informed consent.
  - System operates on a closed corpus — no external image scraping or API calls to identify people.
  - Dossier narratives should not make claims about identity beyond what the photos show.
  - Pet photos are subject to the same consent requirements from the pet owner.
- **Interpretability**:
  - Surface similarity scores, face bounding boxes, and confidence levels so users can judge retrieval quality.
  - Clearly distinguish high-confidence matches from borderline retrievals.
  - Clearly label subject type (human/pet) on all results.
- **Maintainability**:
  - Modular pipeline stages (ingest -> detect -> embed -> index -> retrieve -> narrate) that can be run independently.
  - Configurable model choices at each stage.
  - Pluggable detection/embedding backends per subject type (swap human or pet models independently).
- **Mobile-readiness (architectural)**:
  - Backend is fully stateless — no server-side sessions. All auth via tokens (JWT or similar).
  - All image data served via URLs, never embedded/base64-encoded in API responses. Clients fetch images directly from the static file server or object storage.
  - Long-running operations (corpus indexing, dossier generation) use async job patterns: the API returns a job ID immediately, clients poll or subscribe via WebSocket/SSE for progress and completion.
  - API responses are paginated with cursor-based pagination (not offset-based) to support infinite scroll on mobile.
  - File uploads use multipart form data with size limits enforced server-side — compatible with both browser and mobile HTTP clients.
  - All API responses include only serializable JSON — no HTML fragments, no server-rendered partials.

## 6. Tech Stack and Constraints

- Programming languages:
  - Python for all pipeline and backend logic.
- Frameworks/libraries:
  - **Backend**:
    - FastAPI for the REST API (versioned at `/api/v1/`).
    - PyTorch for model integration.
    - Human face detection/embedding: `insightface` (RetinaFace + ArcFace) or `deepface` as baseline.
    - Pet face detection/embedding: fine-tuned YOLOv8 or similar for pet face detection; a pet re-identification model (e.g., trained on Oxford-IIIT Pet Dataset or a pet re-ID dataset) for embeddings. Fallback: DINOv2 or SigLIP-2 for general visual similarity.
    - FAISS for vector indexing and nearest-neighbor search.
    - A vision-language model (e.g., Qwen-2.5-VL, LLaVA, or similar) for photo description.
    - An LLM (e.g., Claude API, Qwen-2.5, or Llama) for narrative generation.
    - `Pillow` / `piexif` for EXIF metadata extraction.
    - `geopy` or a reverse-geocoding service for GPS to location name.
    - Streamlit or NiceGUI for the interactive UI (or a React frontend if preferred).
  - **Web frontend (v1)**:
    - React (or Next.js) SPA — communicates with backend exclusively via REST API.
    - Tailwind CSS for styling.
    - Responsive design as a baseline — functional on mobile browsers before native app exists.
  - **Mobile app (v2, future)**:
    - React Native (shared JS ecosystem with web) or Flutter. Decision deferred to v2 planning.
    - Will consume the identical `/api/v1/` endpoints — zero backend changes required.
    - **Photo source integration**:
      - **iOS**: `PHPickerViewController` for Apple Photos / camera roll, `UIImagePickerController` for camera. No direct Apple Photos API needed — the system picker handles iCloud transparently.
      - **Android**: `Photo Picker` (Android 13+) for Google Photos / gallery, `CameraX` for camera capture. For Google Photos access beyond the picker, use the Google Photos Library API (requires OAuth consent).
    - **Metadata handling**: Use platform-native EXIF extraction (`CGImageSource` on iOS, `ExifInterface` on Android) before upload to ensure GPS/timestamp survive cloud download and format conversion.
    - Mobile-specific features: camera capture for reference photo, GPS from device, push notifications, background batch upload with resume capability.
- Environment:
  - GPU required for face embedding computation and VLM inference.
  - Local filesystem storage for the photo corpus, vector index, and metadata store.
- Architectural constraints:
  - **Strict separation**: Backend is a headless API server. Frontend is a standalone SPA with its own build pipeline, served from a CDN or static file server — not from FastAPI's `StaticFiles`.
  - **No server-rendered UI**: FastAPI serves JSON only (plus OpenAPI docs). No Jinja templates, no Streamlit, no server-side HTML.
  - **Shared nothing between frontend and backend** at build time — they are independently deployable artifacts connected only by the API contract.
- Other constraints:
  - Corpus path is configurable; the system reads images directly from disk. No requirement for network-mounted filesystems.
  - Focus on retrieval accuracy and narrative quality over UI polish.
  - Participant data stays on-premise — no uploading to external services.

## 7. Project Structure

```
backend/                        # Python API server (independently deployable)
  main.py                       # FastAPI entry point
  src/
    api/
      routes.py                 # API route definitions
      schemas.py                # Pydantic request/response models (API contract)
      deps.py                   # Dependency injection (auth, db, services)
    ingest/                     # Corpus scanning, EXIF extraction, human and pet face detection
    embeddings/                 # Face embedding computation, per-subject-type backends
    index/                      # FAISS index construction, type-filtered search
    retrieval/                  # Query pipeline (detect -> embed -> search -> rank)
    narrative/                  # VLM photo description + LLM dossier generation, multi-day structuring
    jobs/                       # Async job queue (indexing, dossier generation)
    evaluation/                 # Ground-truth comparison, precision/recall, per-type breakdowns
    utils/
      config.py                 # Layered config (Settings singleton)
      logger.py                 # Structured logging
      errors.py                 # AppError + ErrorCode
  configs/                      # Per-environment YAML configs
  tests/
  scripts/
  pyproject.toml

web/                            # React SPA (independently deployable)
  src/
    api/                        # API client layer (typed, auto-generated from OpenAPI)
    components/                 # UI components (upload, photo grid, timeline, dossier)
    pages/                      # Page-level views
    hooks/                      # React hooks (useQuery, useDetection, useDossier)
    utils/
  public/
  package.json
  vite.config.ts

mobile/                         # (v2, future) React Native or Flutter app
  src/
    api/                        # API client (auto-generated from OpenAPI)
    screens/                    # Screen-level views
    components/                 # Shared UI components
    photos/                     # Photo source integration
      picker.ts                 # Unified picker abstraction
      ios.ts                    # Apple Photos / camera roll bridge
      android.ts                # Google Photos / gallery bridge
      camera.ts                 # Camera capture
      metadata.ts               # EXIF extraction and normalization
    upload/                     # Background upload manager (chunked, resumable)
    hooks/

docs/                           # Documentation (shared)
  api-contract.md               # API contract and versioning policy
  requirements/
  architecture/

data/                           # Ground-truth manifests, sample images
```

## 8. Data and Models (AI/ML-Specific)

- Data:
  - **Participant photos**: 10+ geocoded, timestamped photos per participant documenting a period of time (single day to multiple weeks). May include photos of themselves and/or their pets. Contributed voluntarily.
  - **Distractor corpus**: ~1M random photos mixed into the same local directory. Source TBD (could be open datasets like YFCC100M subset, Open Images, or synthetic). Should include animal photos as distractors for pet retrieval testing.
  - **Ground-truth manifest**: JSON/CSV mapping each subject's ID to their contributed filenames and subject type (`human` or `pet`).
  - Preprocessing:
    - EXIF extraction and metadata parsing at ingest time.
    - Human and pet face detection and alignment for all images.
    - Precomputed face embeddings stored in the FAISS index with subject type tags.
- Models:
  - **Human face detection**: RetinaFace (via `insightface`) or MTCNN.
  - **Human face embedding**: ArcFace (via `insightface`) for identity-focused embeddings.
  - **Pet face detection**: Fine-tuned YOLOv8-face or a dedicated pet face detector.
  - **Pet face/body embedding**: DINOv2 for general visual similarity, or a pet re-identification model. Optionally SigLIP-2 for multimodal comparison.
  - **Vision-language model**: Qwen-2.5-VL or LLaVA for describing photo content (scene, activity, objects, attire, pet behavior/posture).
  - **Narrative LLM**: Claude API, Qwen-2.5, or Llama for generating the dossier text from structured photo descriptions.
- Evaluation:
  - **Quantitative**: Precision, recall, F1 per subject against ground-truth manifest. Separate metrics for human vs. pet subjects. Aggregate across all participants.
  - **Qualitative**: Human review of generated dossiers for coherence, accuracy, and readability. Side-by-side comparison with participant's actual account of their period.

## 9. Example Scenarios (Few-Shot Specs)

### Example 1: Successful Full Retrieval (Human, Single Day)

- Input:
  - Reference photo of Participant A (a selfie taken at morning coffee).
  - Corpus contains 12 photos from Participant A's day + ~1M distractors.
- Expected processing steps:
  - Detect human face in reference photo, compute embedding.
  - Search FAISS index (human type filter), retrieve top-k matches above threshold.
  - Extract metadata, order chronologically.
  - Generate single-day dossier narrative.
- Expected output:
  - 11 of 12 photos retrieved (one missed because the participant's face was turned away). Precision: 100%, Recall: 91.7%.
  - Dossier: "The subject's day began at 7:45am at a cafe in the Plateau neighborhood (GPS: 45.52N, 73.58W). They were photographed holding a coffee... By 9:20am they had arrived at an office building downtown..."

### Example 2: Pet Retrieval (Multi-Day)

- Input:
  - Reference photo of Participant B's golden retriever.
  - Corpus contains 25 photos of the dog over 5 days + ~1M distractors (including other dog photos).
- Expected processing steps:
  - Detect pet face in reference photo, compute pet embedding.
  - Search FAISS index (pet type filter), retrieve top-k matches.
  - Group by day, order chronologically within each day.
  - Generate multi-day dossier.
- Expected output:
  - 22 of 25 photos retrieved (3 missed — dog facing away or heavily occluded). Precision: 95.6% (1 false positive: similar-looking golden retriever), Recall: 88%.
  - Dossier: "Over the five-day observation period (March 1-5), the golden retriever was photographed primarily in two locations: a residential neighborhood and a nearby park. Day 1 (March 1): The dog was first seen at 8:12am in a backyard... visited the park at 10:30am... Day 2: A similar morning routine was observed, with the park visit occurring 15 minutes earlier..."

### Example 3: Multi-Week Human Timeline

- Input:
  - Reference photo of Participant C.
  - Corpus contains 45 photos over 3 weeks.
- Expected output:
  - Dossier with executive summary: "Over a 21-day period, the subject was photographed on 12 distinct days. Activity centered around three primary locations: a downtown office (weekdays), a residential area (evenings), and a waterfront trail (weekends). A notable pattern emerged: weekend trail visits occurred consistently between 9-11am."
  - Per-day breakdowns for each of the 12 active days, with gaps noted: "No photos were recovered for March 8-10."

### Example 4: Challenging Retrieval with Lookalikes

- Input:
  - Reference photo of Participant D.
  - Corpus contains 10 photos from Participant D + several lookalike faces in the distractor set.
- Expected processing steps:
  - Retrieve top-50 candidates; 10 true matches + 3 false positives (lookalikes).
- Expected output:
  - Retrieved results with similarity scores. True matches cluster at 0.85-0.95 similarity; false positives at 0.70-0.78.
  - Dossier includes only high-confidence matches, with a note: "3 additional images showed possible matches but were excluded due to lower confidence."

### Example 5: Sparse Metadata Over Multiple Days

- Input:
  - Reference photo of Participant E.
  - 15 photos over 4 days; 6 lack GPS data, 3 lack timestamps.
- Expected output:
  - Timeline with per-day entries and gaps noted: "Day 2 (March 3): Between 11:30am and 2:15pm, no geolocated photos were found. Two undated photos appear to show the subject in what appears to be a park setting and have been tentatively placed in the afternoon based on lighting conditions."

## 10. Interfaces and APIs

### API Design Principles (Mobile-Readiness)

- All endpoints are JSON-in, JSON-out. No HTML responses.
- Images referenced by URL, never inlined. The backend serves images from a `/media/{path}` static endpoint or returns paths the client resolves.
- Long-running operations return immediately with a job ID. Clients poll `GET /jobs/{id}` or subscribe to a WebSocket/SSE channel for progress.
- Pagination uses cursor-based tokens: `?cursor=xxx&limit=20`. No offset-based pagination.
- Errors follow a consistent envelope: `{ "error": { "code": "...", "message": "...", "details": {...} } }`.
- API versioned at the URL level (`/api/v1/`). Breaking changes go in `/api/v2/`.
- OpenAPI schema is the single source of truth for the API contract. Web and mobile clients can auto-generate typed API clients from it.

### API Endpoints (prefix: `/api/v1`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/detect` | Run face detection on uploaded image. Returns bounding boxes, types, confidence. |
| `POST` | `/query` | Submit retrieval query (face crop + type + optional face_bbox). Returns job ID for async processing, or results directly for small corpora. |
| `GET` | `/query/{session_id}/results` | Paginated retrieval results for a query session. |
| `POST` | `/dossier` | Generate dossier from retrieval session. Returns job ID. |
| `GET` | `/dossier/{session_id}` | Retrieve generated dossier. |
| `POST` | `/evaluate` | Run ground-truth evaluation for a subject. |
| `GET` | `/evaluate/summary` | Aggregate evaluation across all subjects, broken down by type. |
| `GET` | `/index/stats` | Index statistics (total images, total faces, human count, pet count, index size). |
| `GET` | `/jobs/{job_id}` | Job status and progress (polling). |
| `GET` | `/jobs/{job_id}/stream` | SSE stream for real-time job progress. |
| `GET` | `/media/{path}` | Serve images by path (thumbnails and full-size). |
| `POST` | `/photos/upload` | Upload one or more photos with metadata. Accepts multipart form data. Returns photo IDs and extracted metadata. |
| `POST` | `/photos/upload/init` | Initiate a resumable upload session (for large batches over mobile networks). Returns an upload session ID. |
| `PATCH` | `/photos/upload/{session_id}` | Resume/continue a chunked upload. Accepts byte range. |
| `GET` | `/photos/upload/{session_id}/status` | Check upload session progress (completed chunks, remaining). |

### Upload Design Notes (Mobile-Readiness)

- Accept `image/jpeg`, `image/png`, `image/heic` content types. Backend normalizes to JPEG/PNG for processing.
- Metadata can be sent as a JSON field alongside the image binary, or extracted server-side from EXIF. Client-provided metadata takes precedence (covers the case where EXIF was stripped by a cloud service but the platform API had the data).
- Max single file size: 20MB. For batch uploads, use the resumable upload flow.
- Resumable uploads use a simple chunked protocol: client sends chunks with `Content-Range` headers, server assembles and acknowledges.

### CLI / Scripts

- `scripts/index_corpus.sh` — Batch-index the full local corpus.
- `scripts/evaluate_all.sh` — Run evaluation across all subjects.

### Internal APIs (Python)

- `detect_faces(image) -> list[Face]` — returns faces tagged with type (human/pet)
- `embed_face(face, subject_type) -> vector`
- `search_index(query_vector, k, threshold, subject_type) -> list[Match]`
- `extract_metadata(image_path) -> ImageMetadata`
- `describe_photo(image, metadata, subject_type) -> str`
- `generate_dossier(photo_descriptions, timeline, subject_type) -> Dossier`
- `group_by_day(timeline) -> dict[date, list[TimelineEntry]]`
- `detect_patterns(day_groups) -> list[Pattern]`

## 11. Testing and Validation

- Tests:
  - **Unit tests**: face detection wrapper (human and pet), embedding computation, EXIF parsing, timeline ordering, day grouping, reverse geocoding, pattern detection.
  - **Integration tests**: end-to-end query pipeline (reference photo -> retrieval -> narrative), API endpoint tests, pet-specific pipeline tests.
  - **Evaluation tests**: precision/recall computation against synthetic ground-truth fixtures, separate fixtures for human and pet subjects.
- Validation:
  - Run retrieval against each subject's ground-truth manifest and verify precision/recall meet minimum thresholds.
  - Manual review of generated dossiers by the participants themselves (does the narrative match their actual period?).
  - Stress test indexing and retrieval at corpus scale (~1M images).
  - Validate pet retrieval accuracy separately — expected to be lower than human face retrieval; set appropriate thresholds.
- Acceptance criteria:
  - Human retrieval recall >= 80% on participant ground-truth sets (faces visible in photo).
  - Human retrieval precision >= 90% at default threshold.
  - Pet retrieval recall >= 70% on ground-truth sets (pet face visible).
  - Pet retrieval precision >= 80% at default threshold.
  - Generated dossiers judged "mostly accurate" by participants for >= 75% of timeline events.
  - Multi-day dossiers correctly group photos by day in >= 95% of cases where timestamps are available.

## 12. Code Style and Quality

- Style:
  - Follow project CLAUDE.md conventions (Python 3.12+, ruff, mypy, structlog, pydantic).
  - Line length: 100 characters.
  - `from __future__ import annotations` in every module.
- Documentation:
  - Docstrings for core pipeline modules.
  - Participant data collection guide with photo requirements.
  - Pet photo collection guide (face visibility, multiple angles, unique markings).
- Clarity:
  - Modular pipeline stages that can be tested and run independently.
  - Clear configuration for model choices, thresholds, and corpus paths.
  - Subject type abstraction: shared interfaces for human and pet pipelines with type-specific implementations.

## 13. Workflow and Tools Usage

- Workflow for implementation:
  1. Corpus ingestion and EXIF metadata extraction.
  2. Human face detection and embedding pipeline.
  3. Pet face detection and embedding pipeline.
  4. FAISS index construction and type-filtered search.
  5. Reference photo query API with subject type selection.
  6. Metadata extraction and multi-day timeline construction.
  7. VLM photo description + LLM multi-day dossier generation.
  8. Interactive web UI (React SPA).
  9. Ground-truth evaluation tooling with per-type breakdowns.
- At each step, provide configurable model/threshold hooks and verify with tests before moving to the next stage.

## 14. Out of Scope / Boundaries

- No real-time video processing — this is a batch/interactive photo retrieval system.
- No biometric identification for security or surveillance purposes — this is a collaborative research experiment with consenting participants.
- No external API calls to identify people or pets (no social media lookups, no public face databases).
- No complex user authentication or multi-tenant features in v1.
- No mobile app in v1 — the mobile-ready architecture is a design constraint, not a v1 deliverable. The web SPA should be responsive enough to be functional on mobile browsers as a stopgap.
- No push notifications in v1 — polling and SSE only.
- No offline mode in v1 — requires network connectivity.
- No client-side image processing (face detection runs server-side only in v1; mobile v2 may add on-device detection).
- No direct Apple Photos API or Google Photos API integration in v1 — the web app uses standard browser file picker only. Cloud photo integration is a v2 mobile deliverable.
- No server-side cloud photo sync — the system never connects to users' Apple/Google accounts directly. The mobile app downloads selected photos locally and uploads them to the backend. The backend only receives image files, never cloud credentials.
- No wild/stray animal identification — pets only, with owner-provided reference photos.
- No cross-species matching (will not match a cat reference against dog photos).
- No automatic participant photo collection — participants manually contribute their photos.

## 15. Output Format for This Session

- When implementing:
  - Provide code as organized file snippets with clear file paths.
  - Precede major changes with a short plan.
  - Include instructions for corpus preparation, indexing, and running the application.
  - Document model download steps and hardware requirements.
  - Note any differences in setup between human and pet detection model dependencies.

## Appendix A: Photo Source Matrix

| Source | Platform | v1 (Web) | v2 (Mobile) |
|--------|----------|----------|-------------|
| File picker (local files) | Web | Browser `<input type="file">` | — |
| Camera roll / gallery | iOS / Android | — | Native picker |
| Apple Photos (incl. iCloud) | iOS | — | `PHPickerViewController` |
| Google Photos | Android | — | Photo Picker / Library API |
| Camera capture | iOS / Android | — | Native camera API |
| Drag and drop | Web | Browser drag-and-drop zone | — |

The backend is source-agnostic — it receives image files + optional metadata JSON via `POST /photos/upload`. It never knows or cares whether the photo came from a browser file picker, Apple Photos, Google Photos, or a camera. All platform-specific logic lives in the client.

## Appendix B: Architectural Decisions for Mobile-Readiness

| Decision | Why |
|----------|-----|
| API-first, headless backend | Same endpoints serve web, mobile, and any future client |
| Stateless backend, token auth | Mobile apps cannot rely on cookies/sessions |
| Images served by URL, never inlined | Mobile clients need to lazy-load, cache, and resize independently |
| Async jobs with polling + SSE | Mobile networks are unreliable; long-running ops must not block HTTP requests |
| Cursor-based pagination | Supports infinite scroll, stable across insertions (unlike offset) |
| OpenAPI as contract | Auto-generate typed clients for React (web) and React Native / Flutter (mobile) |
| Separate deployable artifacts | Backend, web, and mobile ship independently; API versioning handles drift |
| Responsive web as interim mobile | Users get mobile-browser access in v1 before the native app ships in v2 |
