# Project Specification for AI Coding Agent

## 1. Goal

- Build an interactive application that retrieves and (optionally) refines images of a “person of interest” from a face corpus based on a natural-language description.
- Explore whether machines can operate in a human-like regime of recognizing people by narrative descriptions rather than explicit identity labels.

## 2. Deliverables

- A working interactive UI for entering natural-language descriptions and viewing retrieved/refined images.
- Backend code for:
  - Multimodal embedding-based retrieval over a face image corpus.
  - Vision-language–based image refinement or regeneration conditioned on the narrative.
- Configurable pipeline to plug in different embedding and VLM models.
- Basic logging of queries, retrieved neighbors, and observed failures.
- Documentation:
  - README with setup and run instructions.
  - Short design overview of the retrieval + generation pipeline.

## 3. High-Level Requirements

- Users can submit free-form text descriptions of a person (e.g., “soft-spoken man in his 40s with glasses and kind eyes I met at a conference”).
- The system embeds the text and images in a shared space and retrieves nearest-neighbor face images.
- Optionally, the system uses a vision-language model to refine or regenerate a higher-fidelity image conditioned on the narrative and retrieved candidates.
- The task is purposely ambiguous; there is no single “correct” result. The system should support inspecting neighborhoods rather than just a single top-1 match.

## 4. Functional Requirements

### Feature 1: Natural-Language Query Input

- Purpose:
  - Allow users to describe a person of interest in unconstrained language.
- Inputs:
  - Text description of a person (short phrase to multi-sentence narrative).
- Outputs:
  - Parsed/cleaned text fed into the embedding model.
- Detailed behavior:
  - Provide a single text input box in the UI.
  - On submit, pass the text to the multimodal embedding model to obtain a text embedding.
- Edge cases:
  - Empty or extremely short queries (e.g., “person”): prompt user to add more detail.
  - Very long narratives: truncate or summarize if necessary while preserving key attributes.

### Feature 2: Embedding-Based Retrieval from Face Corpus

- Purpose:
  - Retrieve candidate faces whose embeddings are closest to the query description.
- Inputs:
  - Text embedding from the query.
  - Precomputed embeddings for images in the face corpus.
- Outputs:
  - Ranked list of nearest images (with distances/similarity scores).
- Detailed behavior:
  - Use a vector index (e.g., FAISS or a vector database) for nearest-neighbor search.
  - Support configurable top-k retrieval (e.g., k=20).
  - Display a grid of retrieved neighbors, not just the top-1 result.
- Edge cases:
  - No close matches (low similarity scores): still show neighbors but visually/verbally indicate uncertainty.
  - Highly similar but clearly different identities: highlight this as part of exploratory analysis.

### Feature 3: Vision-Language–Based Refinement/Generation

- Purpose:
  - Refine or regenerate a higher-fidelity image that better matches the narrative description.
- Inputs:
  - User’s narrative description.
  - Optionally, one or more retrieved images as context.
- Outputs:
  - A refined or newly generated image (or small set of candidates).
- Detailed behavior:
  - Use a vision-language model (VLM) to condition generation on both text and, optionally, reference images.
  - Provide a control in the UI to trigger refinement/generation after retrieval.
- Edge cases:
  - When generation fails or produces artifacts, show an error or fallback to retrieved neighbors.
  - Make clear that generated images are synthetic and may not correspond to a real person.

### Feature 4: Interactive UI

- Purpose:
  - Provide an accessible interface for experimentation and inspection of neighborhoods.
- Inputs:
  - User’s text description and UI actions (submit query, trigger generation).
- Outputs:
  - Displayed retrieved images, similarity scores, and generated/refined images.
- Detailed behavior:
  - Keep the interface simple: one main input, a “Search” button, and a display area for results.
  - Optionally allow toggling between different embedding models or datasets.
- Edge cases:
  - Avoid overloading the UI with options; prioritize clarity and inspection of neighborhoods.

### Feature 5: Logging and Diagnostics

- Purpose:
  - Capture failures and unexpected behavior for analysis.
- Inputs:
  - User query, retrieved neighbors, generation outcomes.
- Outputs:
  - Structured logs (e.g., JSON/CSV) with key information and error traces.
- Detailed behavior:
  - Log cases where retrieved or generated images seem clearly misaligned with the narrative (e.g., flagged by rules or user interaction).
  - Emphasize recording failures and ambiguous cases.

## 5. Non-Functional Requirements

- Performance:
  - Retrieval should be responsive for interactive use (ideally under a few seconds per query on the target hardware and dataset size).
- Reliability:
  - Graceful handling of missing embeddings, model loading errors, and timeouts.
- Interpretability:
  - Surface similarity scores and multiple neighbors to help users understand the embedding space, not just a single “answer.”
- Usability:
  - Simple, minimal UI where “insight beats polish.”
- Maintainability:
  - Modular components for embeddings, indexing, UI, and generation so models/datasets can be swapped easily.

## 6. Tech Stack and Constraints

- Programming languages:
  - Python for core logic.
- Frameworks/libraries:
  - PyTorch for model integration.
  - `deepface` for baseline face embeddings and sanity checks.
  - FAISS or a vector database for nearest-neighbor search.
  - Streamlit or NiceGUI for the user interface.
- Environment:
  - GPU strongly recommended for embedding and generation.
- Constraints:
  - Focus on research/experimentation quality rather than production hardening.
  - No requirement to identify real people; this is a retrieval/representation experiment.

## 7. Project Structure

- Suggested layout:
  - `src/embeddings/` – code to compute and load image/text embeddings.
  - `src/index/` – vector index construction and search.
  - `src/ui/` – UI application (Streamlit or NiceGUI).
  - `src/generation/` – vision-language refinement/generation code.
  - `configs/` – configuration files (model choices, dataset paths, index parameters).
  - `data/` – pointers to or scripts for downloading CelebA, LFW, etc.
  - `logs/` – query and failure logs.
- The agent should propose a concrete structure aligned with this outline.

## 8. Data and Models (AI/ML-Specific)

- Data:
  - Suggested face corpora:
    - CelebA (small, clean, well-studied).
    - LFW (classic but with limited diversity).
  - Preprocessing:
    - Scripts to download, verify, and align face images if needed.
    - Precompute image embeddings and store them alongside metadata.
- Models:
  - Embedding models:
    - SigLIP-2 for image-text embeddings (primary).
    - Any CLIP-compatible open-weight model for initial retrieval or comparison.
  - Vision-language model:
    - Qwen-2.5-VL (or similar) for vision-language reasoning and conditional image refinement/generation.
- Evaluation:
  - No single ground-truth label; evaluation is qualitative and exploratory.
  - Encourage inspection of neighborhoods and analysis of false positives/ambiguous cases.

## 9. Example Scenarios (Few-Shot Specs)

- Example 1
  - Input:
    - “A middle-aged woman with short gray hair, wearing glasses, who looks like a professor I met at a conference, very kind eyes.”
  - Expected processing steps:
    - Embed text, retrieve top-k faces from CelebA/LFW, display neighbors.
    - Optionally generate a refined image conditioned on the narrative and top-3 neighbors.
  - Expected output:
    - A grid of several plausible faces, with one or more that match many described attributes, plus an optional synthetic refined image.

- Example 2
  - Input:
    - “Young man, 20s, slightly messy dark hair, casual hoodie, looks thoughtful and introverted.”
  - Expected processing steps:
    - Same as above; highlight multiple candidates and their similarity scores.
  - Expected output:
    - Several plausible candidates; emphasis on showing neighborhood diversity rather than a single “correct” match.

## 10. Interfaces and APIs

- UI:
  - Web-based UI with:
    - Text input for the narrative description.
    - “Search” button to trigger retrieval.
    - Optional “Refine/Generate” button after results appear.
- Internal APIs (Python functions/modules):
  - `embed_text(text) -> vector`
  - `embed_images(image_batch) -> vectors`
  - `build_index(embeddings) -> index`
  - `search_index(index, query_vector, k) -> list[results]`
  - `refine_or_generate_image(description, reference_images) -> image(s)`

## 11. Testing and Validation

- Tests:
  - Unit tests for embedding functions, index search, and basic UI routes.
  - Sanity checks:
    - Known “obvious” descriptions should retrieve reasonably aligned images.
    - Retrieval consistency when rerunning the same query.
- Validation:
  - Manual inspection of neighborhoods for a curated set of test descriptions.
  - Logging of failure examples to support later analysis and refinements.

## 12. Code Style and Quality

- Style:
  - Python: follow standard idioms (e.g., PEP8-like conventions).
- Documentation:
  - Docstrings for core modules (embedding, search, UI, generation).
  - Comments explaining key design decisions (e.g., embedding choices, index parameters).
- Clarity:
  - Prefer readable, modular code over premature optimization.

## 13. Workflow and Tools Usage

- Workflow for the AI coding agent:
  - First, propose or confirm the project structure and main components.
  - Then implement:
    1. Data loading and embedding pipeline.
    2. Indexing and retrieval.
    3. Basic UI.
    4. Optional generation/refinement module.
  - At each step, explain assumptions and where configuration hooks are exposed.
- Clarifications:
  - When ambiguity arises (e.g., exact SigLIP-2 checkpoint), propose a reasonable default and note it clearly.

## 14. Out of Scope / Boundaries

- No requirement for real-world identity recognition or verification (not a biometric or security system).
- No strict quantitative benchmarking; focus is on qualitative behavior, ambiguity, and geometry.
- No complex user management, authentication, or production deployment features.

## 15. Output Format for This Session

- When implementing:
  - Provide code as organized file snippets with clear file paths.
  - Precede major changes with a short plan.
  - Include minimal instructions for running the app and preparing embeddings.
