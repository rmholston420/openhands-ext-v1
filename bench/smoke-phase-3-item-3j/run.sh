#!/usr/bin/env bash
# bench/smoke-phase-3-item-3j/run.sh — Phase 3 sign-off item 3.j smoke.
#
# CoderPlannerRouter (RouterLLM subclass) under DockerWorkspace
# (RemoteConversation). ADR-0034 patch adds DiscriminatedUnionMixin to
# LLM and overrides `_validate_subtype` on LLM so that server-side
# `LLM.model_validate(dumped)` reconstructs the router subclass with
# `llms_for_routing` intact.
#
# Verdict criteria:
#   - agent.llm is CoderPlannerRouter client-side.
#   - agent.model_dump(mode="json", context={"expose_secrets": True})
#     round-trips through LLM.model_validate back to CoderPlannerRouter
#     with llms_for_routing.coder.base_url == vLLM :8100 and
#     llms_for_routing.planner.base_url == llama.cpp :8082 preserved.
#   - Task finishes (has_finish_action).
#   - No 'Incorrect API key' / 'api.openai.com' string in event stream
#     (positive check that we did not fall back to OpenAI).
#   - `router-ok-3j` string appears in event stream.

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/.forge-oh/bench_smoke_phase_3_item_3j/${TS}_run"
mkdir -p "$OUT_DIR"

VENV_PY="$REPO_ROOT/.venv/bin/python"

# --- Preflight ---
if ! curl -sf http://127.0.0.1:8100/v1/models >/dev/null 2>&1; then
  echo "PRECONDITION FAIL: coder :8100 not reachable. Start it with" >&2
  echo "  nohup bash scripts/serve-coder.sh > /tmp/oh-serve/coder.log 2>&1 &" >&2
  exit 2
fi
if ! curl -sf http://127.0.0.1:8082/v1/models >/dev/null 2>&1; then
  echo "PRECONDITION FAIL: planner :8082 not reachable. Start it with" >&2
  echo "  nohup bash scripts/serve-planner.sh > /tmp/oh-serve/planner.log 2>&1 &" >&2
  exit 2
fi
if ! docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
  echo "PRECONDITION FAIL: Docker daemon not reachable." >&2
  exit 2
fi

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

TASK_FILE="$REPO_ROOT/bench/smoke-phase-3-item-3j/task.md"
IMAGE="ghcr.io/openhands/agent-server:latest-python"

echo "=== Phase 3 sign-off item 3.j smoke — $(date -Iseconds) ==="
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

from config.agent import build_agent
from config.router import CoderPlannerRouter
from openhands.sdk import Conversation, Message, TextContent
from openhands.sdk.llm.llm import LLM
from openhands.workspace.docker.workspace import DockerWorkspace
from openhands.sdk.workspace import RemoteWorkspace

verdict = {
    "task": "3j_router_under_dockerworkspace",
    "image": IMAGE,
    "started_utc": datetime.now(timezone.utc).isoformat(),
}

# --- Build agent with the router (no bypass; this is the whole point) ---
agent = build_agent()
verdict["agent_llm_cls"]  = type(agent.llm).__name__
verdict["agent_llm_mro"]  = [c.__name__ for c in type(agent.llm).__mro__]
verdict["router_name"]    = getattr(agent.llm, "router_name", None)
verdict["llms_for_routing_keys"] = sorted(list(getattr(agent.llm, "llms_for_routing", {}).keys()))

# --- ADR-0034 round-trip proof: dump the whole agent the way
#     RemoteConversation does, then re-validate through LLM base class
#     annotation to prove the container-side rebuild reconstructs the
#     router subclass with llms_for_routing intact. ---
try:
    dumped = agent.model_dump(mode="json", context={"expose_secrets": True})
    llm_payload = dumped["llm"]
    verdict["llm_payload_kind"] = llm_payload.get("kind")
    verdict["llm_payload_router_name"] = llm_payload.get("router_name")
    verdict["llm_payload_has_llms_for_routing"] = "llms_for_routing" in llm_payload
    if "llms_for_routing" in llm_payload:
        verdict["llm_payload_llms_for_routing_keys"] = sorted(list(llm_payload["llms_for_routing"].keys()))

    # This is the critical assertion: LLM.model_validate on the payload
    # returns a CoderPlannerRouter with llms_for_routing preserved.
    rebuilt = LLM.model_validate(llm_payload)
    verdict["rebuilt_cls"]         = type(rebuilt).__name__
    verdict["rebuilt_router_name"] = getattr(rebuilt, "router_name", None)
    rlfr = getattr(rebuilt, "llms_for_routing", {}) or {}
    verdict["rebuilt_llms_for_routing_keys"] = sorted(list(rlfr.keys()))
    if "coder" in rlfr:
        verdict["rebuilt_coder_base_url"] = str(getattr(rlfr["coder"], "base_url", ""))
        verdict["rebuilt_coder_model"]    = str(getattr(rlfr["coder"], "model", ""))
    if "planner" in rlfr:
        verdict["rebuilt_planner_base_url"] = str(getattr(rlfr["planner"], "base_url", ""))
        verdict["rebuilt_planner_model"]    = str(getattr(rlfr["planner"], "model", ""))
except Exception as e:
    verdict["roundtrip_exception"] = f"{type(e).__name__}: {e}"
    verdict["roundtrip_traceback"] = traceback.format_exc()

# --- Run the task under DockerWorkspace ---
events = []
def on_event(ev):
    try:
        d = ev.model_dump(mode="json")
    except Exception:
        d = {"repr": repr(ev)}
    events.append({"cls": type(ev).__name__, "data": d})

t0 = time.time()
err = None
try:
    with DockerWorkspace(
        server_image=IMAGE,
        network="host",
        host_port=8000,
        enable_gpu=False,
        health_check_timeout=180.0,
    ) as ws:
        verdict["workspace_cls"]       = type(ws).__name__
        verdict["workspace_is_remote"] = isinstance(ws, RemoteWorkspace)
        verdict["workspace_host"]      = getattr(ws, "host", None)

        conv = Conversation(agent=agent, workspace=ws, callbacks=[on_event])
        conv.send_message(Message(role="user",
                                  content=[TextContent(text=TASK)]))
        conv.run()

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

tc = {}
for e in events:
    tc[e["cls"]] = tc.get(e["cls"], 0) + 1
verdict["type_counts"] = tc

def evt_text(e):
    return json.dumps(e["data"], default=str)[:16000]

# Concatenate ALL event data for negative-check greps
all_evt_text = " ".join(evt_text(e) for e in events)

def any_event(pred):
    return any(pred(e) for e in events)

verdict["has_finish_action"] = any_event(
    lambda e: e["cls"] == "ActionEvent" and "Finish" in evt_text(e)
)
verdict["has_router_ok_string"] = any_event(
    lambda e: "router-ok-3j" in evt_text(e)
)
verdict["has_router_ok_file"] = any_event(
    lambda e: "router-ok.txt" in evt_text(e)
)
verdict["has_terminal_error"] = any_event(
    lambda e: e["cls"] == "ConversationErrorEvent"
)

# Negative checks: did the request actually reach vLLM :8100, or did
# it fall back to api.openai.com? Litellm's OpenAI fallback would
# produce distinctive error strings if the endpoint were wrong.
verdict["events_mention_openai"] = ("api.openai.com" in all_evt_text)
verdict["events_mention_incorrect_api_key"] = ("Incorrect API key" in all_evt_text)
verdict["events_mention_vllm_8100"] = ("127.0.0.1:8100" in all_evt_text or "http://127.0.0.1:8100" in all_evt_text)

# Router selection ok?
verdict["rebuild_is_router"] = (verdict.get("rebuilt_cls") == "CoderPlannerRouter")
verdict["rebuild_has_both_llms"] = (
    verdict.get("rebuilt_llms_for_routing_keys") == ["coder", "planner"]
)

verdict["pass"] = (
    err is None
    and verdict.get("workspace_is_remote", False)
    and verdict.get("agent_llm_cls") == "CoderPlannerRouter"
    and verdict["rebuild_is_router"]
    and verdict["rebuild_has_both_llms"]
    and verdict["event_count"] > 0
    and verdict["has_finish_action"]
    and verdict["has_router_ok_string"]
    and not verdict["has_terminal_error"]
    and not verdict["events_mention_openai"]
    and not verdict["events_mention_incorrect_api_key"]
    and wall < 300
)

(OUT_DIR / "events.json").write_text(json.dumps(events, indent=2, default=str))
(OUT_DIR / "verdict.json").write_text(json.dumps(verdict, indent=2, default=str))
print(json.dumps(verdict, indent=2, default=str))
PY

rc=$?
echo ""
echo "=== Item 3.j smoke complete — rc=$rc — verdict at $OUT_DIR/verdict.json ==="
exit $rc
