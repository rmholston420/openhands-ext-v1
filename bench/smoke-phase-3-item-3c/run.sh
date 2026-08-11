#!/usr/bin/env bash
# bench/smoke-phase-3-item-3c/run.sh — Phase 3 sign-off item 3.c smoke.
#
# Trivial task under DockerWorkspace instead of LocalWorkspace. Uses
# the coder LLM at http://127.0.0.1:8100/v1 via network=host so the
# agent-server container reaches it unchanged.

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/.forge-oh/bench_smoke_phase_3_item_3c/${TS}_run"
mkdir -p "$OUT_DIR"

VENV_PY="$REPO_ROOT/.venv/bin/python"

# Preflight: coder up on :8100
if ! curl -sf http://127.0.0.1:8100/v1/models >/dev/null 2>&1; then
  echo "PRECONDITION FAIL: coder :8100 not reachable. Start it with"
  echo "  nohup bash scripts/serve-coder.sh > /tmp/oh-serve/coder.log 2>&1 &"
  echo "and retry." >&2
  exit 2
fi

# Preflight: Docker
if ! docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
  echo "PRECONDITION FAIL: Docker daemon not reachable." >&2
  exit 2
fi

# Preflight: :8000 free (SDK bug workaround requires host_port=8000 when
# network='host'; see BUILD_LOG 2026-08-11 18:38 EDT). Also clean up any
# stale agent-server container from a prior failed run.
STALE_CIDS=$(docker ps -a --filter 'ancestor=ghcr.io/openhands/agent-server:latest-python' --format '{{.ID}}' 2>/dev/null)
if [ -n "$STALE_CIDS" ]; then
  echo "Removing stale agent-server container(s): $STALE_CIDS"
  echo "$STALE_CIDS" | xargs -r docker rm -f >/dev/null
fi
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE '(^|:)8000$'; then
  echo "PRECONDITION FAIL: host port 8000 is bound by something else." >&2
  ss -ltnp 2>/dev/null | grep ':8000' >&2
  exit 2
fi

TASK_FILE="$REPO_ROOT/bench/smoke-phase-3-item-3c/task.md"
IMAGE="ghcr.io/openhands/agent-server:latest-python"

echo "=== Phase 3 sign-off item 3.c smoke — $(date -Iseconds) ==="
echo "OUT_DIR=$OUT_DIR"
echo "IMAGE=$IMAGE"
echo ""

env \
  OUT_DIR="$OUT_DIR" \
  IMAGE="$IMAGE" \
  TASK_FILE="$TASK_FILE" \
  "$VENV_PY" - <<'PY'
import json, os, time, traceback
from pathlib import Path
from datetime import datetime, timezone

OUT_DIR = Path(os.environ["OUT_DIR"])
IMAGE   = os.environ["IMAGE"]
TASK    = Path(os.environ["TASK_FILE"]).read_text()

from config.agent import build_agent, build_coder_llm, _load_max_output_tokens
from openhands.sdk import Conversation, Message, TextContent
from openhands.workspace.docker.workspace import DockerWorkspace
from openhands.sdk.workspace import RemoteWorkspace

# ---- Router bypass for 3.c ----
# CoderPlannerRouter (a RouterLLM subclass) does NOT include
# `llms_for_routing` in its Pydantic serialization surface. Under
# LocalConversation the router dispatches in-process to the coder LLM
# and everything works. Under RemoteConversation the agent is dumped
# to JSON and rebuilt inside the DockerWorkspace container; the child
# LLMs are lost and the placeholder `model=openai/coder-planner-router,
# base_url=null` gets called — which litellm sends to api.openai.com,
# producing 'Incorrect API key provided: <placeholder>'. Bypass the
# router for this smoke: it exists to verify the DockerWorkspace
# mechanism, not the router. RouterLLM-under-RemoteConversation is
# tracked as a separate sign-off item (Phase 3.j to be opened).
agent = build_agent()
mot = _load_max_output_tokens()
agent.llm = build_coder_llm(mot["coder"])

# Collect events
events = []
def on_event(ev):
    try:
        d = ev.model_dump(mode="json")
    except Exception:
        d = {"repr": repr(ev)}
    events.append({"cls": type(ev).__name__, "data": d})

verdict = {
    "task": "3c_dockerworkspace_trivial",
    "image": IMAGE,
    "started_utc": datetime.now(timezone.utc).isoformat(),
}

t0 = time.time()
err = None
try:
    # NOTE: with network='host', Docker ignores -p mappings and the
    # container binds :8000 on the host directly. The SDK's health check
    # polls http://127.0.0.1:{host_port}/health, so we must pin
    # host_port=8000 to match the server's actual bind port.
    with DockerWorkspace(
        server_image=IMAGE,
        network="host",
        host_port=8000,
        enable_gpu=False,
        health_check_timeout=180.0,
    ) as ws:
        verdict["workspace_cls"] = type(ws).__name__
        verdict["workspace_is_remote"] = isinstance(ws, RemoteWorkspace)
        verdict["workspace_host"] = getattr(ws, "host", None)

        conv = Conversation(agent=agent, workspace=ws, callbacks=[on_event])
        conv.send_message(Message(role="user",
                                  content=[TextContent(text=TASK)]))
        conv.run()

        # Post-run state
        try:
            st_ws = conv.state.workspace
            verdict["state_workspace_cls"] = type(st_ws).__name__
        except Exception as e:
            verdict["state_workspace_cls_err"] = f"{type(e).__name__}: {e}"

except Exception as e:
    err = f"{type(e).__name__}: {e}"
    verdict["exception"] = err
    verdict["traceback"] = traceback.format_exc()

wall = time.time() - t0
verdict["wall_seconds"] = round(wall, 2)
verdict["event_count"]  = len(events)

# Type counts
tc = {}
for e in events:
    tc[e["cls"]] = tc.get(e["cls"], 0) + 1
verdict["type_counts"] = tc

def any_event(pred):
    return any(pred(e) for e in events)

def action_names():
    names = []
    for e in events:
        if "Action" in e["cls"]:
            d = e["data"]
            # ActionEvent.action.name or .tool_name; be liberal
            for path in (("action","name"), ("action","tool_name"),
                         ("tool_name",), ("name",)):
                cur = d
                ok = True
                for k in path:
                    if isinstance(cur, dict) and k in cur:
                        cur = cur[k]
                    else:
                        ok = False; break
                if ok and isinstance(cur, str):
                    names.append(cur); break
    return names

verdict["action_names"] = action_names()

def evt_text(e):
    return json.dumps(e["data"], default=str)[:8000]

verdict["has_finish_action"] = any_event(
    lambda e: e["cls"] == "ActionEvent" and "Finish" in evt_text(e)
)
verdict["has_docker_ok_string"] = any_event(
    lambda e: "docker-ok" in evt_text(e)
)
verdict["has_hello_txt"] = any_event(
    lambda e: "hello.txt" in evt_text(e)
)
verdict["has_terminal_error"] = any_event(
    lambda e: "terminal_error" in evt_text(e).lower()
             or ("Observation" in e["cls"] and "error" in evt_text(e).lower())
)

verdict["pass"] = (
    err is None
    and verdict.get("workspace_is_remote", False)
    and verdict["event_count"] > 0
    and verdict["has_finish_action"]
    and (verdict["has_docker_ok_string"] or verdict["has_hello_txt"])
    and not verdict["has_terminal_error"]
    and wall < 300
)

(OUT_DIR / "events.json").write_text(json.dumps(events, indent=2, default=str))
(OUT_DIR / "verdict.json").write_text(json.dumps(verdict, indent=2, default=str))
print(json.dumps(verdict, indent=2, default=str))
PY

rc=$?
echo ""
echo "=== Item 3.c smoke complete — rc=$rc — verdict at $OUT_DIR/verdict.json ==="
exit $rc
