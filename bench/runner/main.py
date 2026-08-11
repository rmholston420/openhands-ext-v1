"""End-to-end tier orchestration.

`run_tier(args)` is the entrypoint imported by scripts/benchmark-tier-runner.py.

Flow (Fast tier):
  for each expanded candidate in the role pool:
    START-CELL bookend
    launch server (VLLMServer or LlamaCppServer)
    wait_ready() with heartbeat
    start NVML sampler (GPU cells only)
    dispatch probe (probe_coder | probe_planner | probe_embedder)
    stop NVML sampler
    terminate server (SIGTERM -> SIGKILL fallback)
    apply rubric rules (R1/R2/R3/R4) → verdict + notes
    build BenchRun, validate against run.schema.json, write to disk
    END-CELL bookend

Rubric enforcement (bench/rubrics/fast-elimination.json):
  R1 = launch failure → eliminate.
  R2 = >1 malformed task → eliminate.
  R3 = latency >5x fastest same-role → flag, don't eliminate.
  R4 = R1 + prior success under older runtime → tag runtime_version_regression.

Progress-visibility (ADR-0007 §7):
  Every step is timestamped and [i/N]-counted; long phases carry heartbeats.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bench.schema import (
    BenchRun,
    Candidate,
    CpuEnvelope,
    CrossCandidateContention,
    Device,
    Format,
    GpuEnvelope,
    Latency,
    Role,
    Rubric,
    Runtime,
    RunMetadata,
    SCHEMA_VERSION,
    TaskOutcome,
    TaskSet,
    Tier,
    ToolCallBehavior,
    Verdict,
    VerdictSource,
    validate_dict,
)

from .candidates import ExpandedCandidate, expand_for_role, MODELS_DIR, REPO_ROOT
from .nvml import NvmlSampler, nvml_available
from .probes import (
    ProbeResult,
    probe_coder,
    probe_embedder,
    probe_planner,
    summarize_latency,
    summarize_tool_call_behavior,
    verdict_from_probe,
)
from .progress import Progress, enforce_unbuffered_env
from .server import (
    BaseServer,
    LaunchFailReason,
    LlamaCppServer,
    ServerLaunchError,
    VLLMServer,
)


# --- Port assignments (spec §0.1) ------------------------------------------

PORTS = {
    ("llama.cpp", "coder"):    8082,
    ("llama.cpp", "planner"):  8082,
    ("llama.cpp", "embedder"): 8085,   # GPU embedder cell
    ("vllm",      "coder"):    8501,
    ("vllm",      "planner"):  8501,
    ("vllm",      "embedder"): 8092,   # GPU embedder cell
    # CPU embedder cells offset:
    ("llama.cpp-cpu", "embedder"): 8083,
    ("vllm-cpu",      "embedder"): 8090,
}


# --- Utilities --------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _result_path(results_dir: Path, tier: Tier, role: Role,
                 cand: ExpandedCandidate, started: datetime,
                 smoke: bool = False) -> Path:
    slug = "-".join([
        cand.slug.lower().replace("/", "-").replace(":", "-"),
        cand.runtime.replace(".", "-"),
        cand.device,
    ])
    stamp = started.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "smoke" if smoke else "phase-0"
    return results_dir / f"{prefix}-{tier.value}-{role.value}-{slug}-{stamp}.json"


def _harness_commit_sha() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, stderr=subprocess.DEVNULL, timeout=5,
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


def _load_rubric(path: Optional[Path]) -> Optional[Rubric]:
    if path is None:
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    # locked_at_utc == authored_utc for the ratified rubric file.
    ts = raw.get("authored_utc") or raw["locked_at_utc"]
    return Rubric(
        identity=raw.get("$comment", "")[:60] or "fast-elimination",
        version=raw.get("schema_version", "1.0.0"),
        locked_at_utc=datetime.fromisoformat(ts.replace("Z", "+00:00")),
    )


def _format_enum(fmt: str) -> Format:
    try:
        return Format(fmt)
    except ValueError:
        return Format.OTHER


# --- Rubric enforcement (fast-elimination.json) -----------------------------


def _apply_fast_rubric(
    *,
    launch_failed: bool,
    launch_fail_reason: Optional[LaunchFailReason],
    probe: Optional[ProbeResult],
    fastest_wall_seconds_for_role: Optional[float],
) -> tuple[str, str]:
    """Return (verdict, notes) after applying R1-R4.

    verdict ∈ {"pass", "fail", "unknown"} — Fast tier is elimination-only.
    """
    notes: list[str] = []

    # R1: launch failure.
    if launch_failed:
        reason = launch_fail_reason.value if launch_fail_reason else "unknown"
        notes.append(f"R1: launch_failure ({reason})")
        # R4: distinguish infra regression from model failure.
        if launch_fail_reason in (LaunchFailReason.STARTUP_TIMEOUT,
                                  LaunchFailReason.EARLY_EXIT):
            notes.append("R4-candidate: possible runtime_version_regression "
                         "— verify against pinned runtime version before "
                         "attributing to model")
        return "fail", "; ".join(notes)

    if probe is None:
        return "unknown", "no probe result"

    # R2: >1 malformed task.
    malformed = sum(1 for t in probe.tasks if t.verdict != "pass")
    if malformed > 1:
        details = [f"{t.task_id}: {t.detail or 'malformed'}"
                   for t in probe.tasks if t.verdict != "pass"]
        notes.append(f"R2: {malformed} malformed tasks (>1 threshold): "
                     + "; ".join(details))
        v = "fail"
    else:
        v = verdict_from_probe(probe)
        if malformed == 1:
            for t in probe.tasks:
                if t.verdict != "pass":
                    notes.append(f"R2-warning: 1 malformed task "
                                 f"({t.task_id}: {t.detail or 'malformed'})")

    # R3: latency outlier.
    if fastest_wall_seconds_for_role and fastest_wall_seconds_for_role > 0:
        cand_walls = [t.wall_seconds for t in probe.tasks if t.wall_seconds > 0]
        if cand_walls:
            cand_median = sorted(cand_walls)[len(cand_walls) // 2]
            if cand_median > 5 * fastest_wall_seconds_for_role:
                notes.append(f"R3: latency_outlier "
                             f"(median={cand_median:.2f}s > 5x fastest="
                             f"{fastest_wall_seconds_for_role:.2f}s) "
                             f"— flag for Medium tier, no eliminate at Fast")

    if probe.notes:
        notes.append(probe.notes)

    return v, "; ".join(notes) if notes else ""


# --- Per-cell dispatch ------------------------------------------------------


def _run_one_cell(
    *,
    tier: Tier,
    role: Role,
    cand: ExpandedCandidate,
    task_set_data: dict,
    task_set_meta: TaskSet,
    rubric: Optional[Rubric],
    llama_cpp_build_tag: Optional[str],
    vllm_release_tag: Optional[str],
    fastest_wall_seconds_for_role: Optional[float],
    progress: Progress,
    server_log_dir: Path,
    workspace_root: Path,
    dry_run: bool,
) -> BenchRun:
    """Run one candidate cell end-to-end. Never raises for expected failure
    modes — encodes them into the BenchRun instead."""

    cell_label = f"{role.value}/{cand.slug}/{cand.runtime}/{cand.device}"
    progress.start_cell(cell_label)
    started_at = _utcnow()
    started_mono = time.monotonic()

    # If dry-run, skip real serving; emit scaffold record.
    if dry_run:
        progress.log("CELL", f"{cell_label} DRY-RUN — no server, no probe")
        record = _build_scaffold_run(
            tier=tier, role=role, cand=cand, task_set_meta=task_set_meta,
            started_at=started_at, ended_at=_utcnow(),
            llama_cpp_build_tag=llama_cpp_build_tag,
            vllm_release_tag=vllm_release_tag, rubric=rubric,
            notes="dry-run scaffold",
        )
        progress.end_cell(cell_label, verdict="dry-run")
        return record

    # 1. Preflight probe SDK availability so we can annotate up front.
    try:
        import openhands.sdk  # noqa: F401
        sdk_ok = True
    except ImportError:
        sdk_ok = False
    if not sdk_ok and role == Role.CODER:
        progress.log("PROBE",
                     f"{cell_label} openhands-sdk not installed — coder cell will "
                     f"use fallback tool-call probe (§0.0c §category 1 partial)")

    # 2. Launch server.
    server: Optional[BaseServer] = None
    launch_failed = False
    launch_fail_reason: Optional[LaunchFailReason] = None
    launch_fail_detail: str = ""
    cold_start_ms: float = 0.0

    try:
        with progress.phase(
            "LAUNCH",
            f"{cell_label} runtime={cand.runtime} slug={cand.slug} "
            f"size~={cand.approx_size_gib}GiB",
            expected_seconds=180,
        ):
            server = _make_server(cand, role, cell_label.replace("/", "_"),
                                  progress, server_log_dir)
            server.start()
            cold_start_ms = server.wait_ready(timeout=300) * 1000.0
    except ServerLaunchError as exc:
        launch_failed = True
        launch_fail_reason = exc.reason
        launch_fail_detail = exc.detail
        progress.log("LAUNCH", f"{cell_label} FAIL [{exc.reason.value}] {exc.detail}")
        if exc.server_log_tail:
            for ln in exc.server_log_tail.splitlines()[-20:]:
                progress.log("LAUNCH", f"{cell_label} log: {ln}")

    probe: Optional[ProbeResult] = None
    gpu_env: Optional[GpuEnvelope] = None
    cpu_env: Optional[CpuEnvelope] = None

    if not launch_failed and server is not None:
        # 3. Start NVML sampler.
        sampler: Optional[NvmlSampler] = None
        if cand.device == "gpu":
            sampler = NvmlSampler(interval_ms=250)
            sampler.start()
            if not nvml_available():
                progress.log("NVML", f"{cell_label} pynvml unavailable — envelope will report coverage=0")

        # 4. Dispatch probe.
        endpoint = f"http://127.0.0.1:{server.port}"
        served_name = getattr(server, "served_name", cand.slug)
        with progress.phase("PROBE", f"{cell_label} probing role={role.value}",
                            expected_seconds=180):
            try:
                if role == Role.CODER:
                    probe = probe_coder(
                        endpoint=endpoint, served_name=served_name,
                        task_set=task_set_data,
                        budget_tokens=task_set_data.get("budget_tokens", 4096),
                        workspace_root=workspace_root,
                    )
                elif role == Role.PLANNER:
                    probe = probe_planner(
                        endpoint=endpoint, served_name=served_name,
                        task_set=task_set_data,
                        budget_tokens=task_set_data.get("budget_tokens", 4096),
                    )
                else:
                    probe = probe_embedder(
                        endpoint=endpoint, served_name=served_name,
                        task_set=task_set_data,
                    )
            except Exception as exc:
                # Probe crashed unexpectedly — treat as launch-adjacent failure.
                progress.log("PROBE", f"{cell_label} probe crashed: {exc!r}")
                probe = None

        # 5. Stop NVML sampler + collect envelope.
        if sampler is not None:
            sampler.stop()
            gpu_env = sampler.result()
            progress.log("NVML",
                         f"{cell_label} vram_peak={gpu_env.vram_peak_mib:.0f}MiB "
                         f"temp_peak={gpu_env.temp_peak_c:.1f}C "
                         f"coverage={gpu_env.nvml_coverage_pct:.1f}%")

    # 6. Teardown server (always, even on partial success).
    if server is not None:
        server.terminate()

    ended_at = _utcnow()

    # 7. Apply rubric.
    verdict_str, verdict_notes = _apply_fast_rubric(
        launch_failed=launch_failed,
        launch_fail_reason=launch_fail_reason,
        probe=probe,
        fastest_wall_seconds_for_role=fastest_wall_seconds_for_role,
    )
    if launch_failed:
        verdict_notes = f"{verdict_notes} :: {launch_fail_detail}"

    # 8. Build BenchRun.
    record = _build_run(
        tier=tier, role=role, cand=cand, task_set_meta=task_set_meta,
        started_at=started_at, ended_at=ended_at,
        llama_cpp_build_tag=llama_cpp_build_tag, vllm_release_tag=vllm_release_tag,
        rubric=rubric,
        probe=probe,
        gpu_env=gpu_env, cpu_env=cpu_env,
        cold_start_ms=cold_start_ms,
        verdict_str=verdict_str, verdict_notes=verdict_notes,
        launched_ok=not launch_failed,
    )

    progress.end_cell(cell_label, verdict=verdict_str)
    return record


def _make_server(
    cand: ExpandedCandidate, role: Role, cell_id: str,
    progress: Progress, log_dir: Path,
) -> BaseServer:
    """Build a server supervisor for `cand`. Raises for unknown runtime/device."""
    role_str = role.value

    if cand.runtime == "vllm":
        port_key = ("vllm-cpu", "embedder") if (cand.device == "cpu" and role == Role.EMBEDDER) \
                   else ("vllm", role_str)
        port = PORTS[port_key]
        if cand.device == "cpu":
            # vLLM CPU offload not yet wired in Phase 0.1 — flag and refuse.
            raise ServerLaunchError(
                reason=LaunchFailReason.MISSING_BINARY,
                detail="vLLM CPU cells require --device cpu build; not wired at Phase 0.1",
            )
        return VLLMServer(
            cell_id=cell_id,
            model_dir=cand.local_model_dir,
            port=port,
            served_name=cand.slug,
            progress=progress,
            log_dir=log_dir,
        )

    if cand.runtime == "llama.cpp":
        port_key = ("llama.cpp-cpu", "embedder") if (cand.device == "cpu" and role == Role.EMBEDDER) \
                   else ("llama.cpp", role_str)
        port = PORTS[port_key]
        if cand.local_gguf_file is None:
            raise ServerLaunchError(
                reason=LaunchFailReason.MISSING_MODEL,
                detail=f"no GGUF file resolved for {cand.slug} — check registry hf_files "
                       f"and models/{cand.slug}/",
            )
        gguf_path = cand.local_model_dir / cand.local_gguf_file
        # CPU cell: force -ngl 0
        ngl = 0 if cand.device == "cpu" else 999
        return LlamaCppServer(
            cell_id=cell_id,
            gguf_path=gguf_path,
            port=port,
            served_name=cand.slug,
            role=role_str,
            progress=progress,
            log_dir=log_dir,
            ngl=ngl,
        )

    raise ServerLaunchError(
        reason=LaunchFailReason.MISSING_BINARY,
        detail=f"unknown runtime: {cand.runtime}",
    )


# --- BenchRun builders -----------------------------------------------------


def _build_scaffold_run(**kw) -> BenchRun:
    """Dry-run scaffold: latency has variance_note to satisfy the guard."""
    lat = Latency(
        per_call_warm_ms_p50=0.0, per_call_warm_ms_p95=0.0,
        cold_start_ms=0.0, per_task_wall_seconds_p50=0.0, repeats=1,
        variance_note="dry-run scaffold (§0.0a: no real measurement performed)",
    )
    started = kw["started_at"]
    ended = kw["ended_at"]
    dur = (ended - started).total_seconds()
    return BenchRun(
        run_metadata=RunMetadata(
            tier=kw["tier"], role=kw["role"],
            candidate=_to_candidate(kw["cand"]),
            task_set=kw["task_set_meta"],
            started_at_utc=started, ended_at_utc=ended,
            duration_seconds=dur,
            harness_commit_sha=_harness_commit_sha(),
            llama_cpp_build_tag=kw["llama_cpp_build_tag"],
            vllm_release_tag=kw["vllm_release_tag"],
            rubric=kw["rubric"], notes=kw.get("notes", "dry-run"),
        ),
        tool_call_behavior=None, task_outcome=None,
        gpu_envelope=None, cpu_envelope=None,
        latency=lat, cross_candidate_contention=None,
    )


def _to_candidate(cand: ExpandedCandidate) -> Candidate:
    return Candidate(
        model=cand.slug, quant=cand.quant,
        format=_format_enum(cand.format),
        runtime=Runtime(cand.runtime), device=Device(cand.device),
    )


def _build_run(
    *,
    tier: Tier,
    role: Role,
    cand: ExpandedCandidate,
    task_set_meta: TaskSet,
    started_at: datetime,
    ended_at: datetime,
    llama_cpp_build_tag: Optional[str],
    vllm_release_tag: Optional[str],
    rubric: Optional[Rubric],
    probe: Optional[ProbeResult],
    gpu_env: Optional[GpuEnvelope],
    cpu_env: Optional[CpuEnvelope],
    cold_start_ms: float,
    verdict_str: str,
    verdict_notes: str,
    launched_ok: bool,
) -> BenchRun:
    dur = (ended_at - started_at).total_seconds()

    # Latency category.
    if probe is not None and probe.tasks:
        lat_summary = summarize_latency(probe)
        latency = Latency(
            per_call_warm_ms_p50=lat_summary["per_call_warm_ms_p50"],
            per_call_warm_ms_p95=lat_summary["per_call_warm_ms_p95"],
            cold_start_ms=cold_start_ms,
            per_task_wall_seconds_p50=lat_summary["per_task_wall_seconds_p50"],
            per_task_wall_seconds_p95=lat_summary.get("per_task_wall_seconds_p95"),
            repeats=lat_summary["repeats"],
        )
    else:
        latency = Latency(
            per_call_warm_ms_p50=0.0, per_call_warm_ms_p95=0.0,
            cold_start_ms=cold_start_ms,
            per_task_wall_seconds_p50=0.0, repeats=0,
            variance_note="probe not run (launch failure or dry-run)",
        )

    # Tool-call-behavior category (coder only).
    tcb: Optional[ToolCallBehavior] = None
    if role == Role.CODER and probe is not None:
        s = summarize_tool_call_behavior(probe)
        tcb = ToolCallBehavior(
            attempts=s["attempts"], successes=s["successes"],
            malformed=s["malformed"], missing_tool_call=s["missing"],
            wrong_tool_selected=s["wrong"], argument_errors=s["argerrors"],
            loop_repetitions=0, retries=s["retries"],
        )

    # TaskOutcome category.
    outcome: Optional[TaskOutcome] = None
    if probe is not None:
        outcome = TaskOutcome(
            verdict=Verdict(verdict_str) if verdict_str in Verdict._value2member_map_
                    else Verdict.UNKNOWN,
            verdict_source=VerdictSource.VERIFY if role != Role.CODER
                    else VerdictSource.TRAJECTORY,
            context_budget_skip=False,
            truncated=any(t.truncated for t in probe.tasks),
        )
    elif not launched_ok:
        outcome = TaskOutcome(
            verdict=Verdict.FAIL,
            verdict_source=VerdictSource.TRANSPORT,
            context_budget_skip=False, truncated=False,
        )

    return BenchRun(
        run_metadata=RunMetadata(
            tier=tier, role=role,
            candidate=_to_candidate(cand),
            task_set=task_set_meta,
            started_at_utc=started_at, ended_at_utc=ended_at,
            duration_seconds=dur,
            harness_commit_sha=_harness_commit_sha(),
            llama_cpp_build_tag=llama_cpp_build_tag,
            vllm_release_tag=vllm_release_tag,
            rubric=rubric,
            notes=verdict_notes or None,
        ),
        tool_call_behavior=tcb,
        task_outcome=outcome,
        gpu_envelope=gpu_env,
        cpu_envelope=cpu_env,
        latency=latency,
        cross_candidate_contention=None,
    )


# --- Tier orchestration ----------------------------------------------------


def run_tier(args: argparse.Namespace) -> int:
    enforce_unbuffered_env()
    tier = Tier(args.tier)
    role = Role(args.role)

    # Load task set + rubric.
    task_set_data = json.loads(Path(args.task_set).read_text(encoding="utf-8"))
    rubric = _load_rubric(Path(args.rubric)) if args.rubric else None

    # Guard: planner requires rubric.
    if role == Role.PLANNER and rubric is None and not args.dry_run:
        print("[GUARD §0.0a] planner runs require --rubric locked before first scored output",
              file=sys.stderr)
        return 2

    # Guard: rubric locked before run.
    started_at = _utcnow()
    if rubric is not None and rubric.locked_at_utc >= started_at:
        print(f"[GUARD §0.0a] rubric locked_at_utc {_iso(rubric.locked_at_utc)} "
              f"not before run_started_at {_iso(started_at)}", file=sys.stderr)
        return 2

    task_set_meta = TaskSet(
        identity=f"{role.value}-{tier.value}",
        version=task_set_data.get("schema_version", "1.0.0"),
        task_count=len(task_set_data.get("tasks", [])) or len(task_set_data.get("queries", [])),
    )

    # Expand candidates from registry.
    if args.candidate_file:
        candidates_raw = json.loads(Path(args.candidate_file).read_text(encoding="utf-8"))
        candidates = [_from_candidate_dict(row) for row in candidates_raw]
    else:
        candidates = expand_for_role(role.value)

    if not args.dry_run and not getattr(args, "smoke", False):
        # Open-pool guard (§0.0b).
        min_pool = {
            (Tier.FAST, Role.CODER): 3,
            (Tier.FAST, Role.PLANNER): 3,
            (Tier.FAST, Role.EMBEDDER): 4,
        }.get((tier, role))
        if min_pool is not None and len(candidates) < min_pool:
            print(f"[GUARD §0.0b] {role.value}/{tier.value} pool has {len(candidates)} "
                  f"candidates; spec minimum is {min_pool}. Refusing.", file=sys.stderr)
            return 2
    if getattr(args, "smoke", False):
        print(f"[SMOKE] pool-guard bypassed; results tagged smoke=true", file=sys.stderr)

    if not candidates:
        print("no candidates to run", file=sys.stderr)
        return 1

    results_dir: Path = Path(args.results_dir)
    server_log_dir = results_dir / "server-logs"
    workspace_root = Path(args.workspace_root) if args.workspace_root \
        else Path("/tmp/oh-ext-workspace")
    results_dir.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)

    progress = Progress(total_cells=len(candidates))
    progress.log("RUN",
                 f"tier={tier.value} role={role.value} candidates={len(candidates)} "
                 f"results_dir={results_dir}")
    progress.log("RUN",
                 f"host={platform.node()} python={platform.python_version()} "
                 f"nvml_available={nvml_available()}")

    # Fastest wall for role — updated as cells complete so later cells can flag R3.
    fastest: Optional[float] = None
    exit_code = 0

    for cand in candidates:
        run_started = _utcnow()
        try:
            record = _run_one_cell(
                tier=tier, role=role, cand=cand,
                task_set_data=task_set_data, task_set_meta=task_set_meta,
                rubric=rubric,
                llama_cpp_build_tag=args.llama_cpp_build,
                vllm_release_tag=args.vllm_release,
                fastest_wall_seconds_for_role=fastest,
                progress=progress,
                server_log_dir=server_log_dir,
                workspace_root=workspace_root,
                dry_run=args.dry_run,
            )
        except Exception as exc:
            progress.log("CELL",
                         f"UNCAUGHT {cand.slug}/{cand.runtime}/{cand.device}: {exc!r}")
            exit_code = 1
            continue

        # Update fastest tracker (skip dry-run / failed launches).
        if record.latency.per_task_wall_seconds_p50 > 0:
            fastest = min(fastest or float("inf"),
                          record.latency.per_task_wall_seconds_p50)

        # Validate + write.
        as_dict = record.to_dict()
        try:
            validate_dict(as_dict)
        except Exception as exc:
            progress.log("SCHEMA",
                         f"FAIL validation for {cand.slug}: {exc}")
            exit_code = 1
            continue
        out = _result_path(results_dir, tier, role, cand, run_started,
                           smoke=getattr(args, "smoke", False))
        out.write_text(json.dumps(as_dict, indent=2) + "\n", encoding="utf-8")
        progress.log("WRITE", f"{out}")

    progress.log("RUN", f"complete exit_code={exit_code}")
    return exit_code


def _from_candidate_dict(row: dict) -> ExpandedCandidate:
    """Load a candidate row from a hand-written --candidate-file JSON list."""
    slug = row["model"]
    return ExpandedCandidate(
        slug=slug,
        hf_repo=row.get("hf_repo", ""),
        format=row.get("format", "safetensors"),
        runtime=row["runtime"],
        device=row.get("device", "gpu"),
        role=row.get("role", "coder"),
        quant=row.get("quant", "unknown"),
        approx_size_gib=float(row.get("approx_size_gib", 0)),
        local_model_dir=MODELS_DIR / slug,
        local_gguf_file=row.get("gguf_file"),
        notes=row.get("notes", ""),
    )
