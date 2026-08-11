#!/usr/bin/env python3
"""Recompute verdict.json for the latest 3.g planner smoke run.

Uses only fields already saved in verdict.json (tool_calls, parsed_args,
wall_seconds, error). Cheap for iterating on the predicate without
re-running the LLM call."""
import json
import sys
from pathlib import Path

runs = sorted(
    (Path.home() / ".forge-oh/bench_smoke_phase_3_item_3g_planner").glob("*_run")
)
if not runs:
    sys.exit("no runs found")
run = runs[-1]
verdict = json.loads((run / "verdict.json").read_text())

tool_calls_seen = verdict.get("tool_calls", [])
parsed_args_seen = verdict.get("parsed_args", [])
err = verdict.get("error")
wall = verdict.get("wall_seconds", 999)

has_toolcall = len(tool_calls_seen) > 0
tool_names_seen = sorted({tc.get("name") for tc in tool_calls_seen if tc.get("name")})
has_command_arg = any(
    isinstance(a, dict)
    and "command" in a
    and "hello-planner-3g" in str(a.get("command", ""))
    for a in parsed_args_seen
)

verdict["has_toolcall"] = has_toolcall
verdict["tool_names_seen"] = tool_names_seen
verdict["has_command_hello_planner_3g"] = has_command_arg
# Backfill/remove legacy field for clarity
verdict.pop("has_terminal_call", None)
verdict["pass"] = bool(
    err is None and has_toolcall and has_command_arg and wall < 60
)

(run / "verdict.json").write_text(json.dumps(verdict, indent=2, default=str))
print(json.dumps(verdict, indent=2, default=str))
