#!/usr/bin/env python3
"""Recompute verdict.json from events.json for the latest 3.c run.

Use when only verdict predicates changed and the events themselves are
still valid (no reason to burn another 51s on a passing conversation)."""
import json, sys
from pathlib import Path

runs = sorted((Path.home()/".forge-oh/bench_smoke_phase_3_item_3c").glob("*_run"))
if not runs:
    sys.exit("no runs found")
run = runs[-1]
events = json.loads((run/"events.json").read_text())
verdict = json.loads((run/"verdict.json").read_text())

def evt_text(e): return json.dumps(e["data"], default=str)[:8000]
def any_event(pred): return any(pred(e) for e in events)

verdict["has_finish_action"] = any_event(
    lambda e: e["cls"] == "ActionEvent" and "Finish" in evt_text(e)
)
verdict["has_docker_ok_string"] = any_event(lambda e: "docker-ok" in evt_text(e))
verdict["has_hello_txt"]        = any_event(lambda e: "hello.txt" in evt_text(e))
verdict["has_terminal_error"]   = any_event(lambda e: e["cls"] == "ConversationErrorEvent")

verdict["pass"] = (
    verdict.get("exception") is None
    and verdict.get("workspace_is_remote", False)
    and verdict["event_count"] > 0
    and verdict["has_finish_action"]
    and (verdict["has_docker_ok_string"] or verdict["has_hello_txt"])
    and not verdict["has_terminal_error"]
    and verdict.get("wall_seconds", 999) < 300
)

(run/"verdict.json").write_text(json.dumps(verdict, indent=2, default=str))
print(json.dumps(verdict, indent=2, default=str))
