#!/usr/bin/env bash
# Shared helper: run a command with 'b' to background, 'q' to stop.
#
# Usage (sourced from other scripts):
#   SERVICE_NAME="My Service"
#   PIDFILE="$PROJECT_ROOT/.my_service.pid"
#   LOGFILE="$PROJECT_ROOT/.my_service.log"
#   CMD="uv run python -m src.pipelines.my_service"
#   source scripts/_run_with_background.sh

set -euo pipefail

: "${SERVICE_NAME:?SERVICE_NAME must be set}"
: "${PIDFILE:?PIDFILE must be set}"
: "${LOGFILE:?LOGFILE must be set}"
: "${CMD:?CMD must be set}"

# Check if already running
if [[ -f "$PIDFILE" ]]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "$SERVICE_NAME already running (PID: $OLD_PID)"
        echo "  Stop it first or check: tail -f $LOGFILE"
        exit 1
    else
        rm -f "$PIDFILE"
    fi
fi

echo "Starting $SERVICE_NAME..."
echo ""

# Start process in background, tee output to log and screen
eval "$CMD" > >(tee "$LOGFILE") 2>&1 &
PROC_PID=$!
echo "$PROC_PID" > "$PIDFILE"

sleep 1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  $SERVICE_NAME running (PID: $PROC_PID)"
echo ""
echo "  Press 'b' to send to background"
echo "  Press 'q' to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

while true; do
    if ! kill -0 "$PROC_PID" 2>/dev/null; then
        echo ""
        echo "$SERVICE_NAME process exited."
        rm -f "$PIDFILE"
        exit 1
    fi

    read -rsn1 -t 1 key || continue

    case "$key" in
        b|B)
            disown "$PROC_PID"
            echo ""
            echo "$SERVICE_NAME sent to background (PID: $PROC_PID)"
            echo "  Logs:  tail -f $LOGFILE"
            echo "  Stop:  kill $PROC_PID"
            exit 0
            ;;
        q|Q)
            echo ""
            echo "Stopping $SERVICE_NAME (PID: $PROC_PID)..."
            kill "$PROC_PID" 2>/dev/null
            wait "$PROC_PID" 2>/dev/null
            rm -f "$PIDFILE"
            echo "$SERVICE_NAME stopped."
            exit 0
            ;;
    esac
done
