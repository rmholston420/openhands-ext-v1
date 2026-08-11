#!/usr/bin/env python3
"""q-c32 calibration: "co-residency contract stopping coder before embedder run"

FINDING: unanswerable_at_pinned_snapshot=true for the code block.

The co-residency contract is defined and enforced by three artifact classes:
1. Task JSON (bench/tasks/embedder-full-multi-block.json co_residency_contract
   + runtime_env_note fields)
2. Shell scripts (scripts/stop-large-model.sh, scripts/serve-{coder,planner}.sh)
3. ADR markdown (ADR-0017 amend #3, ADR-0022 Decision 4, ADR-0030 §co-residency)

NONE of these appear in the code corpus, which is restricted to *.py files.
Verified: grep -rn 'co.residency|systemctl stop|docker stop|stop.*coder' across
openhands-ext-v1/bench/runner/*.py, Kosmos/, Rigpa-LMS/ → 0 hits.

Per rubric G2 line 8: "Every query MUST have >= 1 grade-3 primary; if none,
mark unanswerable_at_pinned_snapshot=true."

All 117 pool chunks grade 0. This is a genuine signal-worthy finding: the
embedders retrieved chunks for a query that has no code-block answer at the
pinned snapshot. Retrieval quality on q-c32 depends entirely on how well the
embedder recognizes semantic non-match — a candidate that ranks anything highly
here is producing noise, not signal.
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from _calibration_driver import emit_qrels


if __name__ == "__main__":
    # No primaries, no secondaries, no marginals — all chunks grade 0.
    path, counts, unans = emit_qrels(
        qid="q-c32",
        primaries_g3=[],
        secondaries_g2=[],
        marginals_g1=[],
        notes=(
            "UNANSWERABLE at pinned snapshot for code block. Co-residency "
            "contract lives in task JSON + shell scripts + ADR markdown, "
            "none of which are in the *.py code corpus. Verified by "
            "grep across all 3 repos. Rubric G2 line 8 satisfied: "
            "unanswerable_at_pinned_snapshot=true. All 117 chunks grade 0."
        ),
    )
    print(f"wrote {path}")
    print(f"grades: {counts}")
    print(f"unanswerable: {unans}")
    assert unans, "expected unanswerable"
