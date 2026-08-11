#!/usr/bin/env python3
"""Inspect per-task raw content lengths from a probe.json sidecar.

Prints one row per task with wall_seconds, output_tokens (from result.json if
present), raw_content length, and truncation flag. Used to size completion
budgets empirically from evidence, not guess.

Usage:
    scripts/inspect-raw-content.py <probe.json> [<probe.json> ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def inspect(probe_path: Path) -> None:
    probe = json.loads(probe_path.read_text())
    # Companion result JSON, if present
    result_path = probe_path.with_name(probe_path.name.replace(".probe.json", ".json"))
    result = None
    if result_path.exists():
        try:
            result = json.loads(result_path.read_text())
        except Exception:
            result = None

    print(f"=== {probe_path.name} ===")
    for t in probe.get("tasks", []):
        raw = t.get("raw_content") or ""
        raw_chars = len(raw)
        # Count <think>...</think> chars specifically (if any)
        think_chars = 0
        depth = 0
        i = 0
        while i < len(raw):
            if raw[i:i+7] == "<think>":
                start = i
                depth += 1
                i += 7
                continue
            if raw[i:i+8] == "</think>":
                if depth > 0:
                    think_chars += (i + 8) - start
                    depth -= 1
                i += 8
                continue
            i += 1
        # Look up wall + tokens
        wall = t.get("wall_seconds", 0.0)
        truncated = t.get("truncated", False)
        detail = t.get("detail", "")
        # Approx tokens from chars (4 chars/token rough)
        approx_tokens = raw_chars // 4
        print(f"  task={t.get('task_id')}")
        print(f"    verdict={t.get('verdict')}  wall={wall}s  truncated={truncated}")
        print(f"    raw_chars={raw_chars}  approx_tokens={approx_tokens}  think_chars={think_chars}")
        if detail:
            print(f"    detail={detail}")
        # Show first 200 chars of raw so we can eyeball
        head = raw[:200].replace("\n", "\\n")
        print(f"    head[:200]={head!r}")
    print()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    for p in sys.argv[1:]:
        inspect(Path(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
