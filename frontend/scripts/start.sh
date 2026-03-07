#!/usr/bin/env bash
# Start the frontend dev server or production build.
# Usage: bash frontend/scripts/start.sh [build]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$FRONTEND_DIR"

if [[ "${1:-}" == "build" ]]; then
    echo "Building frontend for production..."
    npx vite build
    echo "Build complete. Serve from frontend/dist/"
    exit 0
fi

# Kill any existing dev server
lsof -ti:5173 2>/dev/null | xargs kill 2>/dev/null || true

echo "Starting frontend dev server on http://localhost:5173"
echo "Proxying /api to http://localhost:8000"
npx vite --host
