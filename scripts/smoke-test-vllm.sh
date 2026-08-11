#!/usr/bin/env bash
# scripts/smoke-test-vllm.sh
#
# Phase -1 §-1.5 SDK-to-runtime smoke test — vLLM side.
#
# Serves Qwen2.5-1.5B-Instruct (safetensors) on port 8083 via `vllm serve`,
# waits for /health, sends one chat completion, records GPU state, shuts
# down. Writes a metadata JSON with an explicit `status` field so
# `session-end.sh` can refuse false claims of Verification-table green.
#
# PREFLIGHT: refuses to start if the desired GPU memory budget is not free.
# On Colossus we sometimes have the compositor/browser/IDE holding many GiB.
# The failure that motivated this preflight is documented in DEBUG_LOG.md
# 2026-08-11.
#
# Envs:
#   VLLM_GPU_MEM_UTIL    default 0.55 (was 0.6; lowered after 2026-08-11 OOM)
#   VLLM_MAX_MODEL_LEN   default 4096
#   VLLM_STARTUP_TIMEOUT default 240 (cold start on 5090 is 60-180s)
#   VLLM_MIN_FREE_GIB    default 20  (preflight refuses if < this free)
#
# Log: /tmp/openhands-ext-v1-smoke-vllm-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# --- flashinfer Blackwell (SM_120) workaround (2026-08-11) ---
# flashinfer 0.6.16.post3 (bundled with vllm 0.27.0) cannot query SM_120
# device capability under CUDA <12.9 and falls through check_cuda_arch()
# which then raises the misleading "FlashInfer requires GPUs with sm75 or
# higher". Disabling the flashinfer sampler forces vLLM's native top-k/top-p
# path. See DEBUG_LOG.md 2026-08-11 and ADR-0005. Permanent fix (flashinfer
# upgrade + CUDA >=12.9) deferred to Phase 0.
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
# --- end workaround ---

LOG="/tmp/openhands-ext-v1-smoke-vllm-$(date +%s).log"
VENV_BIN="$REPO_ROOT/.venv/bin"
VLLM="$VENV_BIN/vllm"
HF_MODEL_DIR="$REPO_ROOT/models/qwen2.5-1.5b-instruct/hf"
PORT="8083"

GPU_MEM_UTIL="${VLLM_GPU_MEM_UTIL:-0.55}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-4096}"
STARTUP_TIMEOUT="${VLLM_STARTUP_TIMEOUT:-240}"
MIN_FREE_GIB="${VLLM_MIN_FREE_GIB:-20}"

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

# GPU memory preflight
#
# Rationale: on 2026-08-11 vllm failed startup with "Free memory on device
# cuda:0 (2.49/31.39 GiB) on startup is less than desired GPU memory
# utilization (0.6, 18.84 GiB)". A cheaper `nvidia-smi` check surfaces this
# before the ~60s vllm cold start.
FREE_MIB="$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1 | tr -d ' ')"
TOTAL_MIB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')"
FREE_GIB="$(awk -v m="$FREE_MIB" 'BEGIN { printf "%.2f", m/1024 }')"
TOTAL_GIB="$(awk -v m="$TOTAL_MIB" 'BEGIN { printf "%.2f", m/1024 }')"
NEEDED_GIB="$(awk -v t="$TOTAL_MIB" -v u="$GPU_MEM_UTIL" 'BEGIN { printf "%.2f", t*u/1024 }')"

echo "GPU: free=${FREE_GIB} GiB / total=${TOTAL_GIB} GiB (need ~${NEEDED_GIB} GiB for --gpu-memory-utilization=${GPU_MEM_UTIL})"

if [ "$(awk -v f="$FREE_GIB" -v n="$MIN_FREE_GIB" 'BEGIN { print (f<n) ? 1 : 0 }')" = "1" ]; then
  echo "" >&2
  echo "FAIL: only ${FREE_GIB} GiB free on cuda:0 (need >= ${MIN_FREE_GIB} GiB)" >&2
  echo "" >&2
  echo "Top VRAM consumers (from nvidia-smi):" >&2
  nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv,noheader >&2 || true
  echo "" >&2
  echo "Options:" >&2
  echo "  1. Close browser/IDE/other GPU apps and re-run." >&2
  echo "  2. Lower target:  VLLM_GPU_MEM_UTIL=0.3 VLLM_MIN_FREE_GIB=10 bash scripts/smoke-test-vllm.sh" >&2
  echo "  3. Kill orphaned processes:  fuser -k /dev/nvidia*  (aggressive)" >&2
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

STATUS="fail"
ASSISTANT_CONTENT=""

{
  echo "===== smoke-test-vllm start — $(date -Iseconds) ====="
  echo "vllm:                $VLLM"
  echo "model:               $HF_MODEL_DIR"
  echo "port:                $PORT"
  echo "gpu-memory-util:     $GPU_MEM_UTIL"
  echo "max-model-len:       $MAX_MODEL_LEN"
  echo "startup-timeout:     ${STARTUP_TIMEOUT}s"
  echo "free VRAM at start:  ${FREE_GIB}/${TOTAL_GIB} GiB"

  echo ""
  echo "--- starting vllm serve ---"
  "$VLLM" serve "$HF_MODEL_DIR" \
    --host 127.0.0.1 --port "$PORT" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEM_UTIL" \
    --served-model-name qwen2.5-1.5b-instruct \
    >/tmp/vllm-server-$PORT.log 2>&1 &
  SERVER_PID=$!
  echo "server pid: $SERVER_PID"

  echo ""
  echo "--- waiting for /health (up to ${STARTUP_TIMEOUT}s) ---"
  HEALTH_OK=0
  for i in $(seq 1 "$STARTUP_TIMEOUT"); do
    if curl -sf "http://127.0.0.1:$PORT/health" -o /dev/null; then
      echo "health OK after ${i}s"
      HEALTH_OK=1
      break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "FAIL: vllm exited during startup — check /tmp/vllm-server-$PORT.log" >&2
      echo "" >&2
      echo "--- last 80 lines of vllm log ---" >&2
      tail -80 /tmp/vllm-server-$PORT.log >&2 || true
      exit 1
    fi
    sleep 1
  done
  if [ "$HEALTH_OK" -ne 1 ]; then
    echo "FAIL: vllm did not become healthy in ${STARTUP_TIMEOUT}s" >&2
    tail -80 /tmp/vllm-server-$PORT.log >&2 || true
    exit 1
  fi

  echo ""
  echo "--- GPU snapshot (before request) ---"
  nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader

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
  ASSISTANT_CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // empty')
  if [ -z "$ASSISTANT_CONTENT" ]; then
    echo "FAIL: empty assistant content" >&2
    exit 1
  fi
  echo ""
  echo "assistant said: $ASSISTANT_CONTENT"

  echo ""
  echo "--- GPU snapshot (after request) ---"
  nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader

  STATUS="pass"

  mkdir -p bench/results
  METADATA_FILE="bench/results/phase-neg-1-smoke-vllm-$(date -u +%Y%m%dT%H%M%SZ).json"
  cat > "$METADATA_FILE" <<JSON
{
  "phase": "-1.5",
  "component": "vllm smoke",
  "status": "$STATUS",
  "timestamp_utc": "$(date -u -Iseconds)",
  "model": "Qwen2.5-1.5B-Instruct (safetensors)",
  "port": $PORT,
  "config": {
    "gpu_memory_utilization": $GPU_MEM_UTIL,
    "max_model_len": $MAX_MODEL_LEN
  },
  "assistant_content": $(printf '%s' "$ASSISTANT_CONTENT" | jq -Rs .),
  "gpu_snapshot_after": $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader | head -1 | jq -Rs .)
}
JSON
  echo ""
  echo "recorded: $METADATA_FILE"

  echo ""
  echo "===== smoke-test-vllm done — $(date -Iseconds) ====="
} 2>&1 | tee "$LOG"
