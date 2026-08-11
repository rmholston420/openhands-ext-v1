#!/usr/bin/env bash
# scripts/serve-embedder.sh
#
# Start the production embedder role — Qwen3-Embedding-4B-Q8_0 on llama.cpp,
# port 8090, CPU-resident. Per ADR-0017 amendment #3 (2026-08-11 06:39 EDT):
# embedder device corrected from GPU -> CPU to match integration-execution-plan-v16
# lines 159-161 (`-ngl 0 -c 4096`). Empirical: initial GPU config (-ngl 999,
# -c 32768) consumed ~10 GiB VRAM in practice (vs. ADR-0017 original claim of
# ~5 GiB), starving the coder. CPU-resident frees full 31.39 GiB VRAM budget
# for coder or planner.
#
# Port stays at 8090 (spec says 8083; deviation logged in ADR-0017 amendment #3
# to preserve health-check + selection.json convention already established).
#
# Prereqs:
#   - GGUF file at models/qwen3-embedding-4b-q8-gguf/Qwen3-Embedding-4B-Q8_0.gguf
#     (run scripts/pull-models.sh first if missing).
#   - Port 8090 free.
#
# Envs:
#   EMBED_CTX_SIZE       default 4096   (spec value; standard for embedders)
#   EMBED_NGL            default 0      (CPU-only per spec)
#   EMBED_BATCH_SIZE     default 512
#   EMBED_UBATCH_SIZE    default 512   (recommend >= 512 for embedding throughput)
#   LLAMA_STARTUP_TIMEOUT default 120
#
# Runs in foreground.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

SERVER_BIN="$REPO_ROOT/vendor/llama.cpp/build/bin/llama-server"
GGUF="$REPO_ROOT/models/qwen3-embedding-4b-q8-gguf/Qwen3-Embedding-4B-Q8_0.gguf"
PORT="8090"
SERVED_NAME="qwen3-embedding-4b-q8-gguf"

CTX_SIZE="${EMBED_CTX_SIZE:-4096}"
NGL="${EMBED_NGL:-0}"
BATCH_SIZE="${EMBED_BATCH_SIZE:-512}"
UBATCH_SIZE="${EMBED_UBATCH_SIZE:-512}"

if [ ! -x "$SERVER_BIN" ]; then
  echo "FAIL: llama-server not built at $SERVER_BIN — run scripts/build-llama-cpp.sh" >&2
  exit 1
fi
if [ ! -f "$GGUF" ]; then
  echo "FAIL: GGUF missing at $GGUF" >&2
  echo "Run: huggingface-cli download Qwen/Qwen3-Embedding-4B-GGUF Qwen3-Embedding-4B-Q8_0.gguf --local-dir $(dirname $GGUF)" >&2
  exit 1
fi
if ss -tln "sport = :$PORT" | grep -q LISTEN; then
  echo "FAIL: port $PORT already in use" >&2
  ss -tln "sport = :$PORT" >&2
  exit 1
fi

echo "===== serve-embedder start — $(date -Iseconds) ====="
echo "gguf:        $GGUF"
echo "served-name: $SERVED_NAME"
echo "port:        $PORT"
echo "ctx:         $CTX_SIZE"
echo "ngl:         $NGL"
echo "batch:       $BATCH_SIZE / ubatch $UBATCH_SIZE"

exec "$SERVER_BIN" \
  -m "$GGUF" \
  --host 0.0.0.0 --port "$PORT" \
  --alias "$SERVED_NAME" \
  --embedding \
  --pooling last \
  --ctx-size "$CTX_SIZE" \
  --n-gpu-layers "$NGL" \
  --batch-size "$BATCH_SIZE" \
  --ubatch-size "$UBATCH_SIZE" \
  --parallel 1
