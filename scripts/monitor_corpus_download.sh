#!/usr/bin/env bash
# Monitor corpus download progress with ETA calculation.
# Stores last checkpoint in /tmp to calculate speed between runs.

STATE_FILE="/tmp/dossier_download_monitor.state"
COCO_TARGET=118287
NOW=$(date +%s)

# Current counts (use find to avoid ARG_MAX with large dirs)
COCO_COUNT=$(find data/corpus/coco -maxdepth 1 -name "*.jpg" 2>/dev/null | wc -l)
OI_COUNT=$(find data/corpus/open-images -maxdepth 1 \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | wc -l)
COCO_SIZE=$(du -sh data/corpus/coco/ 2>/dev/null | cut -f1)
OI_SIZE=$(du -sh data/corpus/open-images/ 2>/dev/null | cut -f1)
TOTAL_SIZE=$(du -sh data/corpus/ 2>/dev/null | cut -f1)

# Read previous state
PREV_TIME=0
PREV_COCO=0
PREV_OI=0
if [[ -f "$STATE_FILE" ]]; then
    source "$STATE_FILE"
fi

ELAPSED=$((NOW - PREV_TIME))

echo "=== Corpus Download Monitor — $(date '+%H:%M:%S') ==="
echo ""

# --- COCO ---
COCO_REMAINING=$((COCO_TARGET - COCO_COUNT))
if [[ $ELAPSED -gt 0 && $PREV_TIME -gt 0 ]]; then
    COCO_DELTA=$((COCO_COUNT - PREV_COCO))
    COCO_RATE=$((COCO_DELTA * 60 / ELAPSED))  # images per minute

    if [[ $COCO_RATE -gt 0 ]]; then
        COCO_ETA_MIN=$((COCO_REMAINING / COCO_RATE))
        COCO_ETA_H=$((COCO_ETA_MIN / 60))
        COCO_ETA_M=$((COCO_ETA_MIN % 60))
        COCO_PCT=$((COCO_COUNT * 100 / COCO_TARGET))
        echo "  COCO:  ${COCO_COUNT}/${COCO_TARGET} (${COCO_PCT}%) | ${COCO_SIZE}"
        echo "         Speed: ${COCO_RATE} img/min | +${COCO_DELTA} since last check"
        echo "         ETA:   ${COCO_ETA_H}h ${COCO_ETA_M}m remaining"
    elif [[ $COCO_COUNT -gt 100000 ]]; then
        echo "  COCO:  ${COCO_COUNT} images | ${COCO_SIZE}"
        echo "         COMPLETE"
    else
        COCO_PCT=$((COCO_COUNT * 100 / COCO_TARGET))
        echo "  COCO:  ${COCO_COUNT}/${COCO_TARGET} (${COCO_PCT}%) | ${COCO_SIZE}"
        echo "         Speed: stalled (0 new images)"
    fi
else
    COCO_PCT=$((COCO_COUNT * 100 / COCO_TARGET))
    echo "  COCO:  ${COCO_COUNT}/${COCO_TARGET} (${COCO_PCT}%) | ${COCO_SIZE}"
    echo "         Speed: calculating... (first run)"
fi


echo ""

# --- Open Images ---
if [[ $ELAPSED -gt 0 && $PREV_TIME -gt 0 ]]; then
    OI_DELTA=$((OI_COUNT - PREV_OI))
    OI_RATE=$((OI_DELTA * 60 / ELAPSED))

    if [[ $OI_COUNT -eq 0 ]]; then
        # Check fiftyone cache for actual progress
        OI_CACHE_COUNT=$(find ~/fiftyone/open-images-v7/train/data -maxdepth 1 -name "*.jpg" 2>/dev/null | wc -l)
        OI_CACHE_SIZE=$(du -sh ~/fiftyone/open-images-v7/train/data/ 2>/dev/null | cut -f1)
        if [[ $OI_CACHE_COUNT -gt 0 ]]; then
            echo "  Open Images: downloading images to fiftyone cache"
            echo "               ${OI_CACHE_COUNT} images cached (${OI_CACHE_SIZE})"
            echo "               Will copy to corpus dir when complete"
        else
            OI_META_SIZE=$(du -sh ~/fiftyone/open-images-v7/ 2>/dev/null | cut -f1)
            echo "  Open Images: downloading metadata (${OI_META_SIZE:-0} so far)"
            echo "               Images will start after metadata completes"
        fi
    elif [[ $OI_RATE -gt 0 ]]; then
        echo "  Open Images: ${OI_COUNT} images | ${OI_SIZE}"
        echo "               Speed: ${OI_RATE} img/min | +${OI_DELTA} since last check"
        # No fixed target for OI, so just show rate
    else
        echo "  Open Images: ${OI_COUNT} images | ${OI_SIZE}"
        echo "               Speed: stalled (0 new images)"
    fi
else
    if [[ $OI_COUNT -eq 0 ]]; then
        OI_CACHE_COUNT=$(find ~/fiftyone/open-images-v7/train/data -maxdepth 1 -name "*.jpg" 2>/dev/null | wc -l)
        OI_CACHE_SIZE=$(du -sh ~/fiftyone/open-images-v7/train/data/ 2>/dev/null | cut -f1)
        if [[ $OI_CACHE_COUNT -gt 0 ]]; then
            echo "  Open Images: downloading images to fiftyone cache"
            echo "               ${OI_CACHE_COUNT} images cached (${OI_CACHE_SIZE})"
        else
            OI_META_SIZE=$(du -sh ~/fiftyone/open-images-v7/ 2>/dev/null | cut -f1)
            echo "  Open Images: downloading metadata (${OI_META_SIZE:-0} so far)"
        fi
    else
        echo "  Open Images: ${OI_COUNT} images | ${OI_SIZE}"
        echo "               Speed: calculating... (first run)"
    fi
fi

echo ""
echo "  Total: $(( COCO_COUNT + OI_COUNT )) images | ${TOTAL_SIZE}"
echo ""

# Save state for next run
cat > "$STATE_FILE" <<EOF
PREV_TIME=${NOW}
PREV_COCO=${COCO_COUNT}
PREV_OI=${OI_COUNT}
EOF
