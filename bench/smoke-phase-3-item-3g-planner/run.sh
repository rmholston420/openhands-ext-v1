#!/usr/bin/env bash
# bench/smoke-phase-3-item-3g-planner/run.sh
#
# Phase 3 · Item 3.g (planner half): verify native OpenAI tool_calls
# against the planner endpoint (llama.cpp :8082 with --jinja).
#
# Direct LLM.completion(..., tools=[TerminalAction-wrapped ToolDefinition])
# — no Conversation, no router, no DockerWorkspace. Row-2 pattern.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/.forge-oh/bench_smoke_phase_3_item_3g_planner/${TS}_run"
mkdir -p "$OUT_DIR"

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv missing at $REPO_ROOT/.venv" >&2
  exit 1
fi

# REQUIRED: planner endpoint reachable
if ! curl -sf -o /dev/null "http://127.0.0.1:8082/v1/models"; then
  echo "FAIL: planner endpoint not reachable at 127.0.0.1:8082 — start scripts/serve-planner.sh first" >&2
  exit 1
fi

# ADR-0017 co-residency check: coder should NOT be up simultaneously.
if curl -sf -o /dev/null "http://127.0.0.1:8100/v1/models"; then
  echo "WARN: coder :8100 is also up — ADR-0017 XOR violation. Smoke only hits :8082 so continuing." >&2
fi

export OUT_DIR IMAGE=""  # IMAGE unused here; kept for parity with 3.c smoke shape
export TASK_FILE="$REPO_ROOT/bench/smoke-phase-3-item-3g-planner/task.md"

echo "=== Phase 3 · Item 3.g (planner) tool-calling smoke — $(date -Iseconds) ==="
echo "Output dir: $OUT_DIR"

"$VENV_PY" - <<'PY' 2>&1 | tee "$OUT_DIR/log.txt"
import json, os, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

OUT_DIR = Path(os.environ["OUT_DIR"])
TASK    = Path(os.environ["TASK_FILE"]).read_text()

# Extract the verbatim prompt from task.md
_start_marker = "## Prompt (verbatim)"
_end_marker = "## Pass criteria"
_start = TASK.index(_start_marker) + len(_start_marker)
_end = TASK.index(_end_marker)
PROMPT = TASK[_start:_end].strip().lstrip("> ").strip()

from typing import Sequence

from config.agent import build_planner_llm, _load_max_output_tokens
from openhands.sdk.llm.message import Message, TextContent
from openhands.sdk.tool import ToolDefinition
from openhands.tools.terminal import TerminalAction, TerminalObservation


# ToolDefinition is abstract (requires .create()). We only want the
# LLM-facing shape — no executor, no ConversationState, no filesystem.
# Local minimal concrete subclass:
class _LLMOnlyTerminalTool(ToolDefinition[TerminalAction, TerminalObservation]):
    @classmethod
    def create(cls) -> Sequence["_LLMOnlyTerminalTool"]:
        return [cls(
            action_type=TerminalAction,
            observation_type=TerminalObservation,
            description=(
                "Run a shell command in the workspace and return its output. "
                "Use for any shell interaction (echo, ls, cat, mkdir, etc.)."
            ),
        )]

verdict = {
    "task": "3g_planner_toolcall",
    "endpoint": "http://127.0.0.1:8082/v1",
    "model": "qwen3_6-27b-q6k-gguf",
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "prompt_first_line": PROMPT.splitlines()[0],
}

try:
    mot = _load_max_output_tokens()
    planner = build_planner_llm(mot["planner"])
    verdict["planner_base_url"] = planner.base_url
    verdict["planner_model"] = planner.model

    # Build a ToolDefinition wrapping the shipped TerminalAction schema.
    # No executor — we are only verifying that the model decides to call.
    terminal_td = _LLMOnlyTerminalTool.create()[0]
    verdict["tool_openai_json"] = json.loads(json.dumps(
        terminal_td.to_openai_tool(),
        default=str,
    ))

    messages = [Message(role="user", content=[TextContent(text=PROMPT)])]

    t0 = time.time()
    err = None
    try:
        response = planner.completion(messages=messages, tools=[terminal_td])
    except Exception as e:
        response = None
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    wall = time.time() - t0
    verdict["wall_seconds"] = round(wall, 2)
    verdict["error"] = err

    # Inspect response
    tool_calls_seen = []
    parsed_args_seen = []
    if response is not None:
        msg = getattr(response, "message", None)
        verdict["response_has_message"] = msg is not None
        if msg is not None:
            tcs = getattr(msg, "tool_calls", None) or []
            for tc in tcs:
                # Support both direct-fields and OpenAI-nested shapes
                name = (
                    getattr(tc, "name", None)
                    or getattr(getattr(tc, "function", None), "name", None)
                )
                raw_args = (
                    getattr(tc, "arguments", None)
                    or getattr(getattr(tc, "function", None), "arguments", None)
                )
                tool_calls_seen.append({"name": name, "raw_args": raw_args})
                if isinstance(raw_args, str):
                    try:
                        parsed_args_seen.append(json.loads(raw_args))
                    except Exception:
                        parsed_args_seen.append({"__parse_error__": True, "raw": raw_args[:400]})
                elif isinstance(raw_args, dict):
                    parsed_args_seen.append(raw_args)
            # Also extract text content for the log (should be empty if the model called the tool)
            content = getattr(msg, "content", None) or []
            resp_text = ""
            for block in content:
                resp_text += str(getattr(block, "text", "") or "")
            verdict["response_text_head"] = resp_text[:400]
            verdict["response_text_chars"] = len(resp_text)
    verdict["tool_calls"] = tool_calls_seen
    verdict["parsed_args"] = parsed_args_seen

    # Pass predicate.
    #
    # Note on tool-name check: SDK auto-derives the OpenAI tool name from
    # the ToolDefinition class name (snake_case). Our local subclass came
    # out as '_llm_only_terminal'. Since we only handed the model ONE tool,
    # the model "calling a tool with the right command" is sufficient
    # evidence that the endpoint speaks native tool_calls. We record the
    # name we saw for the log but do not gate on it.
    has_toolcall = len(tool_calls_seen) > 0
    tool_names_seen = sorted({tc.get("name") for tc in tool_calls_seen if tc.get("name")})
    has_command_arg = any(
        isinstance(a, dict) and "command" in a and "hello-planner-3g" in str(a.get("command", ""))
        for a in parsed_args_seen
    )
    verdict["has_toolcall"] = has_toolcall
    verdict["tool_names_seen"] = tool_names_seen
    verdict["has_command_hello_planner_3g"] = has_command_arg
    verdict["pass"] = bool(
        err is None
        and has_toolcall
        and has_command_arg
        and wall < 60
    )
except Exception as e:
    traceback.print_exc()
    verdict["exception"] = f"{type(e).__name__}: {e}"
    verdict["pass"] = False

(OUT_DIR / "verdict.json").write_text(json.dumps(verdict, indent=2, default=str))
print(json.dumps(verdict, indent=2, default=str))
PY

RC=${PIPESTATUS[0]}
echo "=== Item 3.g (planner) smoke complete — rc=$RC — verdict at $OUT_DIR/verdict.json ==="
exit $RC
