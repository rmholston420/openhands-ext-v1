#!/usr/bin/env bash
# scripts/serve-planner.sh
#
# Start the production planner role — qwen3_6-35b-a3b-q4kxl-gguf on llama.cpp,
# port 8082. Per ADR-0017 (production role selection) and ADR-0015 (thinker
# 2507-awq eliminated from planner Medium tier). Thinking disabled by
# default per ADR-0008.
#
# Prereqs:
#   - GGUF file at models/qwen3_6-35b-a3b-q4kxl-gguf/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf
#     (run scripts/pull-models.sh first if missing).
#   - Coder NOT running (co-residency Option 2, ADR-0017). If port 8100 is
#     listening, run scripts/stop-large-model.sh coder first. (Coder port
#     amended twice: 8000->8001 2026-08-11 06:10 EDT, 8001->8100 2026-08-11
#     06:24 EDT; OpenHands holds 8000 agent + 8001 node frontend.)
#   - Free VRAM >= 24 GiB (weights ~21 GiB + Q8_0 KV cache ~3-6 GiB @ 32k ctx).
#
# Envs:
#   LLAMA_CTX_SIZE     default 32768
#   LLAMA_NGL          default 999   (offload all layers)
#   LLAMA_FA           default on    (flash attention)
#   LLAMA_KV_TYPE      default q8_0  (KV cache dtype; halves KV memory)
#   LLAMA_STARTUP_TIMEOUT default 180
#
# Runs in foreground.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

SERVER_BIN="$REPO_ROOT/vendor/llama.cpp/build/bin/llama-server"
GGUF="$REPO_ROOT/models/qwen3_6-35b-a3b-q4kxl-gguf/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf"
PORT="8082"
SERVED_NAME="qwen3_6-35b-a3b-q4kxl-gguf"

CTX_SIZE="${LLAMA_CTX_SIZE:-32768}"
NGL="${LLAMA_NGL:-999}"
KV_TYPE="${LLAMA_KV_TYPE:-q8_0}"
STARTUP_TIMEOUT="${LLAMA_STARTUP_TIMEOUT:-180}"

if [ ! -x "$SERVER_BIN" ]; then
  echo "FAIL: llama-server not built at $SERVER_BIN — run scripts/build-llama-cpp.sh" >&2
  exit 1
fi
if [ ! -f "$GGUF" ]; then
  echo "FAIL: GGUF missing at $GGUF" >&2
  echo "Run: huggingface-cli download unsloth/Qwen3.6-35B-A3B-GGUF Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf --local-dir $(dirname $GGUF)" >&2
  exit 1
fi
if ss -tln "sport = :$PORT" | grep -q LISTEN; then
  echo "FAIL: port $PORT already in use" >&2
  ss -tln "sport = :$PORT" >&2
  exit 1
fi
if ss -tln "sport = :8100" | grep -q LISTEN; then
  echo "FAIL: coder is running on port 8100 (co-residency Option 2 violation)" >&2
  echo "Run: bash scripts/stop-large-model.sh coder   # then retry" >&2
  exit 1
fi

echo "===== serve-planner start — $(date -Iseconds) ====="
echo "gguf:        $GGUF"
echo "served-name: $SERVED_NAME"
echo "port:        $PORT"
echo "ctx:         $CTX_SIZE"
echo "ngl:         $NGL  (all layers on GPU)"
echo "kv-type:     $KV_TYPE"
echo "thinking:    disabled (per ADR-0008 default; planner requests must not enable /think)"

exec "$SERVER_BIN" \
  -m "$GGUF" \
  --host 0.0.0.0 --port "$PORT" \
  --alias "$SERVED_NAME" \
  --ctx-size "$CTX_SIZE" \
  --n-gpu-layers "$NGL" \
  --flash-attn on \
  --cache-type-k "$KV_TYPE" \
  --cache-type-v "$KV_TYPE" \
  --parallel 1 \
  --jinja
