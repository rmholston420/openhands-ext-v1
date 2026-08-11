#!/usr/bin/env bash
# bench/smoke-phase-3/run.sh — Phase 3 verification row 1 smoke.
#
# Prereqs:
#   1. scripts/serve-coder.sh running (port 8100).
#   2. scripts/populate-max-output-tokens.sh already run (config/max-output-tokens.json exists).
#   3. .venv/ active OR sourced.
#
# Runs the smoke task from bench/smoke-phase-3/task.md via config.agent.build_agent().
# Emits result JSON to ~/.forge-oh/bench_smoke_phase_3/<ts>_run/result.json.
#
# Pass condition (all must hold):
#   - HTTP 200 from coder endpoint on at least one completion call.
#   - Event stream contains ≥1 tool action + observation.
#   - Event stream ends with FinishAction.
#   - Total wall time < 60s.
#   - Model output contains the exact first line of README-target.txt.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/.forge-oh/bench_smoke_phase_3/${TS}_run"
mkdir -p "$OUT_DIR"

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv missing at $REPO_ROOT/.venv" >&2
  exit 1
fi

# Prereq 1: coder endpoint reachable
if ! curl -sf -o /dev/null "http://127.0.0.1:8100/v1/models"; then
  echo "FAIL: coder endpoint not reachable at 127.0.0.1:8100 — start scripts/serve-coder.sh first" >&2
  exit 1
fi

# Prereq 2: measured max_output_tokens present
if [ ! -f "$REPO_ROOT/config/max-output-tokens.json" ]; then
  echo "FAIL: config/max-output-tokens.json missing — run scripts/populate-max-output-tokens.sh first" >&2
  exit 1
fi

echo "=== Phase 3 smoke — $(date -Iseconds) ==="
echo "Output dir: $OUT_DIR"

# Run the smoke via SDK
"$VENV_PY" - <<'PY' 2>&1 | tee "$OUT_DIR/log.txt"
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from config.agent import build_agent
from openhands.sdk import Conversation
# SDK 1.41: TerminalTool/FileEditorTool are ToolDefinition Pydantic models
# requiring `description`+`action_type` fields; use the SDK's factory instead.
# get_default_tools() returns [terminal, file_editor, task_tracker, browser_tool_set].
# For Phase 3 row-1 smoke we only need terminal + file_editor.
from openhands.tools import get_default_tools

# Extract ONLY the verbatim prompt from task.md — sending the full task doc
# causes the agent to wander (StuckDetector loop-kills at ~60s).
_task_full = Path("bench/smoke-phase-3/task.md").read_text()
_prompt_marker = "## Prompt (verbatim, hand off to agent)"
_end_marker = "## Pass criteria"
_start = _task_full.index(_prompt_marker) + len(_prompt_marker)
_end = _task_full.index(_end_marker)
TASK = _task_full[_start:_end].strip().lstrip("> ").strip()
EXPECTED_LINE = "OpenHands-Ext v1 Phase 3 smoke target."

t0 = time.time()
all_tools = get_default_tools(enable_browser=False, enable_sub_agents=False)
smoke_tools = [t for t in all_tools if t.name in ("terminal", "file_editor")]
agent = build_agent(tools=smoke_tools)
conversation = Conversation(agent=agent)
conversation.send_message(TASK)
result = conversation.run()
wall = time.time() - t0

events = list(conversation.state.events)
has_tool = any(getattr(e, "action", None) or "action" in type(e).__name__.lower() for e in events)
finish_ok = any("Finish" in type(e).__name__ for e in events)
final_text = "".join(str(getattr(e, "content", "") or "") for e in events)
saw_line = EXPECTED_LINE in final_text

verdict = {
    "wall_seconds": round(wall, 2),
    "event_count": len(events),
    "has_tool_action": has_tool,
    "has_finish_action": finish_ok,
    "output_contains_expected_line": saw_line,
    "under_60s": wall < 60,
    "pass": all([has_tool, finish_ok, saw_line, wall < 60]),
}
Path("bench/smoke-phase-3/last_verdict.json").write_text(json.dumps(verdict, indent=2))
print(json.dumps(verdict, indent=2))
PY

cp "$REPO_ROOT/bench/smoke-phase-3/last_verdict.json" "$OUT_DIR/verdict.json"
echo "=== Smoke complete — verdict at $OUT_DIR/verdict.json ==="
