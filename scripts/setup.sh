#!/usr/bin/env bash
# First-time project setup script.
#
# Usage:
#   bash scripts/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=== Project Setup ==="
echo ""

# 1. Check prerequisites
echo "Checking prerequisites..."
for cmd in python3 uv git; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: $cmd is not installed."
        exit 1
    fi
done
echo "  All prerequisites found."
echo ""

# 2. Install dependencies (including dev extras)
echo "Installing dependencies..."
uv sync --extra dev
echo ""

# 3. Copy .env.example → .env if needed
if [[ ! -f .env ]]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "  Edit .env with your settings."
else
    echo ".env already exists — skipping."
fi
echo ""

# 4. Install pre-commit hooks
echo "Installing pre-commit hooks..."
uv run pre-commit install
echo ""

# 5. Create data directories
echo "Creating data directories..."
mkdir -p data/raw data/interim data/processed data/uploads
echo ""

# 6. Run tests to verify setup
echo "Running tests..."
uv run pytest tests/ -x -q
echo ""

echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  uv run python main.py          # Start the dev server"
echo "  uv run pytest tests/ -x -q     # Run tests"
echo "  uv run ruff check src/ tests/  # Lint"
