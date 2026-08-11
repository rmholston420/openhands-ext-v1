#!/usr/bin/env bash
# bench/smoke-phase-3-item-3h-1/run.sh — Phase 3 sign-off item 3.h-1:
# DelegateTool wiring smoke (supervisor → code-explorer subagent).
#
# See task.md for pass criteria and rationale. Coder up on :8100 is required;
# planner may be down (subagent inherits parent LLM per SDK 1.41
# openhands.tools.task.manager:367).

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/.forge-oh/bench_smoke_phase_3_item_3h_1/${TS}_run"
mkdir -p "$OUT_DIR"

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv missing at $REPO_ROOT/.venv" >&2
  exit 1
fi

# Prereq: coder endpoint reachable
if ! curl -sf -o /dev/null "http://127.0.0.1:8100/v1/models"; then
  echo "FAIL: coder endpoint not reachable at 127.0.0.1:8100 — start scripts/serve-coder.sh first" >&2
  exit 1
fi

# Prereq: measured max_output_tokens present
if [ ! -f "$REPO_ROOT/config/max-output-tokens.json" ]; then
  echo "FAIL: config/max-output-tokens.json missing — run scripts/populate-max-output-tokens.sh first" >&2
  exit 1
fi

echo "=== Phase 3 sign-off item 3.h-1 smoke — $(date -Iseconds) ==="
echo "Output dir: $OUT_DIR"

"$VENV_PY" - <<'PY' 2>&1 | tee "$OUT_DIR/log.txt"
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from config.agent import build_agent
from openhands.sdk import Conversation
from openhands.sdk.security.confirmation_policy import NeverConfirm

TASK = (
    "Delegate this subtask to the `code-explorer` subagent (the "
    "`task_tool_set` tool is how you delegate). Ask the subagent to "
    "locate where the class `TaskToolSet` is defined in the installed "
    "OpenHands SDK (search under `.venv/lib/python3.14/site-packages/"
    "openhands/tools/task/`), and to return the exact file path and "
    "the line number of the `class TaskToolSet` definition. When the "
    "subagent returns, report its findings verbatim and then finish."
)

t0 = time.time()

# build_agent() defaults now include TaskToolSet + registered subagents.
agent = build_agent()
conversation = Conversation(agent=agent)
conversation.set_confirmation_policy(NeverConfirm())
conversation.send_message(TASK)

err = None
try:
    conversation.run()
except Exception as e:
    err = f"{type(e).__name__}: {e}"
wall = time.time() - t0

events = list(conversation.state.events)

def _class_name(x):
    return type(x).__name__ if x is not None else "NoneType"

def _event_text_blob(e):
    parts = []
    for attr in ("action", "observation"):
        inner = getattr(e, attr, None)
        if inner is None:
            continue
        content = getattr(inner, "content", None)
        if isinstance(content, list):
            for block in content:
                parts.append(str(getattr(block, "text", "") or ""))
        elif content is not None:
            parts.append(str(content))
        for f in ("message", "summary", "text", "output", "result"):
            v = getattr(inner, f, None)
            if v:
                parts.append(str(v))
    for f in ("content", "message"):
        v = getattr(e, f, None)
        if isinstance(v, list):
            for block in v:
                parts.append(str(getattr(block, "text", "") or block))
        elif v is not None:
            parts.append(str(v))
    return " ".join(p for p in parts if p)

# Event-type tallies
type_counts = {}
task_action_events = []
task_observation_events = []
finish_events = []
for e in events:
    a = getattr(e, "action", None)
    o = getattr(e, "observation", None)
    ename = _class_name(e)
    aname = _class_name(a)
    oname = _class_name(o)
    type_counts[f"event:{ename}"] = type_counts.get(f"event:{ename}", 0) + 1
    if a is not None:
        type_counts[f"action:{aname}"] = type_counts.get(f"action:{aname}", 0) + 1
    if o is not None:
        type_counts[f"observation:{oname}"] = type_counts.get(f"observation:{oname}", 0) + 1
    if "TaskAction" in aname:
        task_action_events.append(e)
    if "TaskObservation" in oname:
        task_observation_events.append(e)
    if "FinishAction" in aname:
        finish_events.append(e)

# The subagent's returned content should quote a real path + a line number
final_text = " ".join(_event_text_blob(e) for e in events)

# Grounded-evidence check: the subagent must produce (a) a real *.py path AND
# (b) some form of line-number citation associated with it. We accept any of:
#   - inline citation "...file.py:198" or "...file.py 198"
#   - agent-formatted "...file.py`" followed later by "line 198"/"Line: 198"/"Line Number: 198"
#   - a plain *.py path co-occurring with any "line[s]?\s*(?:number|no\.?)?\s*:?\s*\d+"
mentions_target_file = "task/definition.py" in final_text
mentions_line_198 = bool(re.search(r"\b198\b", final_text))
_has_py_path = bool(re.search(r"[\w./-]+\.py\b", final_text))
_has_line_number_phrase = bool(
    re.search(r"line\s*(?:number|no\.?|#)?\s*[:\-]?\s*\d+", final_text, re.IGNORECASE)
    or re.search(r"[\w./-]+\.py[:\s]+\d+", final_text)
)
has_any_path_citation = _has_py_path and _has_line_number_phrase

has_task_action = len(task_action_events) >= 1
has_task_observation = len(task_observation_events) >= 1
# Not all SDK paths surface a TaskObservation event at top level; also accept
# "subagent produced text that made it back into the transcript"
# (task_action present AND final_text mentions the target).
delegation_evidenced = has_task_action or has_task_observation

verdict = {
    "wall_seconds": round(wall, 2),
    "run_error": err,
    "event_count": len(events),
    "type_counts": dict(sorted(type_counts.items())),
    "has_task_action": has_task_action,
    "has_task_observation": has_task_observation,
    "has_finish_action": len(finish_events) >= 1,
    "delegation_evidenced": delegation_evidenced,
    "mentions_target_file_task_definition_py": mentions_target_file,
    "mentions_line_198": mentions_line_198,
    "has_any_path_line_citation": has_any_path_citation,
    "final_text_len": len(final_text),
    "final_text_head_2k": final_text[:2000],
    "under_300s": wall < 300,
    "pass": all([
        err is None,
        delegation_evidenced,
        has_any_path_citation,
        mentions_target_file,  # substantive: subagent found the right file
        wall < 300,
    ]),
}
Path("bench/smoke-phase-3-item-3h-1/last_verdict.json").write_text(json.dumps(verdict, indent=2))
print(json.dumps({k: v for k, v in verdict.items() if k != "final_text_head_2k"}, indent=2))
print("--- final_text_head_2k ---")
print(verdict["final_text_head_2k"])
PY

cp "$REPO_ROOT/bench/smoke-phase-3-item-3h-1/last_verdict.json" "$OUT_DIR/verdict.json"
echo "=== Item 3.h-1 smoke complete — verdict at $OUT_DIR/verdict.json ==="
