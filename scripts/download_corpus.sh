#!/usr/bin/env bash
# Download test corpus images for the Dossier pipeline.
# Usage:
#   bash scripts/download_corpus.sh coco               # COCO 2017 train (~118K images)
#   bash scripts/download_corpus.sh open-images         # Open Images V7 filtered (~900K)
#   bash scripts/download_corpus.sh all                 # Both datasets
#
# Options:
#   --limit N       Max images to download (per source or per class)
#   --dry-run       Show what would be downloaded without downloading
#   --classes A B   (open-images only) Override default classes
#
# Images are saved to data/corpus/{coco,open-images}/
# Downloads are resumable — existing files are skipped.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

usage() {
    echo "Usage: bash scripts/download_corpus.sh {coco|open-images|all} [options]"
    echo ""
    echo "Sources:"
    echo "  coco          COCO 2017 train images (~118K, ~18GB)"
    echo "  open-images   Open Images V7 filtered by class (~900K)"
    echo "  all           Download both datasets"
    echo ""
    echo "Options:"
    echo "  --limit N     Max images to download"
    echo "  --dry-run     Preview without downloading"
    echo "  --classes A B (open-images only) Classes to filter"
    echo ""
    echo "Examples:"
    echo "  bash scripts/download_corpus.sh coco --limit 1000"
    echo "  bash scripts/download_corpus.sh open-images --limit 5000 --classes Person Dog"
    echo "  bash scripts/download_corpus.sh all --dry-run"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

SOURCE="$1"
shift

# Validate source argument
case "$SOURCE" in
    coco|open-images|all) ;;
    -h|--help) usage ;;
    *) echo "ERROR: Unknown source '$SOURCE'. Use coco, open-images, or all."; usage ;;
esac

# Collect remaining args to pass through
EXTRA_ARGS=("$@")

echo "=== Dossier Corpus Download ==="
echo "Source:       $SOURCE"
echo "Project root: $PROJECT_ROOT"
echo "Corpus dir:   data/corpus/"
echo ""

download_coco() {
    echo "--- COCO 2017 Train ---"
    uv run python scripts/download_corpus_coco.py "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
    echo ""
}

download_open_images() {
    echo "--- Open Images V7 ---"
    uv run python scripts/download_corpus_openimages.py "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
    echo ""
}

case "$SOURCE" in
    coco)
        download_coco
        ;;
    open-images)
        download_open_images
        ;;
    all)
        download_coco
        download_open_images
        ;;
esac

# Show corpus summary
echo "=== Corpus Summary ==="
if [[ -d "data/corpus/coco" ]]; then
    COCO_COUNT=$(find data/corpus/coco -name "*.jpg" 2>/dev/null | wc -l)
    echo "  COCO:        ${COCO_COUNT} images"
fi
if [[ -d "data/corpus/open-images" ]]; then
    OI_COUNT=$(find data/corpus/open-images -name "*.jpg" -o -name "*.png" 2>/dev/null | wc -l)
    echo "  Open Images: ${OI_COUNT} images"
fi
TOTAL=$(find data/corpus -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | wc -l)
echo "  Total:       ${TOTAL} images"
echo ""
echo "Next step: bash scripts/index_corpus.sh"
