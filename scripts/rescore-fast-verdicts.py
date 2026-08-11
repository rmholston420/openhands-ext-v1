#!/usr/bin/env python3
"""Rescore fast-tier result JSONs against the current rubric implementation.

Motivation: prior to the 2026-08-11 harness fix, _apply_fast_rubric delegated
the verdict to verdict_from_probe when malformed <= 1, which turned a single
malformed task into a "fail" — a violation of the R2 rubric text (eliminate
iff >1 malformed). This script reads each <result>.probe.json, re-applies the
CURRENT (post-fix) rubric via _apply_fast_rubric, and rewrites the corresponding
<result>.json in place. Only task_outcome.verdict, run_metadata.notes, and
run_metadata.harness_commit_sha are touched.

Usage:
    scripts/rescore-fast-verdicts.py <result_json> [<result_json> ...]

Idempotent: running twice produces identical output.
Rubric file itself is NEVER edited — this only rebuilds the derived verdict.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Bootstrap import path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bench.runner.main import _apply_fast_rubric  # noqa: E402
from bench.runner.probes import ProbeResult, TaskResult  # noqa: E402
from bench.runner.server import LaunchFailReason  # noqa: E402


def _probe_from_json(data: dict) -> ProbeResult:
    """Reconstruct a ProbeResult from a .probe.json payload."""
    pr = ProbeResult(role=data.get("role", ""), notes=data.get("notes", ""))
    for t in data.get("tasks", []):
        tr = TaskResult(
            task_id=t["task_id"],
            verdict=t.get("verdict", "fail"),
            verdict_source=t.get("verdict_source", "verify"),
            wall_seconds=t.get("wall_seconds", 0.0),
            detail=t.get("detail", ""),
            truncated=t.get("truncated", False),
            raw_content=t.get("raw_content"),
        )
        pr.tasks.append(tr)
    return pr


def rescore(result_path: Path) -> tuple[str, str, str]:
    """Return (old_verdict, new_verdict, new_notes)."""
    probe_path = result_path.with_suffix(".probe.json") if not str(result_path).endswith(".probe.json") else result_path
    if str(result_path).endswith(".probe.json"):
        raise ValueError(f"pass the result JSON, not the probe JSON: {result_path}")
    if not probe_path.exists():
        # convention: <stem>.json + <stem>.probe.json
        stem = result_path.name[:-5]  # drop .json
        probe_path = result_path.parent / f"{stem}.probe.json"
    if not probe_path.exists():
        raise FileNotFoundError(f"no probe sidecar for {result_path}")

    result = json.loads(result_path.read_text())
    probe_data = json.loads(probe_path.read_text())
    probe = _probe_from_json(probe_data)

    # Launch failure detection: preserved from prior verdict_source == "transport"
    launch_failed = result.get("task_outcome", {}).get("verdict_source") == "transport"
    launch_reason = None
    if launch_failed:
        # can't recover exact reason from JSON; use a generic marker
        launch_reason = LaunchFailReason.EARLY_EXIT

    old_verdict = result.get("task_outcome", {}).get("verdict", "")
    new_verdict, new_notes = _apply_fast_rubric(
        launch_failed=launch_failed,
        launch_fail_reason=launch_reason,
        probe=probe,
        fastest_wall_seconds_for_role=None,  # R3 is non-eliminating; safe to skip
    )

    if new_verdict == old_verdict and new_notes == result.get("run_metadata", {}).get("notes", ""):
        return old_verdict, new_verdict, "unchanged"

    result["task_outcome"]["verdict"] = new_verdict
    result["run_metadata"]["notes"] = new_notes
    # Stamp the harness commit that produced this rescore
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"], cwd=ROOT, text=True
        ).strip()
        result["run_metadata"]["harness_commit_sha"] = sha
    except Exception:
        pass

    result_path.write_text(json.dumps(result, indent=2) + "\n")
    return old_verdict, new_verdict, new_notes


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    paths = [Path(p) for p in sys.argv[1:]]
    exit_code = 0
    for p in paths:
        try:
            old, new, notes = rescore(p)
            flag = "  " if old == new else "CHG"
            print(f"[{flag}] {p.name}: {old} -> {new}")
            if notes != "unchanged":
                print(f"      notes: {notes}")
        except Exception as exc:  # noqa: BLE001
            print(f"[ERR] {p}: {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
