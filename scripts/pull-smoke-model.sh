#!/usr/bin/env bash
# scripts/pull-models.sh
#
# Pulls the Phase -1 smoke-test model in both formats:
#   - GGUF (llama.cpp)          -> models/qwen2.5-1.5b-instruct/gguf/
#   - safetensors (vLLM)        -> models/qwen2.5-1.5b-instruct/hf/
#
# Uses the modern `hf` CLI from huggingface_hub >=1.0. Does NOT set
# HF_HUB_ENABLE_HF_TRANSFER (deprecated). Reuses ~/.cache/huggingface as the
# HF cache — no override.
#
# GGUF source: Qwen/Qwen2.5-1.5B-Instruct-GGUF (official Qwen repo)
#   file: qwen2.5-1.5b-instruct-q4_k_m.gguf   (~940 MB, sensible smoke default)
#
# safetensors source: Qwen/Qwen2.5-1.5B-Instruct (official Qwen repo)
#   full snapshot (~3 GB with tokenizer + config)
#
# Log: /tmp/openhands-ext-v1-pull-models-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-pull-models-$(date +%s).log"
VENV_BIN="$REPO_ROOT/.venv/bin"
HF="$VENV_BIN/hf"

if [ ! -x "$HF" ]; then
  echo "FAIL: hf CLI not found at $HF — run scripts/bootstrap-venv.sh first" >&2
  exit 1
fi

MODEL_DIR="$REPO_ROOT/models/qwen2.5-1.5b-instruct"
GGUF_DIR="$MODEL_DIR/gguf"
HF_DIR="$MODEL_DIR/hf"
GGUF_FILE="qwen2.5-1.5b-instruct-q4_k_m.gguf"

{
  echo "===== pull-models start — $(date -Iseconds) ====="
  echo "hf CLI: $($HF --version 2>&1 | head -1)"

  mkdir -p "$GGUF_DIR" "$HF_DIR"

  # 1. GGUF (single file)
  echo ""
  echo "--- pulling GGUF ($GGUF_FILE) ---"
  if [ -f "$GGUF_DIR/$GGUF_FILE" ]; then
    echo "already present: $GGUF_DIR/$GGUF_FILE"
  else
    "$HF" download Qwen/Qwen2.5-1.5B-Instruct-GGUF "$GGUF_FILE" \
      --local-dir "$GGUF_DIR"
  fi
  ls -la "$GGUF_DIR"

  # 2. safetensors (full snapshot)
  echo ""
  echo "--- pulling safetensors snapshot ---"
  # If already looks complete (has config.json + tokenizer.json + at least one .safetensors), skip.
  if [ -f "$HF_DIR/config.json" ] && [ -f "$HF_DIR/tokenizer.json" ] && ls "$HF_DIR"/*.safetensors >/dev/null 2>&1; then
    echo "snapshot already present at $HF_DIR"
  else
    "$HF" download Qwen/Qwen2.5-1.5B-Instruct \
      --local-dir "$HF_DIR"
  fi
  ls -la "$HF_DIR" | head -20

  # 3. Sanity: GGUF file size and safetensors count
  echo ""
  echo "--- sanity ---"
  GGUF_BYTES=$(stat -c '%s' "$GGUF_DIR/$GGUF_FILE" 2>/dev/null || echo 0)
  echo "GGUF file bytes: $GGUF_BYTES"
  ST_COUNT=$(ls "$HF_DIR"/*.safetensors 2>/dev/null | wc -l)
  echo "safetensors files: $ST_COUNT"
  [ "$GGUF_BYTES" -gt 100000000 ] || { echo "FAIL: GGUF file suspiciously small" >&2; exit 1; }
  [ "$ST_COUNT" -ge 1 ] || { echo "FAIL: no safetensors file present" >&2; exit 1; }

  echo ""
  echo "===== pull-models done — $(date -Iseconds) ====="
  echo "GGUF: $GGUF_DIR/$GGUF_FILE"
  echo "HF:   $HF_DIR"
} 2>&1 | tee "$LOG"
