#!/usr/bin/env bash
# scripts/serve-coder.sh
#
# Start the production coder role — qwen3-coder-30b-a3b-instruct-awq-4bit on
# vLLM, port 8001. Per ADR-0017 (production role selection, amended
# 2026-08-11 06:10 EDT to move coder 8000 -> 8001; OpenHands agent binds
# 127.0.0.1:8000 on Colossus) and ADR-0011#amendment-1 (tool-call parser =
# qwen3_coder).
#
# Prereqs:
#   - HF snapshot at models/qwen3-coder-30b-a3b-instruct-awq-4bit/hf/ (run
#     scripts/pull-models.sh first if missing).
#   - Planner NOT running (co-residency Option 2, ADR-0017). If port 8082
#     is listening, run scripts/stop-large-model.sh planner first.
#   - Free VRAM >= 20 GiB (weights ~17 GiB + KV budget).
#
# Envs:
#   VLLM_GPU_MEM_UTIL     default 0.90
#   VLLM_MAX_MODEL_LEN    default 32768
#   VLLM_STARTUP_TIMEOUT  default 300
#   VLLM_MIN_FREE_GIB     default 20
#
# Runs in foreground. Use `nohup scripts/serve-coder.sh &` or a tmux/screen
# session for detached serve.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

VENV_BIN="$REPO_ROOT/.venv/bin"
VLLM="$VENV_BIN/vllm"
HF_MODEL_DIR="$REPO_ROOT/models/qwen3-coder-30b-a3b-instruct-awq-4bit/hf"
PORT="8001"
SERVED_NAME="qwen3-coder-30b-a3b-instruct-awq-4bit"

GPU_MEM_UTIL="${VLLM_GPU_MEM_UTIL:-0.90}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-32768}"
STARTUP_TIMEOUT="${VLLM_STARTUP_TIMEOUT:-300}"
MIN_FREE_GIB="${VLLM_MIN_FREE_GIB:-20}"

if [ ! -x "$VLLM" ]; then
  echo "FAIL: vllm CLI not found at $VLLM — run scripts/install-vllm.sh" >&2
  exit 1
fi
if [ ! -f "$HF_MODEL_DIR/config.json" ]; then
  echo "FAIL: HF snapshot missing at $HF_MODEL_DIR" >&2
  echo "Run: huggingface-cli download cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit --local-dir $HF_MODEL_DIR" >&2
  exit 1
fi
if ss -tln "sport = :$PORT" | grep -q LISTEN; then
  echo "FAIL: port $PORT already in use" >&2
  ss -tln "sport = :$PORT" >&2
  exit 1
fi
if ss -tln "sport = :8082" | grep -q LISTEN; then
  echo "FAIL: planner is running on port 8082 (co-residency Option 2 violation)" >&2
  echo "Run: bash scripts/stop-large-model.sh planner   # then retry" >&2
  exit 1
fi

# GPU memory preflight (mirrors smoke-test-vllm.sh)
FREE_MIB="$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1 | tr -d ' ')"
FREE_GIB="$(awk -v m="$FREE_MIB" 'BEGIN { printf "%.2f", m/1024 }')"
echo "GPU free: ${FREE_GIB} GiB (need >= ${MIN_FREE_GIB} GiB)"
if [ "$(awk -v f="$FREE_GIB" -v n="$MIN_FREE_GIB" 'BEGIN { print (f<n) ? 1 : 0 }')" = "1" ]; then
  echo "FAIL: only ${FREE_GIB} GiB free — close browser/IDE or stop other GPU users" >&2
  nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv,noheader >&2 || true
  exit 1
fi

echo "===== serve-coder start — $(date -Iseconds) ====="
echo "model:       $HF_MODEL_DIR"
echo "served-name: $SERVED_NAME"
echo "port:        $PORT"
echo "gpu-mem:     $GPU_MEM_UTIL"
echo "max-len:     $MAX_MODEL_LEN"
echo "parser:      qwen3_coder (per ADR-0011 amendment 1)"

exec "$VLLM" serve "$HF_MODEL_DIR" \
  --host 0.0.0.0 --port "$PORT" \
  --served-model-name "$SERVED_NAME" \
  --max-model-len "$MAX_MODEL_LEN" \
  --gpu-memory-utilization "$GPU_MEM_UTIL" \
  --dtype auto \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --quantization awq_marlin
