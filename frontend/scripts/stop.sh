#!/usr/bin/env bash
# Stop the frontend dev server.
# Usage: bash frontend/scripts/stop.sh

set -euo pipefail

PORT=5173

PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
if [[ -z "$PIDS" ]]; then
    echo "No frontend dev server running on port $PORT"
    exit 0
fi

echo "$PIDS" | xargs kill 2>/dev/null || true
echo "Stopped frontend dev server (port $PORT)"
