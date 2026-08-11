#!/usr/bin/env python3
"""Aggregate embedder-medium two-arm bench results into a tier-verdict summary.

Reads per-cell `.probe.json` sidecars from bench/results/ produced by two
runs of the embedder-medium bench (one per arm: portability + domain),
computes per-arm and cross-arm macro-averages, applies the ADR-0016
tiebreak (quality-first, within-3-points → speed wins), and writes a
`medium-verdict-embedder-<UTC timestamp>.json` summary at
bench/results/verdicts/.

Read-only over bench/results/. Never mutates sidecars or per-cell result
JSONs. Idempotent — regenerating the verdict file overwrites only the
target file.

Design notes:
  - Cell identity is derived from the sidecar filename's slug+runtime+device
    triple (the same slug pattern used by _result_path in main.py). Two
    sidecars for the same cell (one per arm) join on this triple.
  - The retrieval probe stores its macro-average summary in ProbeResult.notes
    as a JSON string; we parse it here.
  - Quality metric for the tiebreak is nDCG@10 (primary, gain-scaled 0/1/2
    for domain arm; binary 0/1 for BEIR arm). Within-3-points → speed wins,
    where 3 points on nDCG's 0-1 scale is 0.03 absolute.
  - Speed metric is per-cell corpus_embed_wall_seconds summed across arms
    (both arms embed once per cell).

Usage:
  python3 scripts/aggregate-embedder-medium-verdict.py \\
    --results-dir bench/results \\
    [--out-dir bench/results/verdicts] \\
    [--min-arms 2]   # require both arms present per cell; default 2

Exit codes:
  0 = verdict written.
  2 = insufficient input (no matched cells, or --min-arms not met).
  3 = malformed sidecar (missing summary JSON in notes).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Sidecar filename pattern from bench/runner/main.py::_result_path:
#   {prefix}-{tier}-{role}-{slug}-{runtime}-{device}-{stamp}.probe.json
# where prefix ∈ {phase-0, smoke}, tier=medium, role=embedder, and slug may
# itself contain dashes. We anchor with tier+role and extract runtime+device
# from the tail.
_RUNTIMES = ("vllm", "llama-cpp", "ollama")
_DEVICES = ("gpu", "cpu")


def _parse_sidecar_name(name: str) -> tuple[str, str, str] | None:
    """Return (cell_id, runtime, device) or None if unrecognizable.

    cell_id = slug+runtime+device joined by '/'; matches what the runner
    logs as the human-readable cell_label.
    """
    if not name.endswith(".probe.json"):
        return None
    stem = name[: -len(".probe.json")]
    parts = stem.split("-")
    # Walk from the tail: last part is stamp, prev is device, prev is runtime
    # (accounting for compound runtime 'llama-cpp' which contains a dash).
    if len(parts) < 6:
        return None
    stamp = parts[-1]
    if not re.match(r"^\d{8}T\d{6}Z$", stamp):
        return None
    device = parts[-2]
    if device not in _DEVICES:
        return None
    # Runtime may be single-part ('vllm', 'ollama') or two-part ('llama-cpp').
    if parts[-4:-2] == ["llama", "cpp"]:
        runtime = "llama-cpp"
        slug_end = -4
    elif parts[-3] in ("vllm", "ollama"):
        runtime = parts[-3]
        slug_end = -3
    else:
        return None
    # Locate role position: prefix + tier + role + slug ...
    # prefix ∈ {phase-0, smoke}; both have exactly one dash, so parts[0:2] = prefix,
    # parts[2] = tier, parts[3] = role, parts[4:slug_end] = slug parts.
    if len(parts) < 5:
        return None
    role_ix = 3
    tier_ix = 2
    if parts[tier_ix] != "medium" or parts[role_ix] != "embedder":
        return None
    slug = "-".join(parts[role_ix + 1 : slug_end])
    cell_id = f"{slug}/{runtime}/{device}"
    return cell_id, runtime, device


def _load_sidecar(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_from_sidecar(sidecar: dict[str, Any]) -> dict[str, Any] | None:
    """probe_embedder_retrieval stores its summary in ProbeResult.notes as JSON."""
    notes = sidecar.get("notes")
    if not notes:
        return None
    try:
        parsed = json.loads(notes)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or "macro_average" not in parsed:
        return None
    return parsed


def _cell_verdict(cell_id: str, arms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build the per-cell verdict entry from one or more arm summaries."""
    entry: dict[str, Any] = {
        "cell_id": cell_id,
        "arms_present": sorted(arms.keys()),
        "per_arm": {},
    }
    # Per-arm details.
    quality_values: list[float] = []
    embed_wall_sum = 0.0
    for arm_name, summary in arms.items():
        macro = summary["macro_average"]
        entry["per_arm"][arm_name] = {
            "task_id": summary.get("task_id"),
            "corpus_size": summary.get("corpus_size"),
            "query_count": summary.get("query_count"),
            "embed_wall_seconds": summary.get("embed_wall_seconds"),
            "macro_average": macro,
        }
        # ndcg@10 is the quality signal per ADR-0016.
        if "ndcg@10" in macro:
            quality_values.append(float(macro["ndcg@10"]))
        embed_wall_sum += float(summary.get("embed_wall_seconds") or 0.0)

    # Cross-arm macro-average of the quality metric.
    entry["quality_ndcg_at_10_cross_arm"] = (
        round(sum(quality_values) / len(quality_values), 4) if quality_values else None
    )
    entry["embed_wall_seconds_total"] = round(embed_wall_sum, 3)
    return entry


def _rank_cells(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply ADR-0016 tiebreak: quality-first; within 0.03 nDCG@10 (3 points on
    the 0-100 scale mapped to the 0-1 metric) speed wins."""
    if not cells:
        return cells
    ranked = sorted(
        cells,
        key=lambda e: (
            -(e.get("quality_ndcg_at_10_cross_arm") or -1.0),
            e.get("embed_wall_seconds_total") or float("inf"),
        ),
    )
    # Apply within-3-points tie-break: for any pair adjacent in the ranked
    # list whose quality delta is < 0.03, if the second is faster, swap it up.
    # We iterate once forward; multiple swaps happen naturally by chained
    # comparison because we start from the quality-sorted order.
    changed = True
    while changed:
        changed = False
        for i in range(len(ranked) - 1):
            a, b = ranked[i], ranked[i + 1]
            qa = a.get("quality_ndcg_at_10_cross_arm")
            qb = b.get("quality_ndcg_at_10_cross_arm")
            sa = a.get("embed_wall_seconds_total") or float("inf")
            sb = b.get("embed_wall_seconds_total") or float("inf")
            if qa is None or qb is None:
                continue
            if abs(qa - qb) < 0.03 and sb < sa:
                ranked[i], ranked[i + 1] = b, a
                changed = True
    # Attach rank number.
    for rank, entry in enumerate(ranked, start=1):
        entry["rank"] = rank
    return ranked


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument(
        "--results-dir",
        default="bench/results",
        help="directory containing embedder-medium .probe.json sidecars",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="directory for verdict JSON (default: <results-dir>/verdicts)",
    )
    ap.add_argument(
        "--min-arms",
        type=int,
        default=2,
        help="require at least this many arms per cell (default 2 = both arms)",
    )
    ap.add_argument(
        "--include-smoke",
        action="store_true",
        help="include smoke=true prefixed sidecars (default: exclude)",
    )
    args = ap.parse_args()

    results_dir = Path(args.results_dir)
    if not results_dir.is_dir():
        print(f"ERROR: results-dir does not exist: {results_dir}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir) if args.out_dir else results_dir / "verdicts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Collect matching sidecars.
    cells: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)  # cell_id -> arm -> summary
    for p in sorted(results_dir.iterdir()):
        if not p.name.endswith(".probe.json"):
            continue
        if not args.include_smoke and p.name.startswith("smoke-"):
            continue
        parsed_name = _parse_sidecar_name(p.name)
        if parsed_name is None:
            continue
        cell_id, _runtime, _device = parsed_name
        try:
            sidecar = _load_sidecar(p)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARN: cannot read {p.name}: {exc}", file=sys.stderr)
            continue
        summary = _summary_from_sidecar(sidecar)
        if summary is None:
            print(
                f"WARN: sidecar {p.name} has no retrieval summary in notes; "
                f"is this a Fast-tier embedder sidecar?",
                file=sys.stderr,
            )
            continue
        arm = summary.get("arm") or "unknown"
        # If two sidecars for the same (cell, arm) exist, keep the most recent.
        prev = cells[cell_id].get(arm)
        if prev is None or (summary.get("embed_wall_seconds") is not None):
            cells[cell_id][arm] = summary

    if not cells:
        print(
            "ERROR: no embedder-medium retrieval sidecars found matching the "
            f"expected filename pattern in {results_dir}.",
            file=sys.stderr,
        )
        return 2

    # Filter by --min-arms.
    dropped_cells: list[str] = []
    verdict_entries: list[dict[str, Any]] = []
    for cell_id, arms in cells.items():
        if len(arms) < args.min_arms:
            dropped_cells.append(f"{cell_id} (arms present: {sorted(arms.keys())})")
            continue
        verdict_entries.append(_cell_verdict(cell_id, arms))

    ranked = _rank_cells(verdict_entries)

    # Cross-cell macro (for reference only; not used in ranking).
    quality_values = [
        e["quality_ndcg_at_10_cross_arm"]
        for e in ranked
        if e.get("quality_ndcg_at_10_cross_arm") is not None
    ]

    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    verdict = {
        "$comment": (
            "Auto-generated embedder-medium tier verdict per ADR-0016. "
            "Read-only aggregation over bench/results/ .probe.json sidecars. "
            "Never mutates sidecars or per-cell result JSONs. Regenerate by "
            "re-running scripts/aggregate-embedder-medium-verdict.py."
        ),
        "schema_version": "1.0.0",
        "tier": "medium",
        "role": "embedder",
        "generated_utc": ts,
        "adr_anchor": "adrs/ADR-0016-medium-tier-scoring-rubric-hybrid.md",
        "rubric_anchor": "bench/rubrics/medium-scored.json",
        "cells_evaluated": len(ranked),
        "cells_dropped_below_min_arms": dropped_cells,
        "quality_metric": "ndcg@10 (cross-arm macro-average)",
        "tiebreak": (
            "quality-first; ties within 0.03 nDCG@10 (equivalent to 3 points "
            "on a 0-100 scale) resolved by lower total embed_wall_seconds "
            "(sum across arms)"
        ),
        "cross_cell_summary": {
            "quality_max": round(max(quality_values), 4) if quality_values else None,
            "quality_min": round(min(quality_values), 4) if quality_values else None,
            "quality_median": (
                round(sorted(quality_values)[len(quality_values) // 2], 4)
                if quality_values
                else None
            ),
        },
        "ranked_cells": ranked,
    }

    out_path = out_dir / f"medium-verdict-embedder-{ts}.json"
    out_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path}", file=sys.stderr)
    print(f"  cells evaluated: {len(ranked)}", file=sys.stderr)
    if dropped_cells:
        print(
            f"  cells dropped (below --min-arms={args.min_arms}): {len(dropped_cells)}",
            file=sys.stderr,
        )
        for c in dropped_cells:
            print(f"    - {c}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
