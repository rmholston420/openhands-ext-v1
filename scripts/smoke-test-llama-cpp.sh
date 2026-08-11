#!/usr/bin/env bash
# scripts/smoke-test-llama-cpp.sh
#
# Phase -1 §-1.5 SDK-to-runtime smoke test — llama.cpp side.
#
# Starts llama-server serving qwen2.5-1.5b-instruct Q4_K_M on port 8082,
# waits for /health to return OK, sends one chat completion request via the
# OpenAI-compatible endpoint, then shuts down the server.
#
# Success criteria:
#   - server binds and reports "server is listening"
#   - /health returns 200
#   - /v1/chat/completions returns a non-empty assistant message
#   - GPU utilization > 0 during the request (indicating CUDA path active)
#
# Port choice: 8082 (spec §0.1 Fast tier uses 8082 for llama.cpp).
# Port 8000 is occupied on Colossus per session probe; avoid conflict.
#
# Log: /tmp/openhands-ext-v1-smoke-llama-cpp-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-smoke-llama-cpp-$(date +%s).log"

SERVER_BIN="$REPO_ROOT/vendor/llama.cpp/build/bin/llama-server"
GGUF="$REPO_ROOT/models/qwen2.5-1.5b-instruct/gguf/qwen2.5-1.5b-instruct-q4_k_m.gguf"
PORT="8082"

if [ ! -x "$SERVER_BIN" ]; then
  echo "FAIL: llama-server not built at $SERVER_BIN — run scripts/build-llama-cpp.sh" >&2
  exit 1
fi
if [ ! -f "$GGUF" ]; then
  echo "FAIL: GGUF missing at $GGUF — run scripts/pull-models.sh" >&2
  exit 1
fi

# Ensure port is free
if ss -tln "sport = :$PORT" | grep -q LISTEN; then
  echo "FAIL: port $PORT already in use" >&2
  ss -tln "sport = :$PORT" >&2
  exit 1
fi

SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "stopping llama-server (pid $SERVER_PID)"
    kill "$SERVER_PID" 2>/dev/null || true
    sleep 2
    kill -9 "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

{
  echo "===== smoke-test-llama-cpp start — $(date -Iseconds) ====="
  echo "server: $SERVER_BIN"
  echo "gguf:   $GGUF"
  echo "port:   $PORT"

  # 1. Start server
  echo ""
  echo "--- starting llama-server ---"
  "$SERVER_BIN" \
    -m "$GGUF" \
    --host 127.0.0.1 --port "$PORT" \
    -c 4096 \
    -ngl 999 \
    --log-disable 2>/dev/null >/tmp/llama-server-$PORT.log 2>&1 &
  SERVER_PID=$!
  echo "server pid: $SERVER_PID"

  # 2. Wait for /health
  echo ""
  echo "--- waiting for /health ---"
  for i in $(seq 1 60); do
    if curl -sf "http://127.0.0.1:$PORT/health" -o /dev/null; then
      echo "health OK after ${i}s"
      break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "FAIL: server exited during startup — check /tmp/llama-server-$PORT.log" >&2
      tail -40 /tmp/llama-server-$PORT.log >&2
      exit 1
    fi
    sleep 1
  done
  curl -sf "http://127.0.0.1:$PORT/health" | jq . || true

  # 3. GPU snapshot before
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
  METADATA_FILE="bench/results/phase-neg-1-smoke-llama-cpp-$(date -u +%Y%m%dT%H%M%SZ).json"
  cat > "$METADATA_FILE" <<JSON
{
  "phase": "-1.5",
  "component": "llama.cpp smoke",
  "status": "pass",
  "timestamp_utc": "$(date -u -Iseconds)",
  "model": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
  "port": $PORT,
  "assistant_content": $(printf '%s' "$CONTENT" | jq -Rs .),
  "gpu_snapshot_after": $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader | head -1 | jq -Rs .)
}
JSON
  echo ""
  echo "recorded: $METADATA_FILE"

  echo ""
  echo "===== smoke-test-llama-cpp done — $(date -Iseconds) ====="
} 2>&1 | tee "$LOG"
