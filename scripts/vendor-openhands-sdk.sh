#!/usr/bin/env bash
# scripts/vendor-openhands-sdk.sh
#
# Vendors openhands-sdk at the pinned commit (v1.41.0 =
# ca46719d5e9a0b0af79f7de2da37067a5b94563c), applies the
# DiscriminatedUnionMixin patch on `LLM` (per ADR-0034), and
# installs it editable into the project venv, replacing the pip-installed
# `openhands-sdk` (from `scripts/install-oh-sdk.sh`).
#
# Per ADR-0003: `vendor/` is category 2 (regenerable, gitignored, produced by
# a tracked script). Colossus regenerates the vendored tree by running this
# script. The pinned commit + tracked patch file (`patches/*.patch`) are
# authoritative; the tree itself is not committed.
#
# Per ADR-0034: `LLM` must inherit `DiscriminatedUnionMixin` so
# `Agent.llm: LLM` container-side deserialization dispatches to the correct
# concrete subclass (e.g. `CoderPlannerRouter`) instead of flattening to
# base `LLM` and losing `llms_for_routing`.
#
# Log: /tmp/openhands-ext-v1-vendor-oh-sdk-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-vendor-oh-sdk-$(date +%s).log"
VENDOR_DIR="$REPO_ROOT/vendor/openhands-sdk"
PATCH_FILE="$REPO_ROOT/patches/openhands-sdk-llm-discriminated-union.patch"
VENV_PY="$REPO_ROOT/.venv/bin/python"
VENV_PIP="$VENV_PY -m pip"

# Pinned per ADR-0034; upstream v1.41.0 tag.
UPSTREAM_URL="https://github.com/OpenHands/software-agent-sdk.git"
PIN_TAG="v1.41.0"
PIN_SHA="ca46719d5e9a0b0af79f7de2da37067a5b94563c"

if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv missing at $REPO_ROOT/.venv — run scripts/bootstrap-venv.sh first" >&2
  exit 1
fi

if [ ! -f "$PATCH_FILE" ]; then
  echo "FAIL: patch file missing at $PATCH_FILE" >&2
  exit 1
fi

{
  echo "===== vendor-openhands-sdk start — $(date -Iseconds) ====="
  echo "vendor_dir: $VENDOR_DIR"
  echo "pin_tag:    $PIN_TAG"
  echo "pin_sha:    $PIN_SHA"
  echo "patch:      $PATCH_FILE"

  echo ""
  echo "--- clean existing vendor tree (regenerable per ADR-0003) ---"
  rm -rf "$VENDOR_DIR"
  mkdir -p "$(dirname "$VENDOR_DIR")"

  echo ""
  echo "--- clone $PIN_TAG (shallow) ---"
  git clone --depth 1 --branch "$PIN_TAG" "$UPSTREAM_URL" "$VENDOR_DIR"

  echo ""
  echo "--- verify pinned commit ---"
  ACTUAL_SHA="$(git -C "$VENDOR_DIR" rev-parse HEAD)"
  if [ "$ACTUAL_SHA" != "$PIN_SHA" ]; then
    echo "FAIL: pinned commit mismatch" >&2
    echo "  expected: $PIN_SHA" >&2
    echo "  got:      $ACTUAL_SHA" >&2
    exit 1
  fi
  echo "OK: HEAD == $ACTUAL_SHA"

  echo ""
  echo "--- strip upstream .git (make vendor tree a plain source dir) ---"
  rm -rf "$VENDOR_DIR/.git"

  echo ""
  echo "--- apply DiscriminatedUnionMixin patch (ADR-0034) ---"
  cd "$VENDOR_DIR"
  # Use plain patch(1) rather than git apply — vendor tree is not a git repo.
  patch -p1 --dry-run < "$PATCH_FILE"
  patch -p1 < "$PATCH_FILE"
  cd "$REPO_ROOT"

  echo ""
  echo "--- verify patch applied ---"
  if ! grep -q "^class LLM(DiscriminatedUnionMixin, RetryMixin, NonNativeToolCallingMixin):" \
       "$VENDOR_DIR/openhands-sdk/openhands/sdk/llm/llm.py"; then
    echo "FAIL: LLM class line not patched" >&2
    exit 1
  fi
  if ! grep -q "^from openhands.sdk.utils.models import DiscriminatedUnionMixin$" \
       "$VENDOR_DIR/openhands-sdk/openhands/sdk/llm/llm.py"; then
    echo "FAIL: DiscriminatedUnionMixin import not present" >&2
    exit 1
  fi
  if ! grep -q "ADR-0034 override of" \
       "$VENDOR_DIR/openhands-sdk/openhands/sdk/llm/llm.py"; then
    echo "FAIL: _validate_subtype override not present" >&2
    exit 1
  fi
  echo "OK: patch applied (all 3 anchors verified)"

  echo ""
  echo "--- apply ADR-0037 StuckDetector near-identical patch ---"
  PATCH_SCRIPT_0037="$REPO_ROOT/scripts/apply-stuckdetector-patch.py"
  if [ ! -x "$PATCH_SCRIPT_0037" ]; then
    echo "FAIL: ADR-0037 patch script missing or not executable at $PATCH_SCRIPT_0037" >&2
    exit 1
  fi
  "$VENV_PY" "$PATCH_SCRIPT_0037" "$VENDOR_DIR"

  echo ""
  echo "--- verify ADR-0037 patch applied (sentinels) ---"
  if ! grep -q "# ADR-0037: near-identical repetition (Phase 9 Loop Guard)" \
       "$VENDOR_DIR/openhands-sdk/openhands/sdk/conversation/types.py"; then
    echo "FAIL: ADR-0037 types.py sentinel missing" >&2
    exit 1
  fi
  if ! grep -q "near_identical: int = Field" \
       "$VENDOR_DIR/openhands-sdk/openhands/sdk/conversation/types.py"; then
    echo "FAIL: ADR-0037 near_identical field missing" >&2
    exit 1
  fi
  if ! grep -q "# scenario 6 (ADR-0037): near-identical repetition" \
       "$VENDOR_DIR/openhands-sdk/openhands/sdk/conversation/stuck_detector.py"; then
    echo "FAIL: ADR-0037 stuck_detector.py scenario-6 sentinel missing" >&2
    exit 1
  fi
  if ! grep -q "_is_stuck_near_identical" \
       "$VENDOR_DIR/openhands-sdk/openhands/sdk/conversation/stuck_detector.py"; then
    echo "FAIL: ADR-0037 _is_stuck_near_identical method missing" >&2
    exit 1
  fi
  echo "OK: ADR-0037 patch applied (all 4 sentinels verified)"

  echo ""
  echo "--- uninstall pip-installed openhands-sdk (avoid version conflict) ---"
  $VENV_PIP uninstall -y openhands-sdk || true

  echo ""
  echo "--- pip install -e vendor/openhands-sdk/openhands-sdk ---"
  $VENV_PIP install -e "$VENDOR_DIR/openhands-sdk"

  echo ""
  echo "--- verify install: openhands.sdk.__file__ points at vendor tree ---"
  $VENV_PY -c "
import openhands.sdk
p = openhands.sdk.__file__
assert '/vendor/openhands-sdk/' in p, f'expected vendor path in __file__, got: {p}'
print('openhands.sdk.__file__:', p)
"

  echo ""
  echo "--- verify LLM MRO includes DiscriminatedUnionMixin ---"
  $VENV_PY -c "
from openhands.sdk.llm.llm import LLM
from openhands.sdk.utils.models import DiscriminatedUnionMixin
assert DiscriminatedUnionMixin in LLM.__mro__, f'DiscriminatedUnionMixin not in LLM MRO: {LLM.__mro__}'
print('LLM MRO:', [c.__name__ for c in LLM.__mro__])
print('OK: LLM inherits DiscriminatedUnionMixin')
"

  # Record actuals for verification / audit trail
  mkdir -p bench/results
  METADATA_FILE="bench/results/vendor-oh-sdk-$(date -u +%Y%m%dT%H%M%SZ).json"
  cat > "$METADATA_FILE" <<JSON
{
  "phase": "3.j,9",
  "component": "openhands-sdk (vendored)",
  "adrs": ["ADR-0034", "ADR-0037"],
  "vendored_at_utc": "$(date -u -Iseconds)",
  "upstream_url": "$UPSTREAM_URL",
  "pin_tag": "$PIN_TAG",
  "pin_sha": "$PIN_SHA",
  "patches": [
    "patches/openhands-sdk-llm-discriminated-union.patch",
    "scripts/apply-stuckdetector-patch.py"
  ],
  "vendor_dir": "vendor/openhands-sdk",
  "install_mode": "pip install -e"
}
JSON
  echo ""
  echo "recorded metadata: $METADATA_FILE"

  echo ""
  echo "===== vendor-openhands-sdk done — $(date -Iseconds) ====="
} 2>&1 | tee "$LOG"
