#!/usr/bin/env python3
"""Emit qrels_q-c01.jsonl for calibration slice.

Grading strategy (documented per rubric G2):
- Query: "how does the vLLM AWQ coder endpoint parse tool calls"
- Query decomposition: vLLM (server), AWQ (quant format), coder endpoint
  (role), parse tool calls (extract structured tool_calls[] from response)

Grade-3 primaries (canonical): 4 spans in openhands-ext-v1
- bench/runner/server.py lines 302-512 (VLLMServer.ROLE_FLAGS
  --tool-call-parser hermes + docstring 316-350 explaining
  hermes-vs-qwen3_coder XML/JSON choice)
- bench/runner/candidates.py lines 31-93 (ExpandedCandidate dataclass with
  tool_call_parser / reasoning_parser override fields)
- bench/runner/probes.py lines 918-1029 (_probe_coder_fallback: the
  actual client parsing of msg['tool_calls'] from /v1/chat/completions)
- bench/runner/main.py lines 400-477 (_make_server per-cell parser
  passthrough via extra_flags)

Grade 2 (relevant, missing detail):
- bench/schema/run.py lines 43-133 (Runtime.VLLM, Format.AWQ,
  ToolCallBehavior enum/dataclass — schema for the phenomenon)
- probes.py lines 97-124 (TaskResult with tool_attempts/successes/etc
  fields — result accounting)

Grade 1 (marginal):
- probes.py 285-370 (probe_coder entry + _probe_coder_sdk — SDK path uses
  tools but parsing is inside SDK, not visible here)
- main.py 69-150 (imports + PORTS assignments — mentions VLLMServer + coder
  but boilerplate)
- Kosmos ops/benchmarks/adr_010/harness/arex.py 42-100 (XML tool_call
  regex parsing — wrong protocol/model but genuine tool-call parse
  discussion)

Grade 0: all remaining chunks (per user directive: grade-0-default,
per rubric line "If no chunk is relevant → grade 0")

Rubric G2 line 8: query has ≥1 grade-3 primary → NOT unanswerable.
"""
import json
from pathlib import Path

SESSION = Path("/tmp/oh-ext/bench/gold/embedder-full-multi-block/"
               "labeling_sessions/s01_code.jsonl")
OUT = Path("/tmp/oh-ext/bench/gold/embedder-full-multi-block/labels/"
           "qrels_q-c01.jsonl")


def overlap_ratio(a, b):
    """Line-range overlap ratio (intersection / smaller range).
    Matches rubric line_range_overlap_threshold=0.5 semantics."""
    a0, a1 = a
    b0, b1 = b
    inter = max(0, min(a1, b1) - max(a0, b0) + 1)
    if inter == 0:
        return 0.0
    smaller = min(a1 - a0 + 1, b1 - b0 + 1)
    return inter / smaller


# (repo, file_path, line_range) → (grade, role, note)
PRIMARIES_G3 = [
    ("openhands-ext-v1", "bench/runner/server.py", (302, 512),
     "ROLE_FLAGS with --tool-call-parser hermes + docstring 316-350 "
     "documenting hermes-vs-qwen3_coder XML/JSON parser choice for coder role"),
    ("openhands-ext-v1", "bench/runner/candidates.py", (31, 93),
     "ExpandedCandidate dataclass: tool_call_parser + reasoning_parser "
     "override fields per ADR-0011"),
    ("openhands-ext-v1", "bench/runner/probes.py", (918, 1029),
     "_probe_coder_fallback: sends /v1/chat/completions with tools + "
     "tool_choice=auto, reads msg['tool_calls'], classifies "
     "malformed/missing/wrong — the client-side parse"),
    ("openhands-ext-v1", "bench/runner/main.py", (400, 477),
     "_make_server per-cell --tool-call-parser + --reasoning-parser "
     "extra_flags passthrough (ADR-0011 amend 2)"),
]

GRADE_2 = [
    ("openhands-ext-v1", "bench/schema/run.py", (43, 133),
     "Enums Runtime.VLLM, Format.AWQ + ToolCallBehavior dataclass — schema "
     "for the domain but no parsing logic"),
    ("openhands-ext-v1", "bench/runner/probes.py", (97, 124),
     "TaskResult tool-call accounting fields (tool_attempts/successes/"
     "malformed/missing/wrong/argerrors) — records parse outcomes"),
]

GRADE_1 = [
    ("openhands-ext-v1", "bench/runner/probes.py", (285, 370),
     "probe_coder dispatcher + _probe_coder_sdk header — SDK-driven path "
     "where parsing happens inside openhands.sdk, not visible in this span"),
    ("openhands-ext-v1", "bench/runner/main.py", (69, 150),
     "Imports of VLLMServer + PORTS assignments for vllm/coder — infra "
     "boilerplate mentioning entities"),
    ("Kosmos", "ops/benchmarks/adr_010/harness/arex.py", (42, 100),
     "XML <tool_call> regex parser for AREX-Turbo — wrong protocol "
     "(XML not OpenAI tool_calls) and wrong runtime (not vLLM AWQ coder), "
     "but is a tool-call parser"),
]


def find_grade(row, spans_g3, spans_g2, spans_g1):
    """Match row against (repo, file, line_range) spans by overlap."""
    repo = row["repo"]
    fp = row["source_file_path"]
    lr = tuple(row["line_range"])
    for entries, grade, role in [
        (spans_g3, 3, "primary"),
        (spans_g2, 2, "secondary"),
        (spans_g1, 1, "secondary"),
    ]:
        for r, f, span, note in entries:
            if r == repo and f == fp:
                if overlap_ratio(lr, span) >= 0.5:
                    return grade, role, note
    return 0, "secondary", ""


def main():
    rows = []
    with SESSION.open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("qid") != "q-c01":
                continue
            if r.get("$type") != "pool_row":
                continue
            rows.append(r)

    print(f"pool rows for q-c01: {len(rows)}")

    out_rows = []
    grade_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for r in rows:
        grade, role, note = find_grade(
            r, PRIMARIES_G3, GRADE_2, GRADE_1,
        )
        grade_counts[grade] += 1
        out_rows.append({
            "$type": "qrel",
            "block": "code",
            "qid": "q-c01",
            "chunk_id": r["chunk_id"],
            "repo": r["repo"],
            "source_file_path": r["source_file_path"],
            "line_range": r["line_range"],
            "grade": grade,
            "role": role,
            "labeler_note": note,
        })

    # Session summary row
    unanswerable = grade_counts[3] == 0
    summary = {
        "$type": "session_summary",
        "session_id": "s01_code_qc01_calibration",
        "qid": "q-c01",
        "labels_emitted": len(out_rows),
        "grade_counts": grade_counts,
        "unanswerable_at_pinned_snapshot": unanswerable,
        "drift_check_passed": None,
        "drift_deltas": None,
        "labeling_mode": "calibration_slice_grade0_default",
        "notes": (
            "Calibration slice: read openhands-ext-v1 primaries in full; "
            "spot-read Kosmos + Rigpa-LMS files; graded remaining chunks "
            "as grade 0 by directive. 4 grade-3 primaries identified in "
            "openhands-ext-v1 covering both server-side parser config and "
            "client-side response parsing."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for row in out_rows:
            f.write(json.dumps(row) + "\n")
        f.write(json.dumps(summary) + "\n")

    print(f"wrote {OUT}")
    print(f"grade distribution: {grade_counts}")
    print(f"unanswerable_at_pinned_snapshot: {unanswerable}")


if __name__ == "__main__":
    main()
