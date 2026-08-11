#!/usr/bin/env bash
# scripts/install-vllm.sh
#
# Installs vLLM into the project-local venv at the current latest PyPI
# release. Per spec §-1.1: re-fetch live, don't pin from cache.
#
# vLLM requires a specific CUDA/PyTorch compatibility matrix. The pip install
# will pull an appropriate torch build. Colossus has CUDA 12.8 installed; vLLM
# wheels for cu121/cu128 exist. If the auto-selected wheel doesn't match,
# stop and escalate.
#
# Log: /tmp/openhands-ext-v1-install-vllm-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-install-vllm-$(date +%s).log"
VENV_PY="$REPO_ROOT/.venv/bin/python"
VENV_PIP="$VENV_PY -m pip"

if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv missing at $REPO_ROOT/.venv — run scripts/bootstrap-venv.sh first" >&2
  exit 1
fi

{
  echo "===== install-vllm start — $(date -Iseconds) ====="
  echo "venv: $VENV_PY"

  # 1. Re-fetch live version
  VLLM_V="$(curl -sf https://pypi.org/pypi/vllm/json | jq -r '.info.version')"
  if [ -z "$VLLM_V" ] || [ "$VLLM_V" = "null" ]; then
    echo "FAIL: could not fetch vllm version from PyPI" >&2
    exit 1
  fi
  echo "vllm target: $VLLM_V"

  # 2. Install (pip will pull matching torch)
  echo ""
  echo "--- pip install vllm==$VLLM_V ---"
  $VENV_PIP install --upgrade "vllm==$VLLM_V"

  # 3. Report installed versions
  echo ""
  echo "--- installed versions ---"
  for pkg in vllm torch; do
    $VENV_PIP show "$pkg" 2>/dev/null | grep -E '^(Name|Version|Location):'
    echo "  ---"
  done

  # 4. CUDA availability sanity
  echo ""
  echo "--- torch.cuda sanity ---"
  $VENV_PY -c "
import torch
print('torch:', torch.__version__)
print('cuda available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('cuda version (torch):', torch.version.cuda)
    print('device 0:', torch.cuda.get_device_name(0))
    print('capability:', torch.cuda.get_device_capability(0))
"

  # 5. Record actuals
  mkdir -p bench/results
  METADATA_FILE="bench/results/phase-neg-1-vllm-$(date -u +%Y%m%dT%H%M%SZ).json"
  TORCH_V="$($VENV_PIP show torch 2>/dev/null | awk '/^Version:/ {print $2}')"
  cat > "$METADATA_FILE" <<JSON
{
  "phase": "-1",
  "component": "vllm",
  "fetched_at_utc": "$(date -u -Iseconds)",
  "source": "pypi.org live",
  "vllm":  "$VLLM_V",
  "torch": "$TORCH_V"
}
JSON
  echo ""
  echo "recorded metadata: $METADATA_FILE"

  echo ""
  echo "===== install-vllm done — $(date -Iseconds) ====="
} 2>&1 | tee "$LOG"
