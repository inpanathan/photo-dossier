#!/usr/bin/env bash
# Run evaluation across all subjects in a ground-truth manifest.
# Usage: bash scripts/evaluate_all.sh [manifest_path] [--threshold 0.6] [--top-k 50]
#
# Outputs per-subject and aggregate metrics (JSON + human-readable).
# Requires: inference service running, FAISS index built.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

MANIFEST="${1:-data/evaluation/manifest.json}"
THRESHOLD="${THRESHOLD:-0.6}"
TOP_K="${TOP_K:-50}"
OUTPUT_DIR="${OUTPUT_DIR:-data/evaluation/results}"

# Parse optional args
shift 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --threshold) THRESHOLD="$2"; shift 2 ;;
        --top-k) TOP_K="$2"; shift 2 ;;
        --output) OUTPUT_DIR="$2"; shift 2 ;;
        *) shift ;;
    esac
done

echo "=== Dossier Evaluation ==="
echo "Manifest:  $MANIFEST"
echo "Threshold: $THRESHOLD"
echo "Top-K:     $TOP_K"
echo "Output:    $OUTPUT_DIR"
echo ""

if [[ ! -f "$MANIFEST" ]]; then
    echo "ERROR: Manifest file not found: $MANIFEST"
    echo ""
    echo "Create a manifest file with this structure:"
    echo '  {"subjects": [{"id": "person_1", "name": "Alice", "subject_type": "human",'
    echo '    "reference_photo": "ref/alice.jpg", "expected_photos": ["day1/img1.jpg"]}]}'
    exit 1
fi

# Check inference service
INFERENCE_URL="${INFERENCE__BASE_URL:-http://100.111.31.125:8010}"
echo "Checking inference service at $INFERENCE_URL..."
if ! curl -sf "$INFERENCE_URL/health" > /dev/null 2>&1; then
    echo "ERROR: Inference service not reachable at $INFERENCE_URL."
    echo "Start it first: bash scripts/start_inference.sh"
    exit 1
fi
echo "Inference service healthy."
echo ""

mkdir -p "$OUTPUT_DIR"

echo "Running evaluation..."
uv run python -c "
import json
import sys
from pathlib import Path

from src.evaluation.manifest import load_manifest
from src.evaluation.runner import evaluate
from src.embeddings.client import InferenceClient
from src.index.manager import IndexManager
from src.ingest.store import MetadataStore
from src.retrieval.service import RetrievalService

manifest_path = '$MANIFEST'
threshold = float('$THRESHOLD')
top_k = int('$TOP_K')
output_dir = Path('$OUTPUT_DIR')

# Load services
client = InferenceClient()
store = MetadataStore()
index = IndexManager()
retrieval = RetrievalService(client, index, store)

# Load manifest and run evaluation
subjects = load_manifest(manifest_path)
report = evaluate(subjects, retrieval, threshold=threshold, top_k=top_k)

# Write JSON report
report_dict = report.model_dump()
report_path = output_dir / 'evaluation_report.json'
with open(report_path, 'w') as f:
    json.dump(report_dict, f, indent=2, default=str)

# Print human-readable summary
print()
print('=== Evaluation Results ===')
print(f'Total subjects:  {report.total_subjects}')
print(f'Human subjects:  {report.human_count}')
print(f'Pet subjects:    {report.pet_count}')
print()
print('Aggregate Metrics:')
print(f'  Overall Precision: {report.overall_precision:.3f}')
print(f'  Overall Recall:    {report.overall_recall:.3f}')
print(f'  Overall F1:        {report.overall_f1:.3f}')
print()
if report.human_count > 0:
    print(f'  Human Precision:   {report.human_precision:.3f}')
    print(f'  Human Recall:      {report.human_recall:.3f}')
    print(f'  Human F1:          {report.human_f1:.3f}')
if report.pet_count > 0:
    print(f'  Pet Precision:     {report.pet_precision:.3f}')
    print(f'  Pet Recall:        {report.pet_recall:.3f}')
    print(f'  Pet F1:            {report.pet_f1:.3f}')
print()
if report.cross_type_confusions:
    print(f'Cross-type confusions: {len(report.cross_type_confusions)}')
    for c in report.cross_type_confusions[:5]:
        print(f'  {c}')
print()
print(f'Report saved to: {report_path}')

# Cleanup
store.close()
index.close()
client.close()
"

echo ""
echo "=== Evaluation complete ==="
