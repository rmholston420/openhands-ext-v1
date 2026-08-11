#!/usr/bin/env bash
# bench/smoke-phase-3-row-2/run.sh — Phase 3 row-2: planner routing via metadata (Path A).
#
# Prereqs:
#   1. scripts/serve-coder.sh running (port 8100).
#   2. scripts/serve-planner.sh running (port 8082).
#   3. .venv/ available at repo root.
#
# Exercises CoderPlannerRouter.completion() directly with an
# LLMCallContext(metadata={"role":"planner"}) and verifies:
#   - select_llm returns "planner"
#   - active_llm after completion is the planner LLM (base_url :8082)
#   - response is non-empty text
#   - wall time < 30s

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/.forge-oh/bench_smoke_phase_3_row_2/${TS}_run"
mkdir -p "$OUT_DIR"

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv missing at $REPO_ROOT/.venv" >&2
  exit 1
fi

# Prereq: planner endpoint reachable (REQUIRED — row-2 issues real completions to :8082)
if ! curl -sf -o /dev/null "http://127.0.0.1:8082/v1/models"; then
  echo "FAIL: planner endpoint not reachable at 127.0.0.1:8082 — start scripts/serve-planner.sh first" >&2
  exit 1
fi

# Coder endpoint is OPTIONAL for row-2 (ADR-0017 amend: coder XOR planner+embedder).
# We build the coder LLM object to test select_llm's default routing, but we never
# make an HTTP call to :8100. This lets row-2 run while the planner is resident.
CODER_UP=0
if curl -sf -o /dev/null "http://127.0.0.1:8100/v1/models"; then
  CODER_UP=1
  echo "note: coder endpoint is also up — XOR violation, but row-2 only calls planner endpoint"
fi

echo "=== Phase 3 row-2 smoke (planner routing) — $(date -Iseconds) ==="
echo "Output dir: $OUT_DIR"

"$VENV_PY" - <<'PY' 2>&1 | tee "$OUT_DIR/log.txt"
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from config.agent import (
    build_coder_llm,
    build_planner_llm,
    build_router,
    _load_max_output_tokens,
)
from config.router import CoderPlannerRouter
from openhands.sdk.llm.message import Message, TextContent

# Extract the verbatim prompt (same pattern as row-1)
_task_full = Path("bench/smoke-phase-3-row-2/task.md").read_text()
_prompt_marker = "## Prompt (verbatim, hand off to router)"
_end_marker = "## Pass criteria"
_start = _task_full.index(_prompt_marker) + len(_prompt_marker)
_end = _task_full.index(_end_marker)
PROMPT = _task_full[_start:_end].strip().lstrip("> ").strip()

# Build router directly (factories require measured max_output_tokens per ADR-0033)
mot = _load_max_output_tokens()
coder = build_coder_llm(mot["coder"])
planner = build_planner_llm(mot["planner"])
router = build_router(coder=coder, planner=planner)

# Path B (ADR-0033 amend #5): route via [role:planner] marker in user content.
# PROMPT extracted from task.md already contains the marker.
messages_marker = [Message(role="user", content=[TextContent(text=PROMPT)])]
messages_control = [
    Message(
        role="user",
        content=[TextContent(text="Write a hello world function in Python.")],
    )
]

# Sanity: routing decisions alone (no network)
selected_marker = router.select_llm(messages_marker, None)
print(f"select_llm(marker)   → {selected_marker!r}")

selected_control = router.select_llm(messages_control, None)
print(f"select_llm(control)  → {selected_control!r}")

# Real completion with the marker payload
t0 = time.time()
try:
    response = router.completion(messages=messages_marker)
    err = None
except Exception as e:
    response = None
    err = f"{type(e).__name__}: {e}"
wall = time.time() - t0

# Inspect what actually happened
active_url = getattr(router.active_llm, "base_url", None) if router.active_llm else None
planner_url = planner.base_url
coder_url = coder.base_url
routed_to_planner = (active_url == planner_url)

# Extract response text
response_text = ""
if response is not None:
    # LLMResponse.message.content is list[TextContent]
    msg = getattr(response, "message", None)
    if msg is not None:
        content = getattr(msg, "content", None)
        if isinstance(content, list):
            for block in content:
                response_text += str(getattr(block, "text", "") or "")

verdict = {
    "wall_seconds": round(wall, 2),
    "select_llm_marker": selected_marker,
    "select_llm_control": selected_control,
    "planner_base_url": planner_url,
    "coder_base_url": coder_url,
    "active_llm_base_url_after_completion": active_url,
    "routed_to_planner": routed_to_planner,
    "response_length_chars": len(response_text),
    "response_head": response_text[:200],
    "error": err,
    "under_30s": wall < 30,
    "pass": all([
        selected_marker == "planner",
        selected_control == "coder",
        routed_to_planner,
        err is None,
        len(response_text) > 0,
        wall < 30,
    ]),
}
Path("bench/smoke-phase-3-row-2/last_verdict.json").write_text(json.dumps(verdict, indent=2))
print(json.dumps(verdict, indent=2))
PY

cp "$REPO_ROOT/bench/smoke-phase-3-row-2/last_verdict.json" "$OUT_DIR/verdict.json"
echo "=== Row-2 smoke complete — verdict at $OUT_DIR/verdict.json ==="
