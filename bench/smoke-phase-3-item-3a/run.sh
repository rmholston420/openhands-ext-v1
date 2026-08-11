#!/usr/bin/env bash
# bench/smoke-phase-3-item-3a/run.sh — Phase 3 sign-off item 3.a:
# code-explorer subagent registration smoke (offline, no HTTP).
#
# ADR-0032 DoD: "register code-explorer in the runtime tool registry
# alongside the router table; verify with a read-only investigation smoke test."
# This smoke covers the REGISTRATION half; a live delegation smoke is deferred
# to sign-off item 3.h (DockerWorkspace + DelegateTool handoff).

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/.forge-oh/bench_smoke_phase_3_item_3a/${TS}_run"
mkdir -p "$OUT_DIR"

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv missing at $REPO_ROOT/.venv" >&2
  exit 1
fi

echo "=== Phase 3 sign-off item 3.a smoke — $(date -Iseconds) ==="
echo "Output dir: $OUT_DIR"

"$VENV_PY" - <<'PY' 2>&1 | tee "$OUT_DIR/log.txt"
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

t0 = time.time()

from config.agent import build_agent
from openhands.tools.task import TaskToolSet

# Build the agent — this must side-effect register the code-explorer subagent
err = None
try:
    agent = build_agent()
except Exception as e:
    agent = None
    err = f"{type(e).__name__}: {e}"

# Query the SDK's agent registry via the public accessor (SDK 1.41).
registered_names = []
registry_dump = {}
registry_error = None
if agent is not None:
    try:
        from openhands.sdk.subagent import get_registered_agent_definitions

        defs = get_registered_agent_definitions()
        if isinstance(defs, dict):
            items = defs.items()
        else:
            items = [(getattr(d, "name", str(d)), d) for d in defs]
        for name, defn in items:
            registered_names.append(name)
            registry_dump[name] = {
                "level": getattr(defn, "level", None),
                "tools": list(getattr(defn, "tools", []) or []),
                "source": str(getattr(defn, "source", "") or ""),
            }
    except Exception as e:
        registry_error = f"{type(e).__name__}: {e}"

# Pull the code-explorer definition through the public discovery path too,
# so we can assert its tools list matches the shipped preset regardless of
# which private registry accessor exists.
code_explorer_tools = None
code_explorer_level = None
try:
    from openhands.tools.preset.default import discover_builtin_agents
    for defn in discover_builtin_agents(enable_browser=False):
        if getattr(defn, "name", "") == "code-explorer":
            code_explorer_tools = list(getattr(defn, "tools", []) or [])
            code_explorer_level = getattr(defn, "level", None)
            break
except Exception as e:
    code_explorer_level = f"discover_error: {type(e).__name__}: {e}"

# Verify TaskToolSet is in the agent's tool list
agent_tool_names = []
task_tool_present = False
if agent is not None:
    for t in getattr(agent, "tools", []) or []:
        n = getattr(t, "name", None) or getattr(t, "id", None) or str(t)
        agent_tool_names.append(n)
    task_tool_present = TaskToolSet.name in agent_tool_names

wall = time.time() - t0

code_explorer_registry_entry = registry_dump.get("code-explorer")

verdict = {
    "wall_seconds": round(wall, 2),
    "build_agent_ok": agent is not None,
    "build_agent_error": err,
    "registry_error": registry_error,
    "code_explorer_in_registry": "code-explorer" in registered_names,
    "code_explorer_registry_entry": code_explorer_registry_entry,
    "code_explorer_registry_tools_match_expected": (
        (code_explorer_registry_entry or {}).get("tools") == ["terminal"]
    ),
    "registered_agent_names": registered_names,
    "code_explorer_tools_from_preset": code_explorer_tools,
    "code_explorer_tools_match_expected": code_explorer_tools == ["terminal"],
    "code_explorer_level": code_explorer_level,
    "agent_tool_names": agent_tool_names,
    "task_tool_set_name": TaskToolSet.name,
    "task_tool_present_in_agent": task_tool_present,
    "under_10s": wall < 10,
    "pass": all([
        agent is not None,
        err is None,
        registry_error is None,
        "code-explorer" in registered_names,
        (code_explorer_registry_entry or {}).get("tools") == ["terminal"],
        code_explorer_tools == ["terminal"],
        task_tool_present,
        wall < 10,
    ]),
}
Path("bench/smoke-phase-3-item-3a/last_verdict.json").write_text(json.dumps(verdict, indent=2))
print(json.dumps(verdict, indent=2))
PY

cp "$REPO_ROOT/bench/smoke-phase-3-item-3a/last_verdict.json" "$OUT_DIR/verdict.json"
echo "=== Item 3.a smoke complete — verdict at $OUT_DIR/verdict.json ==="
