#!/usr/bin/env python3
"""Calibration-mode qrel emitter.

Given a query_id and a manifest of (repo, file, line_range, grade, role, note)
canonical spans, iterates the pool rows for that qid and emits qrels via
line-range-overlap-≥0.5 matching. All non-matching chunks graded 0.

Grade-0-default per user directive 2026-08-11.
Rubric G2 line 8: unanswerable_at_pinned_snapshot=true iff no g3 primary.

Usage in per-query emitter modules:

    from _calibration_driver import emit_qrels
    emit_qrels(
        qid="q-c02",
        primaries_g3=[
            ("Kosmos", "adapters/llm/llama_swap/adapter.py", (1, 250), "..."),
        ],
        secondaries_g2=[...],
        marginals_g1=[...],
    )
"""
import json
from pathlib import Path

BASE = Path("/tmp/oh-ext/bench/gold/embedder-full-multi-block")
SESSIONS = BASE / "labeling_sessions"
LABELS = BASE / "labels"


def _overlap_ratio(a, b):
    a0, a1 = a
    b0, b1 = b
    inter = max(0, min(a1, b1) - max(a0, b0) + 1)
    if inter == 0:
        return 0.0
    smaller = min(a1 - a0 + 1, b1 - b0 + 1)
    return inter / smaller


def _find_grade(row, g3, g2, g1):
    repo = row["repo"]
    fp = row["source_file_path"]
    lr = tuple(row["line_range"])
    for entries, grade, role in [
        (g3, 3, "primary"),
        (g2, 2, "secondary"),
        (g1, 1, "secondary"),
    ]:
        for r, f, span, note in entries:
            if r == repo and f == fp:
                if _overlap_ratio(lr, span) >= 0.5:
                    return grade, role, note
    return 0, "secondary", ""


def _collect_pool_rows(qid):
    rows = []
    query_text = None
    block = None
    for sess in sorted(SESSIONS.glob("*.jsonl")):
        with sess.open() as f:
            for line in f:
                r = json.loads(line)
                if r.get("qid") != qid:
                    continue
                if r.get("$type") == "pool_row":
                    rows.append(r)
                    if query_text is None:
                        query_text = r["query_text"]
                        block = r["block"]
    return rows, query_text, block


def emit_qrels(
    *,
    qid,
    primaries_g3=None,
    secondaries_g2=None,
    marginals_g1=None,
    labeling_mode="calibration",
    notes="",
    session_id_suffix="",
):
    """Emit qrels_<qid>.jsonl for one query.

    Returns (out_path, grade_counts, unanswerable).
    """
    primaries_g3 = primaries_g3 or []
    secondaries_g2 = secondaries_g2 or []
    marginals_g1 = marginals_g1 or []

    rows, query_text, block = _collect_pool_rows(qid)
    assert rows, f"no pool rows for {qid}"

    grade_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    out_rows = []
    for r in rows:
        grade, role, note = _find_grade(
            r, primaries_g3, secondaries_g2, marginals_g1,
        )
        grade_counts[grade] += 1
        out_rows.append({
            "$type": "qrel",
            "block": block,
            "qid": qid,
            "chunk_id": r["chunk_id"],
            "repo": r["repo"],
            "source_file_path": r["source_file_path"],
            "line_range": r["line_range"],
            "grade": grade,
            "role": role,
            "labeler_note": note,
        })

    unanswerable = grade_counts[3] == 0
    session_id = f"{qid}_{labeling_mode}{session_id_suffix}"
    summary = {
        "$type": "session_summary",
        "session_id": session_id,
        "qid": qid,
        "query_text": query_text,
        "labels_emitted": len(out_rows),
        "grade_counts": grade_counts,
        "unanswerable_at_pinned_snapshot": unanswerable,
        "labeling_mode": labeling_mode,
        "notes": notes,
    }

    out_path = LABELS / f"qrels_{qid}.jsonl"
    LABELS.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for row in out_rows:
            f.write(json.dumps(row) + "\n")
        f.write(json.dumps(summary) + "\n")

    return out_path, grade_counts, unanswerable
