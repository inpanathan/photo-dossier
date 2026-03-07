#!/usr/bin/env bash
# Index the photo corpus — runs the batch indexing pipeline.
# Usage: bash scripts/index_corpus.sh [corpus_dir] [--full]
#
# Options:
#   corpus_dir  Override corpus directory (default: from config)
#   --full      Force full reindex (skip incremental mode)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

CORPUS_DIR="${1:-}"
INCREMENTAL="true"

for arg in "$@"; do
    if [[ "$arg" == "--full" ]]; then
        INCREMENTAL="false"
    fi
done

echo "=== Dossier Corpus Indexing ==="
echo "Project root: $PROJECT_ROOT"
echo "Incremental:  $INCREMENTAL"

if [[ -n "$CORPUS_DIR" && "$CORPUS_DIR" != "--full" ]]; then
    echo "Corpus dir:   $CORPUS_DIR"
fi

# Check inference service is reachable
INFERENCE_URL="${INFERENCE__BASE_URL:-http://100.111.31.125:8010}"
echo ""
echo "Checking inference service at $INFERENCE_URL..."
if ! curl -sf "$INFERENCE_URL/health" > /dev/null 2>&1; then
    echo "ERROR: Inference service at $INFERENCE_URL is not reachable."
    echo "Start the inference service on 7810 first:"
    echo "  ssh 100.111.31.125 'cd ~/projects/dossier-inference && CUDA_VISIBLE_DEVICES=0 nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8010 > /tmp/inference.log 2>&1 &'"
    exit 1
fi
echo "Inference service is healthy."

echo ""
echo "Starting indexing..."
uv run python -c "
import sys
from src.embeddings.client import InferenceClient
from src.index.manager import IndexManager
from src.ingest.store import MetadataStore
from src.index.batch import BatchIndexer

corpus_dir = '${CORPUS_DIR}' or None
incremental = ${INCREMENTAL} == 'true'

client = InferenceClient()
store = MetadataStore()
index = IndexManager()
indexer = BatchIndexer(client, store, index)

def progress(p, msg):
    print(f'  [{p*100:.0f}%] {msg}')

stats = indexer.run(
    corpus_dir=corpus_dir,
    incremental=incremental,
    progress_callback=progress,
)

print()
print('=== Indexing Complete ===')
for k, v in stats.items():
    print(f'  {k}: {v}')

store.close()
index.close()
client.close()
"
