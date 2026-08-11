#!/usr/bin/env bash
# scripts/bootstrap-venv.sh
#
# Creates or refreshes the project-local Python venv at .venv/ and installs
# base tooling. Idempotent — safe to re-run.
#
# Design principles (learned the hard way):
#   - No `exec > >(tee ...)` at any scope. That redirection killed an
#     interactive shell on 2026-08-10.
#   - `set -e` is scoped to this script only, never leaks to the parent shell.
#   - Log to /tmp with a fixed filename so tail is easy.
#   - Uses the modern `hf` CLI, not the deprecated `huggingface-cli`.
#   - Does NOT export HF_HUB_ENABLE_HF_TRANSFER (deprecated); relies on default
#     Xet transport (or HF_XET_HIGH_PERFORMANCE=1 if the user opts in).
#
# Usage:
#   bash scripts/bootstrap-venv.sh
#
# After completion:
#   source .venv/bin/activate   # if you need the venv in your interactive shell

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-bootstrap-venv-$(date +%s).log"
echo "logging to $LOG"

{
  echo "===== bootstrap-venv start — $(date -Iseconds) ====="

  # 1. Verify python and venv module available.
  if ! command -v python3 >/dev/null 2>&1; then
    echo "FAIL: python3 not on PATH" >&2
    exit 1
  fi
  python3 -m venv --help >/dev/null 2>&1 || {
    echo "FAIL: python3 -m venv unavailable — apt install python3-venv" >&2
    exit 1
  }
  echo "python3: $(python3 --version)"

  # 2. Create venv if missing.
  if [ ! -x ".venv/bin/python" ]; then
    echo "creating .venv/"
    python3 -m venv .venv
  else
    echo ".venv already present"
  fi

  # 3. Upgrade pip/wheel/setuptools inside the venv.
  echo "--- upgrading pip/wheel/setuptools inside .venv ---"
  ./.venv/bin/python -m pip install --upgrade pip wheel setuptools

  # 4. Install the modern huggingface CLI (`hf`) and dependencies.
  # The `[cli]` extra is deprecated in huggingface_hub >=1.0; hf is bundled.
  echo "--- installing huggingface_hub (provides `hf` CLI) ---"
  ./.venv/bin/python -m pip install --upgrade 'huggingface_hub>=1.0'

  # 5. Sanity-check.
  echo ""
  echo "--- versions ---"
  ./.venv/bin/python --version
  ./.venv/bin/python -m pip --version
  ./.venv/bin/hf --version 2>&1 | head -1 || ./.venv/bin/python -m huggingface_hub.commands.huggingface_cli --version 2>&1 | head -1

  echo ""
  echo "===== bootstrap-venv done — $(date -Iseconds) ====="
  echo ""
  echo "To activate the venv in your shell:"
  echo "    source $REPO_ROOT/.venv/bin/activate"
} 2>&1 | tee "$LOG"
