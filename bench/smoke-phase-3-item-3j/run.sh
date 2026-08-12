#!/usr/bin/env bash
# bench/smoke-phase-3-item-3j/run.sh — Phase 3 sign-off item 3.j smoke.
#
# CoderPlannerRouter (RouterLLM subclass) survives the ADR-0034 serialization
# boundary. Per ADR-0036, this smoke runs under LocalWorkspace, not
# DockerWorkspace: the published `ghcr.io/openhands/agent-server:*-python`
# tags are PyInstaller binary target with frozen `openhands.sdk` bytecode
# inside the ELF, so no overlay-image approach can inject the ADR-0034 patch
# into the container. The container-side leg is deferred to sign-off item 3.k
# (source-target agent-server rebuild). LocalWorkspace exercises the same
# patched code path (`LLM._validate_subtype` via `LLM.model_validate`) in the
# client interpreter, which is sufficient evidence for ADR-0034.
#
# Verdict criteria:
#   - agent.llm is CoderPlannerRouter client-side.
#   - agent.model_dump(mode="json", context={"expose_secrets": True})
#     round-trips through LLM.model_validate back to CoderPlannerRouter
#     with llms_for_routing.coder.base_url == vLLM :8100 and
#     llms_for_routing.planner.base_url == llama.cpp :8082 preserved.
#     This is the load-bearing ADR-0034 assertion.
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
# Planner :8082 endpoint reachability is NOT part of 3.j's DoD.
# 3.j proves ADR-0034 round-trip + router-lands-on-vLLM for the coder
# leg. Planner is a static field in `llms_for_routing` (verified by the
# in-harness round-trip check), not called during the trivial task.
# ADR-0017 XOR co-residency blocks planner while coder holds the 5090,
# which is expected. Recorded in the verdict as `planner_endpoint_up`.
if curl -sf http://127.0.0.1:8082/v1/models >/dev/null 2>&1; then
  export PLANNER_ENDPOINT_UP=1
else
  export PLANNER_ENDPOINT_UP=0
  echo "NOTE: planner :8082 not reachable (ADR-0017 XOR while coder holds GPU). Continuing — planner presence is field-only in 3.j."
fi

TASK_FILE="$REPO_ROOT/bench/smoke-phase-3-item-3j/task.md"

echo "=== Phase 3 sign-off item 3.j smoke — $(date -Iseconds) ==="
echo "OUT_DIR=$OUT_DIR"
echo "workspace: LocalWorkspace (per ADR-0036)"
echo ""

env \
  OUT_DIR="$OUT_DIR" \
  TASK_FILE="$TASK_FILE" \
  "$VENV_PY" - <<'PY'
import json, os, tempfile, time, traceback
from pathlib import Path
from datetime import datetime, timezone

OUT_DIR = Path(os.environ["OUT_DIR"])
TASK    = Path(os.environ["TASK_FILE"]).read_text()

from config.agent import build_agent
from config.router import CoderPlannerRouter
from openhands.sdk import Conversation, Message, TextContent
from openhands.sdk.llm.llm import LLM
from openhands.sdk.workspace import LocalWorkspace

verdict = {
    "task": "3j_router_local_workspace",
    "workspace_kind": "LocalWorkspace",
    "adr_reference": "ADR-0034 (client-side, load-bearing) + ADR-0036 (LocalWorkspace decision; 3.k defers container-side)",
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "planner_endpoint_up": (os.environ.get("PLANNER_ENDPOINT_UP") == "1"),
}

# --- Build agent with the router (no bypass; this is the whole point) ---
agent = build_agent()
verdict["agent_llm_cls"]  = type(agent.llm).__name__
verdict["agent_llm_mro"]  = [c.__name__ for c in type(agent.llm).__mro__]
verdict["router_name"]    = getattr(agent.llm, "router_name", None)
verdict["llms_for_routing_keys"] = sorted(list(getattr(agent.llm, "llms_for_routing", {}).keys()))

# --- ADR-0034 round-trip proof: dump the whole agent the way
#     RemoteConversation does, then re-validate through LLM base class
#     annotation to prove the rebuild reconstructs the router subclass
#     with llms_for_routing intact. This is the load-bearing assertion.
try:
    dumped = agent.model_dump(mode="json", context={"expose_secrets": True})
    llm_payload = dumped["llm"]
    verdict["llm_payload_kind"] = llm_payload.get("kind")
    verdict["llm_payload_router_name"] = llm_payload.get("router_name")
    verdict["llm_payload_has_llms_for_routing"] = "llms_for_routing" in llm_payload
    if "llms_for_routing" in llm_payload:
        verdict["llm_payload_llms_for_routing_keys"] = sorted(list(llm_payload["llms_for_routing"].keys()))

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

# --- Run the task under LocalWorkspace ---
events = []
def on_event(ev):
    try:
        d = ev.model_dump(mode="json")
    except Exception:
        d = {"repr": repr(ev)}
    events.append({"cls": type(ev).__name__, "data": d})

t0 = time.time()
err = None
with tempfile.TemporaryDirectory(prefix="oh-3j-ws-") as ws_dir:
    try:
        # LocalWorkspace exposes `working_dir` for the task's cwd. The task
        # writes /workspace/router-ok.txt inside the sandbox path.
        # We use a temp dir per run so smoke runs are hermetic.
        ws = LocalWorkspace(working_dir=ws_dir)
        verdict["workspace_cls"]  = type(ws).__name__
        verdict["workspace_dir"]  = ws_dir

        # Rewrite the task to use the temp workspace path so LocalWorkspace's
        # cwd conventions match. Replace /workspace/ with the temp dir.
        task_local = TASK.replace("/workspace/router-ok.txt", f"{ws_dir}/router-ok.txt") \
                         .replace("cat /workspace/router-ok.txt", f"cat {ws_dir}/router-ok.txt")

        conv = Conversation(agent=agent, workspace=ws, callbacks=[on_event])
        conv.send_message(Message(role="user",
                                  content=[TextContent(text=task_local)]))
        conv.run()

        try:
            st_ws = conv.state.workspace
            verdict["state_workspace_cls"] = type(st_ws).__name__
        except Exception as e:
            verdict["state_workspace_cls_err"] = f"{type(e).__name__}: {e}"

        # File-existence check inside the workspace dir as additional evidence.
        router_ok_path = Path(ws_dir) / "router-ok.txt"
        verdict["router_ok_file_exists"] = router_ok_path.exists()
        if router_ok_path.exists():
            verdict["router_ok_file_contents"] = router_ok_path.read_text().strip()
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
verdict["has_router_ok_file_ref"] = any_event(
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

# ADR-0034 assertion (load-bearing): both base URLs preserved through
# the dump→validate round-trip.
verdict["rebuild_preserves_coder_url"] = (
    verdict.get("rebuilt_coder_base_url", "").startswith("http://127.0.0.1:8100")
)
verdict["rebuild_preserves_planner_url"] = (
    verdict.get("rebuilt_planner_base_url", "").startswith("http://127.0.0.1:8082")
)

verdict["pass"] = (
    err is None
    and verdict.get("agent_llm_cls") == "CoderPlannerRouter"
    and verdict["rebuild_is_router"]
    and verdict["rebuild_has_both_llms"]
    and verdict["rebuild_preserves_coder_url"]
    and verdict["rebuild_preserves_planner_url"]
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
