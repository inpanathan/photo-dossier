#!/usr/bin/env bash
# Start the inference service on the 7810 node.
# Usage: bash scripts/start_inference.sh [--stop]

set -euo pipefail

REMOTE_HOST="100.111.31.125"
REMOTE_DIR="/home/vinpanathan/projects/dossier-inference"
PORT=8010

if [[ "${1:-}" == "--stop" ]]; then
    echo "Stopping inference service on $REMOTE_HOST..."
    ssh "$REMOTE_HOST" "pkill -f 'uvicorn main:app.*$PORT' 2>/dev/null || true"
    echo "Stopped."
    exit 0
fi

echo "=== Starting Dossier Inference Service ==="
echo "Host: $REMOTE_HOST"
echo "Port: $PORT"
echo ""

# Kill any existing process on the port
ssh "$REMOTE_HOST" "pkill -f 'uvicorn main:app.*$PORT' 2>/dev/null || true"
sleep 2

# Start the service
ssh "$REMOTE_HOST" "cd $REMOTE_DIR && CUDA_VISIBLE_DEVICES=0 nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port $PORT > /tmp/inference.log 2>&1 &"

echo "Waiting for models to load (this takes ~45 seconds)..."

# Poll for readiness
for i in $(seq 1 60); do
    if curl -sf "http://$REMOTE_HOST:$PORT/health" > /dev/null 2>&1; then
        echo ""
        echo "Inference service is ready!"
        curl -s "http://$REMOTE_HOST:$PORT/health" | python3 -m json.tool
        exit 0
    fi
    printf "."
    sleep 2
done

echo ""
echo "ERROR: Service did not start within 120 seconds."
echo "Check logs: ssh $REMOTE_HOST 'tail -50 /tmp/inference.log'"
exit 1
