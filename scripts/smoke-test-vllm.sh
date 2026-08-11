#!/usr/bin/env bash
# scripts/smoke-test-vllm.sh
#
# Phase -1 §-1.5 SDK-to-runtime smoke test — vLLM side.
#
# Serves Qwen2.5-1.5B-Instruct (safetensors) on port 8083 via `vllm serve`,
# waits for /health, sends one chat completion, records GPU state, shuts down.
#
# Port choice: 8083 (spec §0.1 Fast tier uses 8085 for vLLM; 8083 avoids
# collision with the llama.cpp smoke server on 8082 if both run in sequence).
#
# Log: /tmp/openhands-ext-v1-smoke-vllm-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-smoke-vllm-$(date +%s).log"
VENV_BIN="$REPO_ROOT/.venv/bin"
VLLM="$VENV_BIN/vllm"
HF_MODEL_DIR="$REPO_ROOT/models/qwen2.5-1.5b-instruct/hf"
PORT="8083"

if [ ! -x "$VLLM" ]; then
  echo "FAIL: vllm CLI not found at $VLLM — run scripts/install-vllm.sh" >&2
  exit 1
fi
if [ ! -f "$HF_MODEL_DIR/config.json" ]; then
  echo "FAIL: HF snapshot missing at $HF_MODEL_DIR — run scripts/pull-models.sh" >&2
  exit 1
fi
if ss -tln "sport = :$PORT" | grep -q LISTEN; then
  echo "FAIL: port $PORT already in use" >&2
  exit 1
fi

SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "stopping vllm (pid $SERVER_PID)"
    kill "$SERVER_PID" 2>/dev/null || true
    sleep 3
    kill -9 "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

{
  echo "===== smoke-test-vllm start — $(date -Iseconds) ====="
  echo "vllm:  $VLLM"
  echo "model: $HF_MODEL_DIR"
  echo "port:  $PORT"

  # 1. Start server
  echo ""
  echo "--- starting vllm serve ---"
  "$VLLM" serve "$HF_MODEL_DIR" \
    --host 127.0.0.1 --port "$PORT" \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.6 \
    --served-model-name qwen2.5-1.5b-instruct \
    >/tmp/vllm-server-$PORT.log 2>&1 &
  SERVER_PID=$!
  echo "server pid: $SERVER_PID"

  # 2. Wait for /health (vLLM cold start can take 60-120s)
  echo ""
  echo "--- waiting for /health (up to 180s) ---"
  for i in $(seq 1 180); do
    if curl -sf "http://127.0.0.1:$PORT/health" -o /dev/null; then
      echo "health OK after ${i}s"
      break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "FAIL: vllm exited during startup — check /tmp/vllm-server-$PORT.log" >&2
      tail -50 /tmp/vllm-server-$PORT.log >&2
      exit 1
    fi
    sleep 1
  done

  # 3. GPU snapshot before request
  echo ""
  echo "--- GPU snapshot (before request) ---"
  nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader

  # 4. Chat completion
  echo ""
  echo "--- POST /v1/chat/completions ---"
  RESPONSE=$(curl -sf -X POST "http://127.0.0.1:$PORT/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "qwen2.5-1.5b-instruct",
      "messages": [
        {"role":"system","content":"You are a helpful assistant. Reply in one short sentence."},
        {"role":"user","content":"Say hello and confirm you are running on the RTX 5090."}
      ],
      "max_tokens": 64,
      "temperature": 0.0
    }')
  echo "$RESPONSE" | jq .
  CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // empty')
  if [ -z "$CONTENT" ]; then
    echo "FAIL: empty assistant content" >&2
    exit 1
  fi
  echo ""
  echo "assistant said: $CONTENT"

  # 5. GPU snapshot after
  echo ""
  echo "--- GPU snapshot (after request) ---"
  nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader

  # 6. Metadata record
  mkdir -p bench/results
  METADATA_FILE="bench/results/phase-neg-1-smoke-vllm-$(date -u +%Y%m%dT%H%M%SZ).json"
  cat > "$METADATA_FILE" <<JSON
{
  "phase": "-1.5",
  "component": "vllm smoke",
  "timestamp_utc": "$(date -u -Iseconds)",
  "model": "Qwen2.5-1.5B-Instruct (safetensors)",
  "port": $PORT,
  "assistant_content": $(printf '%s' "$CONTENT" | jq -Rs .),
  "gpu_snapshot_after": $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader | head -1 | jq -Rs .)
}
JSON
  echo ""
  echo "recorded: $METADATA_FILE"

  echo ""
  echo "===== smoke-test-vllm done — $(date -Iseconds) ====="
} 2>&1 | tee "$LOG"
