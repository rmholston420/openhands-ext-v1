#!/usr/bin/env python3
"""Summarize fast-tier verdict distribution per candidate.

Groups <results>/phase-0-fast-<role>-<candidate>-<runtime>-<device>-*.json by
(role, candidate, runtime, device) and reports the count of pass/fail/unknown
under the current rubric implementation. Sidecar-less files are counted as
"no-probe" (rescore cannot evaluate them; they retain whatever verdict the
harness wrote at the time).

Read-only. Does not rescore, does not write.

Usage:
    scripts/summarize-fast-verdicts.py [<result_glob>...]
Default glob: bench/results/phase-0-fast-*.json
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

RE_NAME = re.compile(
    r"^phase-0-fast-(?P<role>coder|planner|embedder)-"
    r"(?P<rest>.+?)-(?P<ts>\d{8}T\d{6}Z)\.json$"
)

def parse_key(fname: str) -> tuple[str, str, str] | None:
    m = RE_NAME.match(fname)
    if not m:
        return None
    role = m.group("role")
    rest = m.group("rest")
    # Rest is "<candidate-quant-format>-<runtime>-<device>". Runtime is one of
    # {vllm, llama-cpp, ollama}. Device is {gpu, cpu}. Split on last two tokens.
    parts = rest.rsplit("-", 2)
    if len(parts) != 3:
        return None
    candidate, runtime, device = parts
    return role, candidate, f"{runtime}/{device}"


def main() -> int:
    patterns = sys.argv[1:] or ["bench/results/phase-0-fast-*.json"]
    files: list[Path] = []
    for pat in patterns:
        files.extend(Path(p) for p in glob.glob(pat) if not p.endswith(".probe.json"))

    groups: dict[tuple[str, str, str], list[Path]] = defaultdict(list)
    for f in files:
        k = parse_key(f.name)
        if k:
            groups[k].append(f)

    rows: list[tuple] = []
    for (role, cand, runtime), paths in sorted(groups.items()):
        pass_ct = fail_ct = unk_ct = noprobe_ct = 0
        for p in sorted(paths):
            try:
                d = json.loads(p.read_text())
                v = d.get("task_outcome", {}).get("verdict", "unknown")
            except Exception:
                v = "unknown"
            probe = p.with_name(p.name[:-5] + ".probe.json")
            if not probe.exists():
                noprobe_ct += 1
            if v == "pass":
                pass_ct += 1
            elif v == "fail":
                fail_ct += 1
            else:
                unk_ct += 1
        rows.append((role, cand, runtime, len(paths), pass_ct, fail_ct, unk_ct, noprobe_ct))

    # Column widths
    cols = ["role", "candidate", "runtime/device", "runs", "pass", "fail", "unk", "no-probe"]
    widths = [len(c) for c in cols]
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(str(v)))

    def fmt(vals):
        return "  ".join(str(v).ljust(widths[i]) for i, v in enumerate(vals))

    print(fmt(cols))
    print(fmt(["-" * w for w in widths]))
    for r in rows:
        print(fmt(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
