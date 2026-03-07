#!/usr/bin/env bash
# Start the VLM (Vision-Language Model) service on the 7810 node.
# Uses vLLM to serve Qwen2.5-VL-7B-Instruct on GPU 1, port 8011.
# Usage: bash scripts/start_vlm.sh [--stop]
#
# Prerequisites:
#   On 7810, install vLLM:  pip install vllm
#   Model will be auto-downloaded on first start (~15GB).

set -euo pipefail

REMOTE_HOST="100.111.31.125"
PORT=8011
MODEL="Qwen/Qwen2.5-VL-7B-Instruct"
GPU_ID=1

if [[ "${1:-}" == "--stop" ]]; then
    echo "Stopping VLM service on $REMOTE_HOST..."
    ssh "$REMOTE_HOST" "pkill -f 'vllm.*$PORT' 2>/dev/null || true"
    echo "Stopped."
    exit 0
fi

echo "=== Starting Dossier VLM Service ==="
echo "Host:  $REMOTE_HOST"
echo "Port:  $PORT"
echo "Model: $MODEL"
echo "GPU:   $GPU_ID"
echo ""

# Kill any existing process on the port
ssh "$REMOTE_HOST" "pkill -f 'vllm.*$PORT' 2>/dev/null || true"
sleep 2

# Start vLLM with OpenAI-compatible API
ssh "$REMOTE_HOST" "CUDA_VISIBLE_DEVICES=$GPU_ID nohup python -m vllm.entrypoints.openai.api_server \
    --model $MODEL \
    --port $PORT \
    --host 0.0.0.0 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.90 \
    --trust-remote-code \
    > /tmp/vlm.log 2>&1 &"

echo "Waiting for model to load (this takes 2-5 minutes)..."

# Poll for readiness
for i in $(seq 1 180); do
    if curl -sf "http://$REMOTE_HOST:$PORT/v1/models" > /dev/null 2>&1; then
        echo ""
        echo "VLM service is ready!"
        curl -s "http://$REMOTE_HOST:$PORT/v1/models" | python3 -m json.tool
        exit 0
    fi
    printf "."
    sleep 2
done

echo ""
echo "ERROR: VLM service did not start within 6 minutes."
echo "Check logs: ssh $REMOTE_HOST 'tail -100 /tmp/vlm.log'"
exit 1
