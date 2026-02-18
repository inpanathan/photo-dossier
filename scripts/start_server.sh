#!/usr/bin/env bash
# Start the application server.
#
# Usage:
#   ./scripts/start_server.sh              # dev mode (default)
#   ./scripts/start_server.sh staging      # staging mode
#   ./scripts/start_server.sh production   # production mode
#   ./scripts/start_server.sh docker       # docker mode (foreground, no reload)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

MODE="${1:-dev}"

case "$MODE" in
    dev)
        export APP_ENV=dev
        SERVICE_NAME="Dev Server"
        PIDFILE="$PROJECT_ROOT/.server.pid"
        LOGFILE="$PROJECT_ROOT/.server.log"
        CMD="uv run python main.py"
        source "$SCRIPT_DIR/_run_with_background.sh"
        ;;
    staging)
        export APP_ENV=staging
        SERVICE_NAME="Staging Server"
        PIDFILE="$PROJECT_ROOT/.server.pid"
        LOGFILE="$PROJECT_ROOT/.server.log"
        CMD="uv run python main.py"
        source "$SCRIPT_DIR/_run_with_background.sh"
        ;;
    production)
        export APP_ENV=production
        SERVICE_NAME="Production Server"
        PIDFILE="$PROJECT_ROOT/.server.pid"
        LOGFILE="$PROJECT_ROOT/.server.log"
        CMD="uv run python main.py"
        source "$SCRIPT_DIR/_run_with_background.sh"
        ;;
    docker)
        export APP_ENV="${APP_ENV:-production}"
        exec uv run python main.py
        ;;
    *)
        echo "Usage: $0 {dev|staging|production|docker}"
        exit 1
        ;;
esac
