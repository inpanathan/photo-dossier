#!/usr/bin/env bash
# Download model weights needed by the Dossier system.
# Usage: bash scripts/download_models.sh [--remote-only] [--local-only]
#
# Downloads:
#   On 7810 (remote): InsightFace models (auto-downloaded by insightface lib)
#   On 7810 (remote): Qwen2.5-VL-7B-Instruct (downloaded by vLLM on first start)
#   On local machine:  Qwen2.5-14B-Instruct-AWQ (downloaded by vLLM on first start)
#
# Most models are auto-downloaded on first use. This script pre-fetches them
# to avoid delays during first inference.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

REMOTE_HOST="100.111.31.125"
REMOTE_DIR="/home/vinpanathan/projects/dossier-inference"

SKIP_REMOTE=false
SKIP_LOCAL=false

for arg in "$@"; do
    case "$arg" in
        --remote-only) SKIP_LOCAL=true ;;
        --local-only) SKIP_REMOTE=true ;;
    esac
done

echo "=== Dossier Model Download ==="
echo ""

# ---- Remote models (7810 node) ----
if [[ "$SKIP_REMOTE" == "false" ]]; then
    echo "--- Remote models (7810: $REMOTE_HOST) ---"

    # Check connectivity
    if ! ssh -o ConnectTimeout=5 "$REMOTE_HOST" 'echo ok' > /dev/null 2>&1; then
        echo "WARNING: Cannot reach $REMOTE_HOST. Skipping remote models."
    else
        # InsightFace models (buffalo_l) — auto-downloaded on import
        echo "1. InsightFace models (auto-download on first use)..."
        ssh "$REMOTE_HOST" "cd $REMOTE_DIR && python3 -c '
import insightface
app = insightface.app.FaceAnalysis(name=\"buffalo_l\", root=\".\")
print(\"InsightFace models ready.\")
' 2>/dev/null" && echo "   Done." || echo "   Skipped (run inference service to trigger download)."

        # YOLOv8 — auto-downloaded by ultralytics
        echo "2. YOLOv8 model (auto-download on first use)..."
        ssh "$REMOTE_HOST" "python3 -c '
from ultralytics import YOLO
model = YOLO(\"yolov8n.pt\")
print(\"YOLOv8 model ready.\")
' 2>/dev/null" && echo "   Done." || echo "   Skipped (install ultralytics on 7810)."

        # Qwen2.5-VL-7B — downloaded by vLLM or huggingface_hub
        echo "3. Qwen2.5-VL-7B-Instruct (large, ~15GB)..."
        echo "   This model is auto-downloaded when starting the VLM service."
        echo "   Run: bash scripts/start_vlm.sh"

        echo ""
    fi
fi

# ---- Local models ----
if [[ "$SKIP_LOCAL" == "false" ]]; then
    echo "--- Local models ---"

    # Qwen2.5-14B-Instruct-AWQ — for narrative dossier generation
    echo "1. Qwen2.5-14B-Instruct-AWQ (for dossier LLM)..."
    echo "   This model is auto-downloaded when starting vLLM locally."
    echo "   Start with: CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \\"
    echo "     --model Qwen/Qwen2.5-14B-Instruct-AWQ --port 8001"

    # Create data directories
    echo ""
    echo "2. Creating data directories..."
    mkdir -p data/{corpus,indices,uploads}
    echo "   Created data/corpus, data/indices, data/uploads"

    echo ""
fi

echo "=== Model download complete ==="
echo ""
echo "Notes:"
echo "  - Most models auto-download on first use via huggingface_hub"
echo "  - For gated models, set HF_TOKEN in your environment"
echo "  - Total disk space needed: ~40GB (all models combined)"
