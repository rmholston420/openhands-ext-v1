"""Per-role probe implementations.

Each probe drives one server (already up) through its Fast-tier task set and
returns a `ProbeResult`. All HTTP is done through `urllib.request` (no
extra dependency for planner/embedder). The coder probe uses the OpenHands
SDK when available and gracefully degrades to raw tool-call chat completions
when the SDK is not installed — the degraded path still checks tool selection
via OpenAI-style tool_calls in the assistant message, and the outer runner
tags such cells with `notes="degraded: openhands-sdk unavailable"`.

Return contract:
  ProbeResult holds enough to construct a `BenchRun` category by category:
    tool_call_behavior (coder only)
    task_outcome (coder + planner; embedder passes through .verdict)
    per_call_warm_ms samples (for Latency category)
    task_wall_seconds samples
"""
from __future__ import annotations

import json
import math
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Local imports deferred to keep module import cheap for the CLI.

# --- Shared helpers ---------------------------------------------------------


class HttpPostError(Exception):
    """HTTP error with the server's response body captured.

    urllib.request.urlopen raises HTTPError on non-2xx and does NOT expose
    the response body via str(exc) — by default only the status line is
    surfaced (e.g. `<HTTPError 400: 'Bad Request'>`), which hides the actual
    validation error emitted by vLLM's OpenAI-compatible API. This wrapper
    reads the error body (best-effort) and includes it in the message so
    probe `detail` fields carry the real cause.
    """


def _http_post(url: str, payload: dict, *, timeout: int = 300) -> tuple[dict, float]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        # Best-effort body capture; the file object may already be consumed
        # or the server may have sent no body. Truncate to keep detail bounded.
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        snippet = err_body[:1024]
        raise HttpPostError(
            f"HTTP {exc.code} {exc.reason}: {snippet!r}"
            + (" [...truncated]" if len(err_body) > 1024 else "")
        ) from exc
    wall = time.monotonic() - t0
    return json.loads(raw.decode("utf-8")), wall


# --- Result dataclasses -----------------------------------------------------

# Max bytes of raw model output kept per task in the sidecar. Planner outputs
# are short JSON; thinking-model prose can be large. 8 KiB is enough to
# capture typical <think>...</think> + final JSON without bloating sidecars.
RAW_CONTENT_MAX = 8192


def _truncate_raw(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    if len(s) <= RAW_CONTENT_MAX:
        return s
    return s[:RAW_CONTENT_MAX] + f"\n\n[...truncated: original {len(s)} chars]"



@dataclass
class TaskResult:
    task_id: str
    verdict: str            # "pass" | "fail" | "timeout"
    verdict_source: str     # "verify" | "trajectory" | "timeout" | "transport"
    wall_seconds: float
    per_call_warm_ms: list[float] = field(default_factory=list)
    detail: str = ""
    truncated: bool = False
    context_budget_skip: bool = False
    # Coder-only accounting (per §0.0a denominator rule):
    tool_attempts: int = 0
    tool_successes: int = 0
    tool_malformed: int = 0
    tool_missing: int = 0
    tool_wrong: int = 0
    tool_argerrors: int = 0
    tool_retries: int = 0
    # Raw model output capture for R2 diagnosis (planner/coder). Truncated to
    # RAW_CONTENT_MAX bytes to keep sidecar files bounded. See ADR-0007 §diagnostics.
    raw_content: Optional[str] = None


@dataclass
class ProbeResult:
    role: str
    tasks: list[TaskResult] = field(default_factory=list)
    notes: str = ""


# --- Planner probe ----------------------------------------------------------


def probe_planner(
    *,
    endpoint: str,
    served_name: str,
    task_set: dict,
    budget_tokens: int,
) -> ProbeResult:
    """Raw /v1/chat/completions call; JSON-parse; validate against output_schema;
    check DAG."""
    from jsonschema import Draft202012Validator, ValidationError

    schema = task_set["output_schema"]
    validator = Draft202012Validator(schema)
    # Task-set-level chat_template_kwargs (e.g. {"enable_thinking": false}).
    # See ADR-0008: Fast-tier planner disables thinking mode.
    ctk = task_set.get("chat_template_kwargs") or {}
    # ADR-0009: Fast-tier planner uses OpenAI-compat guided decoding
    # (response_format=json_schema) so the model can only emit schema-conforming
    # JSON. Eliminates "planning prose instead of JSON" R2 failures observed
    # after ADR-0008 disabled thinking mode.
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "plan", "schema": schema, "strict": True},
    }
    result = ProbeResult(role="planner")
    notes_parts = ["response_format=json_schema"]
    if ctk:
        notes_parts.append(f"chat_template_kwargs={json.dumps(ctk)}")
    result.notes = " ".join(notes_parts)
    for t in task_set["tasks"]:
        tr = TaskResult(task_id=t["id"], verdict="fail", verdict_source="verify",
                        wall_seconds=0.0)
        payload = {
            "model": served_name,
            "messages": [{"role": "user", "content": t["prompt"]}],
            "temperature": 0.6,
            "top_p": 0.95,
            "max_tokens": budget_tokens,
            "response_format": response_format,
        }
        if ctk:
            payload["chat_template_kwargs"] = ctk
        try:
            resp, wall = _http_post(f"{endpoint}/v1/chat/completions", payload, timeout=180)
        except HttpPostError as exc:
            tr.wall_seconds = 0.0
            tr.verdict_source = "transport"
            tr.detail = f"transport error: {exc}"
            result.tasks.append(tr)
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            tr.wall_seconds = 0.0
            tr.verdict_source = "transport"
            tr.detail = f"transport error: {exc!r}"
            result.tasks.append(tr)
            continue

        tr.wall_seconds = wall
        try:
            content = resp["choices"][0]["message"]["content"]
            finish = resp["choices"][0].get("finish_reason", "")
            usage = resp.get("usage", {})
        except (KeyError, IndexError, TypeError):
            tr.detail = "malformed response envelope"
            result.tasks.append(tr)
            continue

        # Capture raw model output for R2 diagnosis (thinking blocks + JSON).
        tr.raw_content = _truncate_raw(content)

        if finish == "length":
            tr.truncated = True
            tr.detail = "truncated at max_tokens"
            result.tasks.append(tr)
            continue

        # Extract JSON object from content (strip prose accidentally emitted).
        raw = _extract_json_object(content)
        if raw is None:
            tr.detail = "no JSON object in output"
            result.tasks.append(tr)
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            tr.detail = f"JSON parse error: {exc}"
            result.tasks.append(tr)
            continue

        try:
            validator.validate(obj)
        except ValidationError as exc:
            tr.detail = f"schema violation: {exc.message}"
            result.tasks.append(tr)
            continue

        # DAG check.
        steps = obj["steps"]
        if len(steps) < int(t.get("min_steps", 3)):
            tr.detail = f"too few steps ({len(steps)} < {t.get('min_steps', 3)})"
            result.tasks.append(tr)
            continue
        if not _is_dag(steps):
            tr.detail = "dependency graph is not a DAG"
            result.tasks.append(tr)
            continue

        tr.verdict = "pass"
        tr.detail = f"steps={len(steps)} usage={usage}"
        result.tasks.append(tr)

    return result


def _extract_json_object(text: str) -> Optional[str]:
    """Extract the first balanced {...} block from text."""
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start:i + 1]
    return None


def _is_dag(steps: list[dict]) -> bool:
    """Return True iff (1) every dep references an earlier step id, and
    (2) no id appears twice."""
    seen: set[str] = set()
    for s in steps:
        sid = s["id"]
        if sid in seen:
            return False
        for dep in s.get("deps", []):
            if dep not in seen:
                return False
        seen.add(sid)
    return True


# --- Embedder probe ---------------------------------------------------------


def probe_embedder(
    *,
    endpoint: str,
    served_name: str,
    task_set: dict,
) -> ProbeResult:
    result = ProbeResult(role="embedder")
    # Single /v1/embeddings call with all inputs at once.
    inputs = [q["text"] for q in task_set["queries"]]
    payload = {"model": served_name, "input": inputs}
    task_id = "embedder-fast-all"
    tr = TaskResult(task_id=task_id, verdict="fail", verdict_source="verify",
                    wall_seconds=0.0)
    try:
        resp, wall = _http_post(f"{endpoint}/v1/embeddings", payload, timeout=120)
    except HttpPostError as exc:
        tr.detail = f"transport error: {exc}"
        tr.verdict_source = "transport"
        result.tasks.append(tr)
        return result
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        tr.detail = f"transport error: {exc!r}"
        tr.verdict_source = "transport"
        result.tasks.append(tr)
        return result

    tr.wall_seconds = wall
    try:
        vectors = [row["embedding"] for row in resp["data"]]
    except (KeyError, TypeError):
        tr.detail = "malformed embeddings envelope"
        result.tasks.append(tr)
        return result

    if len(vectors) != len(inputs):
        tr.detail = f"vector count {len(vectors)} != inputs {len(inputs)}"
        result.tasks.append(tr)
        return result

    probes = task_set["probes"]
    min_norm = float(probes.get("vector_min_norm", 1e-6))
    for i, v in enumerate(vectors):
        if v is None:
            tr.detail = f"vector[{i}] is null"
            result.tasks.append(tr)
            return result
        n = math.sqrt(sum(x * x for x in v))
        if n < min_norm:
            tr.detail = f"vector[{i}] norm {n:.2e} < min {min_norm:.2e}"
            result.tasks.append(tr)
            return result

    id_to_idx = {q["id"]: i for i, q in enumerate(task_set["queries"])}

    def _cos(a: list[float], b: list[float]) -> float:
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return sum(x * y for x, y in zip(a, b)) / (na * nb)

    id_min = float(probes["identical_pair_min_cosine"])
    or_max = float(probes["orthogonal_pair_max_cosine"])
    # identical pair
    ia = vectors[id_to_idx["embedder-fast-01-identical-a"]]
    ib = vectors[id_to_idx["embedder-fast-02-identical-b"]]
    ic = _cos(ia, ib)
    if ic < id_min:
        tr.detail = f"identical-pair cosine {ic:.4f} < min {id_min}"
        result.tasks.append(tr)
        return result
    # orthogonal pair
    oa = vectors[id_to_idx["embedder-fast-03-orthogonal-a"]]
    ob = vectors[id_to_idx["embedder-fast-04-orthogonal-b"]]
    oc = _cos(oa, ob)
    if oc > or_max:
        tr.detail = f"orthogonal-pair cosine {oc:.4f} > max {or_max}"
        result.tasks.append(tr)
        return result

    tr.verdict = "pass"
    tr.detail = f"identical={ic:.4f} orthogonal={oc:.4f} n_vecs={len(vectors)}"
    result.tasks.append(tr)
    return result


# --- Coder probe ------------------------------------------------------------


def probe_coder(
    *,
    endpoint: str,
    served_name: str,
    task_set: dict,
    budget_tokens: int,
    workspace_root: Path,
) -> ProbeResult:
    """OpenHands SDK path if available; fallback to raw tool-call chat.

    The SDK path drives Conversation(agent, workspace=DockerWorkspace(...))
    and captures ActionEvent/ObservationEvent. The fallback path issues one
    /v1/chat/completions call per task with the OpenAI tool-choice API and
    verifies the requested tool name against expected_tool_sequence[0]. Both
    paths do post-hoc file-state verification against expected_file_state and
    expected_output_contains.
    """
    sdk_unavailable_reason: Optional[str] = None
    try:
        from openhands.sdk import Agent, Conversation, LLM  # type: ignore  # noqa
        try:
            return _probe_coder_sdk(
                endpoint=endpoint, served_name=served_name,
                task_set=task_set, budget_tokens=budget_tokens,
                workspace_root=workspace_root,
            )
        except NotImplementedError as exc:
            # SDK is installed but the SDK-driven path is a stub (spec-adequate
            # per ADR-0007). Fall through to the fallback exactly like the
            # ImportError case, and tag the notes so the sidecar records why.
            sdk_unavailable_reason = f"sdk path stubbed ({exc})"
    except ImportError as exc:
        sdk_unavailable_reason = f"openhands-sdk unavailable ({exc})"

    result = _probe_coder_fallback(
        endpoint=endpoint, served_name=served_name,
        task_set=task_set, budget_tokens=budget_tokens,
    )
    if sdk_unavailable_reason:
        result.notes = (result.notes + "; " if result.notes else "") + \
            f"degraded: {sdk_unavailable_reason} — used raw tool-call fallback"
    return result


def _probe_coder_sdk(
    *,
    endpoint: str,
    served_name: str,
    task_set: dict,
    budget_tokens: int,
    workspace_root: Path,
) -> ProbeResult:
    """Full OpenHands SDK invocation per ADR-0026 v1 harness (amendment 2).

    Contract (see adrs/ADR-0026-coder-multi-turn-correctness-harness-v1.md):
      * One DockerWorkspace per cell (auto-boots container on construction).
      * Reused across all 10 tasks; wiped between tasks via execute_command.
      * Per task: wipe -> seed fixtures via file_upload -> build LLM/Agent/
        Conversation with callbacks=[on_event], max_iteration_per_run=20 ->
        send_message(prompt) -> run() -> verify expected_final_state via
        execute_command('cat ...') per expected_final_state_mode -> smoke
        test if smoke_test_command is not null -> capture event trace.
      * ws.cleanup() at cell end.

    Returns a ProbeResult whose per-task `detail` field is a JSON string
    encoding the multi-turn artifacts (tool trace, final states, smoke,
    turn count) so the scoring stage (Perplexity-Max) can read them
    directly without a second SDK invocation.
    """
    # SDK imports — must succeed here; the outer probe_coder gated on
    # ImportError already. If any of these fail we raise ImportError to
    # let probe_coder degrade to the fallback with a clear reason.
    try:
        from openhands.sdk import Agent, Conversation, LLM  # type: ignore
        from openhands.sdk.event import (  # type: ignore
            ActionEvent, AgentErrorEvent, MessageEvent, ObservationEvent,
        )
        from openhands.tools.preset.default import get_default_tools  # type: ignore
        from openhands.workspace import DockerWorkspace  # type: ignore
        from pydantic import SecretStr  # type: ignore
    except ImportError as exc:
        raise NotImplementedError(f"SDK import mismatch at runtime: {exc}") from exc

    # Standard coder tool set for stage-2 correctness runs.
    # `enable_browser=False`: bench containers have no display and we do not
    # allow network fetches during scored coder tasks.
    # `enable_sub_agents=False`: keep this a single-agent trace so events
    # match the harness contract (no TaskToolSet delegation).
    default_tools = get_default_tools(
        enable_browser=False, enable_sub_agents=False,
    )

    result = ProbeResult(role="coder")
    tasks = task_set.get("tasks", [])
    max_iter = int(task_set.get("max_iteration_per_run", 20))
    reversal = task_set.get("reversal_criteria")

    # --- Container up (once per cell) --------------------------------------
    t_ws_start = time.monotonic()
    try:
        ws = DockerWorkspace(
            working_dir="/workspace",
            enable_gpu=False,
            health_check_timeout=120.0,
        )
    except Exception as exc:  # noqa: BLE001 — container boot is a cell-fatal
        # Emit a single "task" record so the cell has structure even on
        # workspace-fatal failure, then return.
        for t in tasks:
            result.tasks.append(TaskResult(
                task_id=t["id"], verdict="fail",
                verdict_source="transport", wall_seconds=0.0,
                detail=f"DockerWorkspace boot failed: {exc!r}",
            ))
        result.notes = f"workspace_boot_failed: {exc!r}"
        return result
    ws_boot_seconds = time.monotonic() - t_ws_start
    result.notes = (
        f"harness=v1 sdk=openhands-sdk max_iter={max_iter} "
        f"ws_boot={ws_boot_seconds:.2f}s image=ghcr.io/openhands/agent-server:latest-python"
    )

    # Build LLM once per cell — same endpoint + sampling for every task.
    #
    # ADR-0026 amendment 3 (2026-08-11 EDT):
    # DockerWorkspace runs the agent inside a container on Docker's default
    # bridge network. Inside the container, 127.0.0.1 is the container's own
    # loopback — NOT the host. The runner-launched vLLM is bound to the host's
    # 127.0.0.1:<port>. To reach it from the container we rewrite loopback
    # hosts to 172.17.0.1 (docker0 bridge gateway on stock Linux Docker).
    # No effect on non-loopback endpoints (e.g. a manually configured LAN host).
    import urllib.parse as _urlparse
    parsed = _urlparse.urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    _host = parsed.hostname or ""
    if _host in ("127.0.0.1", "localhost", "0.0.0.0"):
        _port = f":{parsed.port}" if parsed.port else ""
        container_endpoint = f"{parsed.scheme}://172.17.0.1{_port}"
    else:
        container_endpoint = endpoint
    llm = LLM(
        model=f"openai/{served_name}",
        base_url=f"{container_endpoint.rstrip('/')}/v1",
        api_key=SecretStr("sk-local"),
        temperature=0.7, top_p=0.8, top_k=20,
        max_output_tokens=budget_tokens,
    )

    try:
        for t in tasks:
            tr = _run_sdk_task(
                task=t, ws=ws, llm=llm,
                Agent=Agent, Conversation=Conversation,
                ActionEvent=ActionEvent, ObservationEvent=ObservationEvent,
                MessageEvent=MessageEvent, AgentErrorEvent=AgentErrorEvent,
                max_iter=max_iter,
            )
            result.tasks.append(tr)
    finally:
        # Always tear down; --rm on the container also handles it, but explicit
        # cleanup avoids leaking a stale wrapper.
        try:
            ws.cleanup()
        except Exception:  # noqa: BLE001
            pass

    return result


# --- SDK per-task driver ----------------------------------------------------


def _run_sdk_task(
    *,
    task: dict,
    ws,
    llm,
    Agent,
    Conversation,
    ActionEvent,
    ObservationEvent,
    MessageEvent,
    AgentErrorEvent,
    max_iter: int,
) -> "TaskResult":
    """Drive a single task under the SDK Conversation contract.

    Records the full multi-turn artifact in TaskResult.detail as a compact
    JSON string. The scoring stage reads this and materializes the trace,
    file states, and smoke result for Perplexity-Max rubric evaluation.
    """
    import tempfile as _tempfile

    tid = task["id"]
    tr = TaskResult(
        task_id=tid, verdict="fail", verdict_source="verify",
        wall_seconds=0.0,
    )

    # --- 1. Wipe workspace between tasks ---------------------------------
    try:
        ws.execute_command(
            "rm -rf /workspace/repo && mkdir -p /workspace/repo",
            timeout=30.0,
        )
    except Exception as exc:  # noqa: BLE001
        tr.verdict_source = "transport"
        tr.detail = json.dumps({"phase": "wipe", "error": repr(exc)})
        return tr

    # --- 2. Seed fixtures --------------------------------------------------
    fixtures = task.get("fixtures", {}) or {}
    seed_failures: list[dict] = []
    for path, content in fixtures.items():
        if path.startswith("$"):
            # Sentinel field (e.g. "$note"); harness-side setup notes.
            # Task-08 uses "$note" to describe a git-init pre-seed; if we
            # detect it, initialize a git repo with the expected modified
            # files so the model has something to inspect via git status.
            if tid == "coder-medium-08-check-git-status":
                try:
                    ws.execute_command(
                        "cd /workspace/repo && git init -q && "
                        "echo 'orig main' > src/main.py 2>/dev/null || "
                        "(mkdir -p src && echo 'orig main' > src/main.py) && "
                        "echo 'orig readme' > README.md && "
                        "git add -A && git -c user.email=b@x -c user.name=b commit -q -m init && "
                        "echo 'modified main' > src/main.py && "
                        "echo 'modified readme' > README.md",
                        timeout=30.0,
                    )
                except Exception as exc:  # noqa: BLE001
                    seed_failures.append({"kind": "git_init", "error": repr(exc)})
            continue
        # Regular file fixture: write to host tempfile, upload, delete host copy.
        with _tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as fh:
            fh.write(content)
            host_path = fh.name
        try:
            # Ensure parent dir exists inside container.
            parent = path.rsplit("/", 1)[0]
            if parent:
                ws.execute_command(f"mkdir -p {parent}", timeout=15.0)
            ws.file_upload(host_path, path)
        except Exception as exc:  # noqa: BLE001
            seed_failures.append({"path": path, "error": repr(exc)})
        finally:
            try:
                Path(host_path).unlink()
            except OSError:
                pass

    if seed_failures:
        tr.verdict_source = "transport"
        tr.detail = json.dumps({"phase": "seed", "failures": seed_failures})
        return tr

    # --- 3. Event capture callback ---------------------------------------
    events_recorded: list[dict] = []
    tool_trace: list[str] = []
    action_count = 0
    agent_errors = 0

    def _on_event(event) -> None:
        nonlocal action_count, agent_errors
        kind = type(event).__name__
        rec = {"kind": kind}
        if isinstance(event, ActionEvent):
            action_count += 1
            # Extract tool name if possible — SDK ActionEvent varies; best-effort.
            tool_name = getattr(event, "tool_name", None) or \
                getattr(getattr(event, "action", None), "tool_name", None) or \
                getattr(getattr(event, "tool", None), "name", None)
            if tool_name:
                tool_trace.append(str(tool_name))
                rec["tool"] = str(tool_name)
        elif isinstance(event, AgentErrorEvent):
            agent_errors += 1
            rec["error"] = str(getattr(event, "error", getattr(event, "message", "")))[:200]
        elif isinstance(event, ObservationEvent):
            obs = getattr(event, "observation", None) or getattr(event, "tool_name", None)
            if obs is not None:
                rec["obs"] = str(obs)[:120]
        elif isinstance(event, MessageEvent):
            role = getattr(getattr(event, "message", None), "role", None) or \
                   getattr(event, "source", None)
            if role:
                rec["role"] = str(role)
        events_recorded.append(rec)

    # --- 4. Build Agent + Conversation and run ---------------------------
    t0 = time.monotonic()
    hit_iter_cap = False
    run_error: Optional[str] = None
    try:
        # Fail fast if the tool preset silently returns nothing — an empty
        # tool list is what caused stage-2 attempt 4 (2026-08-11 EDT) to burn
        # ~5 min in an Action/Error loop with only ['finish','think'] wired.
        assert default_tools, (
            "get_default_tools returned an empty list; refusing to launch "
            "a coder probe with no filesystem/bash tools"
        )
        agent = Agent(llm=llm, tools=default_tools)
        conv = Conversation(
            agent=agent, workspace=ws, callbacks=[_on_event],
            max_iteration_per_run=max_iter,
        )
        conv.send_message(task["prompt"])
        conv.run()
    except Exception as exc:  # noqa: BLE001
        run_error = repr(exc)
    tr.wall_seconds = time.monotonic() - t0
    if action_count >= max_iter:
        hit_iter_cap = True

    # --- 5. Verify final state -------------------------------------------
    mode = task.get("expected_final_state_mode", "rubric_only")
    expected = task.get("expected_final_state", {}) or {}
    final_states: dict[str, dict] = {}
    for path in sorted(expected.keys()):
        try:
            cmd_result = ws.execute_command(f"cat {path}", timeout=15.0)
            actual = getattr(cmd_result, "stdout", None)
            if actual is None:
                actual = getattr(cmd_result, "output", "") or ""
            final_states[path] = {
                "actual": actual,
                "expected": expected[path],
                "exit_code": getattr(cmd_result, "exit_code",
                                     getattr(cmd_result, "returncode", None)),
            }
        except Exception as exc:  # noqa: BLE001
            final_states[path] = {
                "actual": None,
                "expected": expected[path],
                "read_error": repr(exc),
            }

    # --- 6. Smoke test (optional) ----------------------------------------
    smoke_cmd = task.get("smoke_test_command")
    smoke_result: Optional[dict] = None
    if smoke_cmd:
        try:
            cmd_result = ws.execute_command(
                smoke_cmd, cwd="/workspace/repo", timeout=30.0,
            )
            smoke_result = {
                "exit_code": getattr(cmd_result, "exit_code",
                                     getattr(cmd_result, "returncode", None)),
                "stdout": (getattr(cmd_result, "stdout",
                                   getattr(cmd_result, "output", "")) or "")[:1024],
                "stderr": (getattr(cmd_result, "stderr", "") or "")[:1024],
            }
        except Exception as exc:  # noqa: BLE001
            smoke_result = {"exec_error": repr(exc)}

    # --- 7. Compact artifact record --------------------------------------
    #
    # Scoring stage (Perplexity-Max) reads this JSON and materializes the
    # inputs. Verdict here is a coarse pass/fail based on: did the agent
    # produce something (event trace non-empty) AND did the smoke test pass
    # (when present) AND is at least one expected file present. The
    # fine-grained 0-100 score is assigned by the scoring stage against the
    # gold rubric.
    coarse_pass = (
        run_error is None
        and action_count > 0
        and (smoke_result is None or smoke_result.get("exit_code") == 0)
    )
    if mode == "no_changes_expected":
        # Task-08: agent must NOT modify files. Coarse pass if event trace
        # has messages and no AgentErrorEvents. Fine-grained per rubric.
        coarse_pass = (
            run_error is None and action_count > 0 and agent_errors == 0
        )
    tr.verdict = "pass" if coarse_pass else "fail"
    tr.verdict_source = "verify"
    tr.tool_attempts = action_count
    tr.tool_successes = action_count - agent_errors
    tr.tool_wrong = 0  # scoring stage computes vs expected_tool_sequence
    tr.tool_malformed = agent_errors

    artifact = {
        "harness_version": "v1",
        "task_id": tid,
        "turn_count": action_count,
        "hit_iteration_cap": hit_iter_cap,
        "agent_error_count": agent_errors,
        "tool_trace": tool_trace,
        "expected_tool_sequence": task.get("expected_tool_sequence", []),
        "expected_tool_sequence_tolerance": task.get(
            "expected_tool_sequence_tolerance"
        ),
        "preferred_tools": task.get("preferred_tools", []),
        "dispreferred_tools": task.get("dispreferred_tools", []),
        "expected_final_state_mode": mode,
        "final_states": final_states,
        "smoke_test_command": smoke_cmd,
        "smoke_result": smoke_result,
        "run_error": run_error,
        "events_tail": events_recorded[-40:],  # keep artifact bounded
    }
    tr.detail = json.dumps(artifact, ensure_ascii=False)
    return tr


def _tool_schemas_for_task_set(task_set: dict) -> list[dict]:
    """Advertise the four coder tools referenced by coder-fast tasks."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the exact contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create a new file with exact contents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "str_replace_editor",
                "description": "Replace a specific string in an existing file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_str": {"type": "string"},
                        "new_str": {"type": "string"},
                    },
                    "required": ["path", "old_str", "new_str"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_bash",
                "description": "Execute a bash command in the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        },
    ]


def _probe_coder_fallback(
    *,
    endpoint: str,
    served_name: str,
    task_set: dict,
    budget_tokens: int,
) -> ProbeResult:
    """Single-turn tool-call probe: send tools + prompt, verify the model
    selects `expected_tool_sequence[0]` and does not invoke any forbidden
    tool. This tests tool selection under Fast-tier budget.

    Per §0.0a denominator rule: every task counts in `attempts`. Malformed
    tool-calls (JSON parse fail, wrong name, missing name) count toward
    `malformed`, `wrong_tool_selected`, `missing_tool_call` respectively —
    they are NOT removed from denominators.
    """
    result = ProbeResult(role="coder")
    tools = _tool_schemas_for_task_set(task_set)
    # Task-set-level chat_template_kwargs (opt-in; e.g. Fast tier may set
    # {"enable_thinking": false} per ADR-0008 to preserve tool-call budget
    # on thinking models). Default off preserves current coder behavior.
    ctk = task_set.get("chat_template_kwargs") or {}
    if ctk:
        result.notes = f"chat_template_kwargs={json.dumps(ctk)}"
    for t in task_set["tasks"]:
        tr = TaskResult(task_id=t["id"], verdict="fail",
                        verdict_source="trajectory", wall_seconds=0.0,
                        tool_attempts=1)
        payload = {
            "model": served_name,
            "messages": [
                {"role": "system",
                 "content": "You are a coding agent. Select exactly one tool call to accomplish the task."},
                {"role": "user", "content": t["prompt"]},
            ],
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.7,
            "top_p": 0.8,
            "max_tokens": budget_tokens,
        }
        if ctk:
            payload["chat_template_kwargs"] = ctk
        try:
            resp, wall = _http_post(f"{endpoint}/v1/chat/completions", payload, timeout=180)
        except HttpPostError as exc:
            tr.detail = f"transport error: {exc}"
            tr.verdict_source = "transport"
            tr.tool_malformed = 1
            result.tasks.append(tr)
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            tr.detail = f"transport error: {exc!r}"
            tr.verdict_source = "transport"
            tr.tool_malformed = 1
            result.tasks.append(tr)
            continue

        tr.wall_seconds = wall
        try:
            msg = resp["choices"][0]["message"]
            finish = resp["choices"][0].get("finish_reason", "")
        except (KeyError, IndexError, TypeError):
            tr.detail = "malformed response envelope"
            tr.tool_malformed = 1
            result.tasks.append(tr)
            continue

        # Capture raw message (content + tool_calls) for R2 diagnosis.
        try:
            tr.raw_content = _truncate_raw(json.dumps(msg))
        except (TypeError, ValueError):
            tr.raw_content = _truncate_raw(str(msg))

        if finish == "length":
            tr.truncated = True
            tr.detail = "truncated at max_tokens before tool_call emit"
            tr.tool_malformed = 1
            result.tasks.append(tr)
            continue

        tool_calls = msg.get("tool_calls") or []
        expected = t["expected_tool_sequence"]
        forbidden = set(t.get("forbidden_tools", []))

        if not tool_calls:
            tr.detail = f"no tool_calls (finish={finish!r})"
            tr.tool_missing = 1
            result.tasks.append(tr)
            continue

        # First tool call — check name.
        called = tool_calls[0].get("function", {}).get("name", "")
        # forbidden across the whole tool_calls list
        called_all = [tc.get("function", {}).get("name", "") for tc in tool_calls]
        if any(c in forbidden for c in called_all):
            tr.detail = f"invoked forbidden tool: {[c for c in called_all if c in forbidden]}"
            tr.tool_wrong = 1
            result.tasks.append(tr)
            continue

        if called != expected[0]:
            tr.detail = f"wrong tool: called={called!r} expected={expected[0]!r}"
            tr.tool_wrong = 1
            result.tasks.append(tr)
            continue

        # Argument well-formedness: json-parse arguments.
        args_raw = tool_calls[0].get("function", {}).get("arguments", "")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            if not isinstance(args, dict):
                raise ValueError("arguments not a dict")
        except (ValueError, json.JSONDecodeError) as exc:
            tr.detail = f"malformed tool arguments: {exc}"
            tr.tool_malformed = 1
            result.tasks.append(tr)
            continue

        tr.verdict = "pass"
        tr.tool_successes = 1
        tr.detail = f"tool={called} args_keys={sorted(args.keys())}"
        result.tasks.append(tr)

    return result


# --- Aggregators ------------------------------------------------------------


def summarize_tool_call_behavior(pr: ProbeResult) -> dict:
    tot = {"attempts": 0, "successes": 0, "malformed": 0,
           "missing": 0, "wrong": 0, "argerrors": 0, "retries": 0}
    for t in pr.tasks:
        tot["attempts"] += t.tool_attempts
        tot["successes"] += t.tool_successes
        tot["malformed"] += t.tool_malformed
        tot["missing"] += t.tool_missing
        tot["wrong"] += t.tool_wrong
        tot["argerrors"] += t.tool_argerrors
        tot["retries"] += t.tool_retries
    return tot


def summarize_latency(pr: ProbeResult) -> dict:
    walls = [t.wall_seconds for t in pr.tasks if t.wall_seconds > 0]
    if not walls:
        return {
            "per_call_warm_ms_p50": 0.0,
            "per_call_warm_ms_p95": 0.0,
            "per_task_wall_seconds_p50": 0.0,
            "repeats": len(pr.tasks),
        }
    walls_sorted = sorted(walls)

    def pct(p: float) -> float:
        if not walls_sorted:
            return 0.0
        k = min(len(walls_sorted) - 1, int(round((p / 100) * (len(walls_sorted) - 1))))
        return walls_sorted[k]

    p50 = pct(50)
    p95 = pct(95)
    return {
        "per_call_warm_ms_p50": p50 * 1000.0,
        "per_call_warm_ms_p95": p95 * 1000.0,
        "per_task_wall_seconds_p50": p50,
        "per_task_wall_seconds_p95": p95,
        "repeats": len(pr.tasks),
    }


def verdict_from_probe(pr: ProbeResult) -> str:
    """Task-set-level verdict: pass only if every task passed."""
    if not pr.tasks:
        return "unknown"
    return "pass" if all(t.verdict == "pass" for t in pr.tasks) else "fail"
