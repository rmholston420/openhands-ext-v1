#!/usr/bin/env bash
# Phase 9 smoke — ADR-0037 loop-guard near-identical scenario.
# DoD: "Send 3+ identical/near-identical tool calls → loop-guard hook flags repetition."
#
# Deterministic in-process test — no LLM, no vLLM, no Docker.
# Runs the ADR-0037 contract test against the patched vendored openhands-sdk.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

VENV_PY="${VENV_PY:-$REPO_ROOT/.venv/bin/python}"
if [ ! -x "$VENV_PY" ]; then
  # fall back to .oh-venv (project convention on Colossus)
  if [ -x "$REPO_ROOT/.oh-venv/bin/python" ]; then
    VENV_PY="$REPO_ROOT/.oh-venv/bin/python"
  else
    echo "FAIL: no venv python found (.venv or .oh-venv)" >&2
    exit 1
  fi
fi

echo "=== Phase 9 smoke — ADR-0037 loop-guard near-identical ==="
echo "VENV_PY=$VENV_PY"
echo

# --- 1) sentinel check: ADR-0037 patch is applied to the installed SDK ---
echo "--- 1/3 sentinel check: ADR-0037 patch applied to installed sdk ---"
"$VENV_PY" - <<'PY'
import sys
from openhands.sdk.conversation.stuck_detector import StuckDetector
from openhands.sdk.conversation.types import StuckDetectionThresholds

# Assert patched surface exists.
t = StuckDetectionThresholds()
assert hasattr(t, "near_identical"), "FAIL: near_identical field missing on StuckDetectionThresholds"
assert t.near_identical == 3, f"FAIL: near_identical default != 3 (got {t.near_identical})"
assert hasattr(StuckDetector, "_is_stuck_near_identical"), "FAIL: _is_stuck_near_identical method missing"
assert hasattr(StuckDetector, "_adr0037_action_key"), "FAIL: _adr0037_action_key method missing"
print("OK: patched surface present (near_identical field + methods)")
PY

# --- 2) contract test suite ---
echo
echo "--- 2/3 contract test: tests/sdk_patch/test_stuckdetector_near_identical.py ---"
"$VENV_PY" -m unittest tests.sdk_patch.test_stuckdetector_near_identical -v

# --- 3) end-to-end scenario: build 3 near-identical events, run is_stuck path ---
echo
echo "--- 3/3 end-to-end: 3 near-identical ActionEvents → detector flags loop ---"
"$VENV_PY" - <<'PY'
import json, sys
from openhands.sdk.conversation.stuck_detector import StuckDetector
from openhands.sdk.conversation.types import StuckDetectionThresholds
from openhands.sdk.event import ActionEvent
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Function as LLMFunction,
)

def mk_evt(tool_name: str, arguments: str) -> ActionEvent:
    tc = ChatCompletionMessageToolCall(
        id=f"call_{tool_name}_{abs(hash(arguments)) % 10_000}",
        type="function",
        function=LLMFunction(name=tool_name, arguments=arguments),
    )
    return ActionEvent.model_construct(
        source="agent",
        tool_name=tool_name,
        tool_call=tc,
        action=None,
        thought=[],
        tool_call_id=tc.id,
    )

# 3 near-identical: same tool, args differ only in whitespace/case/key-order.
events = [
    mk_evt("edit_file", '{"path":"a.py","content":"hello"}'),
    mk_evt("edit_file", '{"path": "a.py",  "content": "hello"}'),
    mk_evt("EDIT_FILE", '{"content":"HELLO","path":"a.py"}'),
]

# Build a detector without a real ConversationState (ADR-0037 code path
# doesn't touch self.state).
det = StuckDetector.__new__(StuckDetector)
det.state = None
det.thresholds = StuckDetectionThresholds()

if not det._is_stuck_near_identical(events):
    print("FAIL: 3 near-identical ActionEvents were NOT flagged", file=sys.stderr)
    sys.exit(1)

# Negative control: 2 calls should NOT trip.
if det._is_stuck_near_identical(events[:2]):
    print("FAIL: 2 events tripped (below threshold=3)", file=sys.stderr)
    sys.exit(1)

# Negative control: 3 different-content calls should NOT trip.
different = [
    mk_evt("edit_file", '{"path":"a.py","content":"1"}'),
    mk_evt("edit_file", '{"path":"a.py","content":"2"}'),
    mk_evt("edit_file", '{"path":"a.py","content":"3"}'),
]
if det._is_stuck_near_identical(different):
    print("FAIL: 3 different-content calls tripped (false positive)", file=sys.stderr)
    sys.exit(1)

print("OK: 3 near-identical calls flagged; below-threshold + different-content did not.")
PY

echo
echo "============================================================"
echo "OK Phase 9 smoke PASSED (ADR-0037)"
echo "============================================================"
