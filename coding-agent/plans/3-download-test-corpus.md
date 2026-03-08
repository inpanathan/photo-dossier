# Plan 3: Download Test Corpus Images

**Date**: 2026-03-07
**Goal**: Create script(s) to download ~1M random images (humans, animals, mixed) into `data/corpus/` for testing the Dossier pipeline.

## Strategy

Download from three complementary sources to get diverse coverage:

1. **COCO 2017** (~118K train images) — mixed scenes with people + animals together. Best match for real photo library. Via HuggingFace `datasets` library.
2. **Open Images V7** (~900K filtered) — filter for Person, Dog, Cat, Animal classes. Largest single source. Via the `openimages` downloader or `fiftyone`.
3. **Total target**: ~1M images across `data/corpus/{coco,open-images}/`

## Steps

- [x] 1. Add `datasets` and `fiftyone` (or `openimages`) to project deps as optional `corpus` extra
- [x] 2. Create `scripts/download_corpus.sh` — wrapper script with subcommands
- [x] 3. Create `scripts/download_corpus_coco.py` — Python worker for COCO download
- [x] 4. Create `scripts/download_corpus_openimages.py` — Python worker for Open Images download
- [x] 5. Update `docs/app_cheatsheet.md` with new script documentation
- [x] 6. Lint passes

## Directory Layout

```
data/corpus/
├── coco/           # COCO 2017 train images
│   ├── 000000.jpg
│   └── ...
└── open-images/    # Open Images V7 filtered
    ├── 000000.jpg
    └── ...
```

## Notes

- `data/corpus/` is already in `.gitignore`
- Downloads are resumable (skip existing files)
- Progress bars for large downloads
- No GPU required — just image files
