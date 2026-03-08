# Summary: Market Research & Mobile Feasibility Analysis

**Date**: 2026-03-07

## Task

Research and document: (1) existing products in the market that overlap with Dossier's capabilities, (2) feasibility of running Dossier on mobile phones with on-device AI/ML, and (3) instructions for exporting Apple Photos to Google Drive using osxphotos.

## What Was Produced

### Market Landscape
- `docs/research/market-landscape.md` — Competitive analysis across three product categories:
  - Photo management with face recognition (Google Photos, Apple Photos, Immich, PhotoPrism, etc.)
  - Reverse face search (PimEyes, Facecheck.id, Clearview AI)
  - OSINT / intelligence platforms (Social Links, Maltego, Babel Street, Palantir)
- Feature comparison matrix showing Dossier's differentiators
- Market gaps and open questions for further research

### Mobile Feasibility
- `docs/research/mobile-feasibility.md` — Component-by-component analysis:
  - What can run on-device: face/pet detection, embeddings, EXIF, SQLite, small vector search
  - What cannot: 7B+ VLM, 14B LLM (need cloud/server)
  - Proposed hybrid architecture (on-device detection + cloud narrative)
  - Mobile framework options (native vs cross-platform)
  - Migration path from current Python/server codebase
  - Effort estimate by phase

### Apple Photos Export Instructions
- Provided detailed osxphotos export commands for Mac → Google Drive
- Covered: full export, date range, album filter, faces-only filter
- Included flag reference, HEIC handling, and resumability

## Key Decisions

- Research is exploratory — documented under `docs/research/` (new directory)
- No code changes; purely documentation
- Both research docs include "Open Questions" sections for future sessions
- Added `corpus` optional dependency group to `pyproject.toml` (user change: `datasets`, `Pillow`, `fiftyone`)
- Added `scripts/*.py` T20 ignore to ruff config (user change)

## Known Considerations

- Google Photos API has restrictions for new apps — Takeout may be more reliable for bulk download
- Mobile feasibility depends on hardware trajectory (~2027 for on-device 20B+ models)
- Apple App Store review is an open question for face-matching apps
- No corpus download script was created yet — deferred pending user's Google Photos approach decision
