#!/usr/bin/env python3
"""benchmark-tier-runner — Phase 0 tier orchestrator entrypoint.

This is a thin CLI shim over `bench.runner.main.run_tier`. All orchestration
logic lives under `bench/runner/`:

  bench/runner/progress.py    — line-buffered timestamped progress printer
  bench/runner/server.py      — VLLMServer / LlamaCppServer process supervisors
  bench/runner/nvml.py        — background GPU-envelope sampler
  bench/runner/probes.py      — coder / planner / embedder probes
  bench/runner/candidates.py  — registry-based candidate expansion
  bench/runner/main.py        — per-cell dispatch, rubric enforcement, schema-emit

Design constraints enforced across the runner (see docstring of each module):

1. §0.0a Denominator-exclusion: malformed calls never leave the denominator.
2. §0.0a Latency-must-be-measured: dry-run sets an explicit variance_note.
3. §0.0a Rubric lock: planner requires --rubric locked strictly before
   run_started_at. Fail hard otherwise.
4. §0.0b Open-pool guard: refuse to run if the pool has fewer candidates
   than the spec minimum for role/tier.
5. §0.0c Uniform schema: every run emits `BenchRun` and validates against
   `bench/schema/run.schema.json` before writing.
6. §0.1 Tier-scope guard: Fast tier never populates cross_candidate_contention.
7. §0.1 Runtime-version regression flag: launch STARTUP_TIMEOUT / EARLY_EXIT
   failures are tagged with an R4 candidate note so the pruning log can
   distinguish infra work from model failure.
8. ADR-0007 §7 Progress-visibility: every meaningful step emits a
   line-buffered timestamped log with [i/N] counters; long phases carry
   heartbeats every 5s with elapsed-seconds ticker.

Example (single role, dry run — safe on any machine):

    python scripts/benchmark-tier-runner.py \\
      --tier fast --role planner \\
      --task-set bench/tasks/planner-fast.json \\
      --rubric bench/rubrics/fast-elimination.json \\
      --dry-run

Example (real Fast-tier planner run on Colossus):

    python scripts/benchmark-tier-runner.py \\
      --tier fast --role planner \\
      --task-set bench/tasks/planner-fast.json \\
      --rubric bench/rubrics/fast-elimination.json \\
      --llama-cpp-build "$(cat .versions/llama.cpp 2>/dev/null || echo unknown)" \\
      --vllm-release "$(cat .versions/vllm 2>/dev/null || echo unknown)"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make bench/ importable when run as a script from repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bench.runner.main import run_tier  # noqa: E402
from bench.schema import Role, Tier  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 0 tier benchmark runner.",
    )
    p.add_argument("--tier", required=True, choices=[t.value for t in Tier])
    p.add_argument("--role", required=True, choices=[r.value for r in Role])
    p.add_argument("--task-set", type=Path, required=True,
                   help="Path to bench/tasks/<role>-<tier>.json.")
    p.add_argument("--rubric", type=Path, required=False,
                   help="Path to bench/rubrics/<tier>-elimination.json "
                        "(required for planner).")
    p.add_argument("--candidate-file", type=Path, required=False,
                   help="Override candidate list; default = registry expansion.")
    p.add_argument("--results-dir", type=Path, default=Path("bench/results"))
    p.add_argument("--workspace-root", type=Path, required=False,
                   help="Root for coder-fixtures Docker workspace mounts. "
                        "Defaults to /tmp/oh-ext-workspace.")
    p.add_argument("--llama-cpp-build", default=None,
                   help="Exact llama.cpp build tag for run_metadata (e.g. b10356).")
    p.add_argument("--vllm-release", default=None,
                   help="Exact vLLM release tag for run_metadata (e.g. v0.27.0).")
    p.add_argument("--dry-run", action="store_true",
                   help="Skip server launch + probe; emit schema-conformant scaffold records.")
    p.add_argument("--smoke", action="store_true",
                   help="Bypass §0.0b open-pool guard (allow <min_pool candidates); "
                        "result files are prefixed 'smoke-' instead of 'phase-0-'. "
                        "Use for single-candidate hardware verification only, not "
                        "for real Fast-tier elimination decisions.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run_tier(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
