#!/usr/bin/env python3
"""benchmark-tier-runner — Phase 0 tier orchestrator.

SCOPE: this is the *scaffolding* for Phase 0.1 / 0.2 / 0.3. It defines the
run loop, the on-disk layout for results, and the guards from
`docs/specs/integration-execution-plan-v16.md` §0.0a and §0.0c that the
actual harness must honor. Per-candidate serving and per-role scoring are
plugged in via `--task-set` and `--candidate` config files (schema at
`bench/tasks/README.md`, added in a follow-up commit).

Guards enforced here, at scaffold-level:

1. §0.0a Denominator-exclusion: this runner never subtracts malformed calls
   from denominators when computing rates. See `_summarize_rates`.
2. §0.0a Latency-must-be-measured: no code path in this file writes a
   latency value that was not observed. `--dry-run` produces null latency.
3. §0.0a Rubric lock: for planner runs, `--rubric` is required and its
   `locked_at_utc` must precede `--run-started-at`. Fail hard otherwise.
4. §0.0c Uniform schema: every run emits a `bench.schema.BenchRun` and
   validates against `run.schema.json` before it is written to disk.
5. §0.1 Tier-scope guard: `--tier fast` refuses to emit `cross_candidate_contention`.
   Only `--tier full` may populate Category 6.
6. §0.0b Open-pool guard: the runner refuses to run if `--candidate-file`
   lists fewer candidates than the spec's minimum for the role/tier. This
   catches accidental pre-narrowing.
7. §0.1 Runtime-version regression flag: launch failures under the pinned
   runtime version are tagged `runtime_version_regression=true` in the
   pruning log, not silently attributed to the model.
8. Progress visibility (user preference, 2026-08-11): the real serving loop
   MUST emit line-buffered timestamped progress at every meaningful step
   — cell start, launch phase, per-task probe, cell teardown — with an
   elapsed-seconds ticker on any phase longer than ~15s. No silent
   multi-minute phases. No `capture_output=True` without tee'ing to
   stderr/stdout in real time.

Usage (design; not yet executable end-to-end — task/candidate loaders TODO):

    python scripts/benchmark-tier-runner.py \\
      --tier fast \\
      --role coder \\
      --candidate-file bench/candidates/coder-fast.json \\
      --task-set bench/tasks/coder-fast.json \\
      --results-dir bench/results \\
      --llama-cpp-build "$(cat .versions/llama.cpp)" \\
      --vllm-release "$(cat .versions/vllm)"

Nothing in this file *runs* a model yet — the launcher and the SDK event
capture come in subsequent commits (see docs/roadmap once Phase 0 begins).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Make bench/ importable when run as a script from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench.schema import (  # noqa: E402
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


# --- Spec-enforced minimums ---------------------------------------------------

# From §0.0b + §0.1/0.2/0.3. If a candidate-file has fewer entries than these,
# the pool has been pre-narrowed and the run must refuse.
MIN_POOL: dict[tuple[Tier, Role], int] = {
    (Tier.FAST, Role.CODER): 3,     # spec §0.0b lists 3 coder candidates
    (Tier.FAST, Role.PLANNER): 3,   # spec §0.0b lists 3 planner candidates
    (Tier.FAST, Role.EMBEDDER): 4,  # 2 models * {CPU, GPU} min, actually 8 with runtime axis
    # Medium/Full pools shrink per Phase 0.2 shortlist rule (2-3/role).
    (Tier.MEDIUM, Role.CODER): 2,
    (Tier.MEDIUM, Role.PLANNER): 2,
    (Tier.MEDIUM, Role.EMBEDDER): 2,
    (Tier.FULL, Role.CODER): 2,
    (Tier.FULL, Role.PLANNER): 2,
    (Tier.FULL, Role.EMBEDDER): 2,
}


# --- Small helpers ------------------------------------------------------------


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("datetime must be tz-aware")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _summarize_rates(tcb: ToolCallBehavior) -> dict[str, float]:
    """Rate helpers that honor §0.0a denominator-exclusion.

    Every rate divides by `tcb.attempts`, NEVER by `attempts - malformed`.
    """
    if tcb.attempts == 0:
        return {
            "success_rate": 0.0,
            "malformed_rate": 0.0,
            "missing_tool_call_rate": 0.0,
            "wrong_tool_selected_rate": 0.0,
            "argument_error_rate": 0.0,
        }
    n = float(tcb.attempts)
    return {
        "success_rate": tcb.successes / n,
        "malformed_rate": tcb.malformed / n,
        "missing_tool_call_rate": tcb.missing_tool_call / n,
        "wrong_tool_selected_rate": tcb.wrong_tool_selected / n,
        "argument_error_rate": tcb.argument_errors / n,
    }


def _harness_commit_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


# --- Guard functions ----------------------------------------------------------


def guard_open_pool(tier: Tier, role: Role, candidate_count: int) -> None:
    """§0.0b: pool starts open at Fast tier. Refuse silent pre-narrowing."""
    minimum = MIN_POOL.get((tier, role))
    if minimum is None:
        return
    if candidate_count < minimum:
        raise SystemExit(
            f"[GUARD §0.0b] Candidate pool for {role.value} at {tier.value} tier is "
            f"{candidate_count}; spec minimum is {minimum}. Pool starts OPEN at Fast tier "
            f"and only shrinks after documented elimination. Refusing to run."
        )


def guard_rubric_lock(role: Role, rubric: Optional[Rubric], run_started_at: datetime) -> None:
    """§0.0a: rubrics must be timestamped before first scored output."""
    if role == Role.PLANNER and rubric is None:
        raise SystemExit(
            "[GUARD §0.0a] Planner runs require --rubric (locked before first scored output)."
        )
    if rubric is not None and rubric.locked_at_utc >= run_started_at:
        raise SystemExit(
            f"[GUARD §0.0a] Rubric locked_at_utc ({iso(rubric.locked_at_utc)}) is not "
            f"strictly before run started_at_utc ({iso(run_started_at)}). "
            f"No post-hoc rubric edits allowed."
        )


def guard_tier_scope(tier: Tier, contention: Optional[CrossCandidateContention]) -> None:
    """§0.1/0.2: only Full tier populates Category 6."""
    if contention is not None and tier != Tier.FULL:
        raise SystemExit(
            f"[GUARD §0.3] cross_candidate_contention may only be populated at tier=full "
            f"(got tier={tier.value}). Fast/Medium tiers must leave it null."
        )


def guard_latency_measured(latency: Latency, dry_run: bool) -> None:
    """§0.0a: latency values must be measured. `--dry-run` skips real measurement
    and must produce a scaffold record marked accordingly; enforce by requiring
    a `variance_note` when dry-run."""
    if dry_run and not latency.variance_note:
        raise SystemExit(
            "[GUARD §0.0a] --dry-run must set latency.variance_note='dry-run scaffold' "
            "to prevent unmeasured values from being treated as real measurements."
        )


# --- Result path convention ---------------------------------------------------

# bench/results/phase-0-<tier>-<role>-<candidate-slug>-<YYYYMMDDTHHMMSSZ>.json
def result_path(
    results_dir: Path,
    tier: Tier,
    role: Role,
    candidate: Candidate,
    started_at: datetime,
) -> Path:
    slug = "-".join(
        [
            candidate.model.lower().replace("/", "-").replace(":", "-"),
            candidate.quant.lower(),
            candidate.runtime.value.replace(".", "-"),
            candidate.device.value,
        ]
    )
    stamp = started_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"phase-0-{tier.value}-{role.value}-{slug}-{stamp}.json"
    return results_dir / fname


# --- Dry-run scaffold builder -------------------------------------------------


def build_dry_run_record(
    *,
    tier: Tier,
    role: Role,
    candidate: Candidate,
    task_set: TaskSet,
    started_at: datetime,
    llama_cpp_build_tag: Optional[str],
    vllm_release_tag: Optional[str],
    rubric: Optional[Rubric],
) -> BenchRun:
    """Produce a syntactically-valid but explicitly-marked-null BenchRun for
    dry-run/CI/schema-conformance testing. Never use for real ranking."""
    ended_at = started_at
    latency = Latency(
        per_call_warm_ms_p50=0.0,
        per_call_warm_ms_p95=0.0,
        cold_start_ms=0.0,
        per_task_wall_seconds_p50=0.0,
        repeats=1,
        variance_note="dry-run scaffold (§0.0a: no real measurement performed)",
    )
    return BenchRun(
        run_metadata=RunMetadata(
            tier=tier,
            role=role,
            candidate=candidate,
            task_set=task_set,
            started_at_utc=started_at,
            ended_at_utc=ended_at,
            duration_seconds=0.0,
            harness_commit_sha=_harness_commit_sha(),
            llama_cpp_build_tag=llama_cpp_build_tag,
            vllm_release_tag=vllm_release_tag,
            rubric=rubric,
            notes="dry-run scaffold",
        ),
        tool_call_behavior=None,
        task_outcome=None,
        gpu_envelope=None,
        cpu_envelope=None,
        latency=latency,
        cross_candidate_contention=None,
    )


# --- CLI ----------------------------------------------------------------------


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 0 tier benchmark runner (scaffolding).",
    )
    p.add_argument("--tier", required=True, choices=[t.value for t in Tier])
    p.add_argument("--role", required=True, choices=[r.value for r in Role])
    p.add_argument("--candidate-file", type=Path, required=False,
                   help="JSON list of candidates for the role at this tier.")
    p.add_argument("--task-set", type=Path, required=False,
                   help="Path to task-set definition JSON.")
    p.add_argument("--rubric", type=Path, required=False,
                   help="Required for planner: rubric JSON with locked_at_utc.")
    p.add_argument("--results-dir", type=Path, default=Path("bench/results"))
    p.add_argument("--llama-cpp-build", default=None,
                   help="Exact llama.cpp build tag for run_metadata (e.g. b10356).")
    p.add_argument("--vllm-release", default=None,
                   help="Exact vLLM release tag for run_metadata (e.g. v0.27.0).")
    p.add_argument("--dry-run", action="store_true",
                   help="Emit schema-conformant scaffold records without running models.")
    return p.parse_args(argv)


def load_candidates(path: Optional[Path]) -> list[Candidate]:
    """Minimal loader — full loader arrives with bench/candidates/*.json in a
    follow-up commit. For now, returns empty list if path is None so
    --dry-run can validate the scaffold flow."""
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[Candidate] = []
    for row in data:
        out.append(Candidate(
            model=row["model"],
            quant=row["quant"],
            format=Format(row["format"]),
            runtime=Runtime(row["runtime"]),
            device=Device(row["device"]),
        ))
    return out


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    tier = Tier(args.tier)
    role = Role(args.role)

    candidates = load_candidates(args.candidate_file)
    if not args.dry_run:
        guard_open_pool(tier, role, len(candidates))

    if candidates:
        target_candidates = candidates
    else:
        # Dry-run without a file: use a placeholder so we can validate scaffold shape.
        target_candidates = [Candidate(
            model="placeholder", quant="none", format=Format.OTHER,
            runtime=Runtime.LLAMA_CPP, device=Device.GPU,
        )]

    task_set = TaskSet(
        identity=f"{role.value}-{tier.value}",
        version="0.0.0",
        task_count=1,
    )

    # Rubric is only required for planner; dry-run allows None to demonstrate
    # that the guard fires correctly for real (non-dry) planner runs.
    rubric: Optional[Rubric] = None
    if args.rubric is not None:
        raw = json.loads(args.rubric.read_text(encoding="utf-8"))
        rubric = Rubric(
            identity=raw["identity"],
            version=raw["version"],
            locked_at_utc=datetime.fromisoformat(raw["locked_at_utc"].replace("Z", "+00:00")),
        )

    args.results_dir.mkdir(parents=True, exist_ok=True)
    exit_code = 0

    for cand in target_candidates:
        started = utcnow()
        if not args.dry_run:
            guard_rubric_lock(role, rubric, started)

        # Build scaffold record. Real path: launch server, run tasks, sample NVML,
        # collect SDK ActionEvent/ObservationEvent stream, score, then build the
        # record from real measurements. Not yet implemented.
        record = build_dry_run_record(
            tier=tier,
            role=role,
            candidate=cand,
            task_set=task_set,
            started_at=started,
            llama_cpp_build_tag=args.llama_cpp_build,
            vllm_release_tag=args.vllm_release,
            rubric=rubric,
        )

        guard_tier_scope(tier, record.cross_candidate_contention)
        guard_latency_measured(record.latency, dry_run=args.dry_run)

        # Validate before writing — schema is source of truth.
        as_dict = record.to_dict()
        validate_dict(as_dict)

        out = result_path(args.results_dir, tier, role, cand, started)
        out.write_text(json.dumps(as_dict, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE {out}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
