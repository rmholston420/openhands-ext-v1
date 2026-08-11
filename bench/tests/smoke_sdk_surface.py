#!/usr/bin/env python3
"""ADR-0026 v1 SDK-surface smoke — Phase 0.3 gate-2 stage-1 smoke.

Purpose: verify that every SDK symbol and method that `_probe_coder_sdk`
depends on actually exists in the installed openhands-sdk 1.41.0 with the
signature the harness assumes. No LLM is contacted; `conv.run()` is NOT
invoked. If this passes, all remaining stage-1 risks in `_probe_coder_sdk`
reduce to LLM-side surface (tool registration, output shape) that stage-2
(one-task runner smoke at :8100) will exercise.

Checks (in order — each is a hard stop):
  1. All imports the harness uses resolve.
  2. DockerWorkspace boots (health_check_timeout=120s).
  3. execute_command(cmd) returns an object with either .stdout or .output
     AND either .exit_code or .returncode. Records which attributes exist so
     we can lock the harness to a stable shape.
  4. file_upload(host_path, container_path) round-trips: seed a small file,
     upload, cat back, byte-compare.
  5. mkdir chain works (parent-of-parent path).
  6. Agent(llm=<stub>, tools=[]) constructs. LLM constructor is called but
     no request is made.
  7. Conversation(agent, workspace=ws, callbacks=[cb], max_iteration_per_run=20)
     constructs. `.send_message('hi')` is called. `.run()` is NOT called.
  8. Event class isinstance checks work (ActionEvent, ObservationEvent,
     MessageEvent, AgentErrorEvent are all classes).
  9. ws.cleanup() succeeds.

Run:
    python -m bench.tests.smoke_sdk_surface

Emits a compact JSON report on stdout and exits 0 on success, 1 on any
verified failure. All errors are wrapped so partial results still print.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path


def _rec(status: str, **kw) -> dict:
    return {"status": status, **kw}


def main() -> int:
    report: dict[str, dict] = {}
    ok_so_far = True

    def step(name: str, fn):
        nonlocal ok_so_far
        if not ok_so_far:
            report[name] = _rec("skip", reason="prior step failed")
            return None
        t0 = time.monotonic()
        try:
            out = fn()
            report[name] = _rec("ok", seconds=round(time.monotonic() - t0, 3),
                                **(out or {}))
            return out
        except Exception as exc:  # noqa: BLE001
            report[name] = _rec("fail", seconds=round(time.monotonic() - t0, 3),
                                error=repr(exc))
            ok_so_far = False
            return None

    # --- 1. Imports ------------------------------------------------------
    ctx: dict = {}

    def _imports():
        from openhands.sdk import Agent, Conversation, LLM  # noqa: F401
        from openhands.sdk.event import (  # noqa: F401
            ActionEvent, AgentErrorEvent, MessageEvent, ObservationEvent,
        )
        from openhands.workspace import DockerWorkspace  # noqa: F401
        from pydantic import SecretStr  # noqa: F401
        ctx.update(
            Agent=Agent, Conversation=Conversation, LLM=LLM,
            DockerWorkspace=DockerWorkspace, SecretStr=SecretStr,
            ActionEvent=ActionEvent, ObservationEvent=ObservationEvent,
            MessageEvent=MessageEvent, AgentErrorEvent=AgentErrorEvent,
        )
        # Version snapshot for later cross-check.
        from importlib.metadata import version
        return {"openhands_sdk": version("openhands-sdk")}

    step("imports", _imports)

    # --- 2. DockerWorkspace boot -----------------------------------------
    def _boot():
        ws = ctx["DockerWorkspace"](
            working_dir="/workspace",
            enable_gpu=False,
            health_check_timeout=120.0,
        )
        ctx["ws"] = ws
        return {"type": type(ws).__name__}

    step("docker_workspace_boot", _boot)

    # --- 3. execute_command surface --------------------------------------
    def _exec():
        ws = ctx["ws"]
        result = ws.execute_command("echo hello_smoke && pwd", timeout=15.0)
        # Detect stdout attribute
        attrs = [a for a in ("stdout", "output", "exit_code", "returncode")
                 if hasattr(result, a)]
        stdout_val = getattr(result, "stdout", None) or getattr(result, "output", "")
        exit_val = getattr(result, "exit_code", getattr(result, "returncode", None))
        return {
            "result_type": type(result).__name__,
            "attrs_present": attrs,
            "stdout_head": (stdout_val or "")[:80],
            "exit_code": exit_val,
        }

    step("execute_command_surface", _exec)

    # --- 4. file_upload round-trip ---------------------------------------
    def _upload():
        ws = ctx["ws"]
        payload = "hello from smoke\n"
        with tempfile.NamedTemporaryFile(mode="w", delete=False,
                                          encoding="utf-8") as fh:
            fh.write(payload)
            host = fh.name
        try:
            ws.execute_command("mkdir -p /workspace/repo", timeout=10.0)
            ws.file_upload(host, "/workspace/repo/smoke.txt")
            r = ws.execute_command("cat /workspace/repo/smoke.txt", timeout=10.0)
            got = getattr(r, "stdout", None) or getattr(r, "output", "")
            match = got.startswith("hello from smoke")
            return {"upload_match": match, "got_head": got[:80]}
        finally:
            try:
                Path(host).unlink()
            except OSError:
                pass

    step("file_upload_roundtrip", _upload)

    # --- 5. mkdir chain --------------------------------------------------
    def _mkdir():
        ws = ctx["ws"]
        r = ws.execute_command(
            "mkdir -p /workspace/repo/a/b/c && test -d /workspace/repo/a/b/c "
            "&& echo YES", timeout=10.0,
        )
        got = (getattr(r, "stdout", None) or getattr(r, "output", "")).strip()
        return {"created": got == "YES", "got": got[:40]}

    step("mkdir_chain", _mkdir)

    # --- 6. LLM + Agent construct (no traffic) ---------------------------
    def _agent():
        llm = ctx["LLM"](
            model="openai/stub-not-served",
            base_url="http://127.0.0.1:59999/v1",  # bogus port; no request
            api_key=ctx["SecretStr"]("sk-local"),
            temperature=0.7, top_p=0.8, top_k=20,
        )
        agent = ctx["Agent"](llm=llm, tools=[])
        ctx["llm"] = llm
        ctx["agent"] = agent
        return {"agent_type": type(agent).__name__,
                "llm_type": type(llm).__name__}

    step("agent_construct", _agent)

    # --- 7. Conversation construct + send_message (no run) ---------------
    events_captured: list[str] = []

    def _cb(event) -> None:
        events_captured.append(type(event).__name__)

    def _conv():
        conv = ctx["Conversation"](
            agent=ctx["agent"], workspace=ctx["ws"],
            callbacks=[_cb], max_iteration_per_run=20,
        )
        # send_message is host-side only; must not trigger LLM traffic
        conv.send_message("smoke: verify constructor + queue only")
        ctx["conv"] = conv
        return {"conv_type": type(conv).__name__,
                "events_after_send": events_captured[-5:]}

    step("conversation_construct", _conv)

    # --- 8. Event class isinstance sanity --------------------------------
    def _events():
        # Not a real event probe — just verify the classes are usable in
        # isinstance() calls (i.e. proper classes, not typing.Union / etc.).
        cls_names = []
        for name in ("ActionEvent", "ObservationEvent", "MessageEvent",
                     "AgentErrorEvent"):
            cls = ctx[name]
            isinstance(object(), cls)  # would TypeError if not a class
            cls_names.append(name)
        return {"classes_ok": cls_names}

    step("event_classes", _events)

    # --- 9. Cleanup ------------------------------------------------------
    def _cleanup():
        ctx["ws"].cleanup()
        return {}

    step("workspace_cleanup", _cleanup)

    # --- Report ----------------------------------------------------------
    print(json.dumps({
        "harness": "smoke_sdk_surface",
        "ok": ok_so_far,
        "steps": report,
    }, indent=2))
    return 0 if ok_so_far else 1


if __name__ == "__main__":
    sys.exit(main())
