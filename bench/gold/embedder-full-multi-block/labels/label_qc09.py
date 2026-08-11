#!/usr/bin/env python3
"""q-c09 calibration: "structure-aware chunker per-symbol code splitter"

FINDING: unanswerable_at_pinned_snapshot=true — canonical file MISSING FROM POOL.

The canonical answer to this query exists at the pinned corpus SHA
(openhands-ext-v1 @ a9d5bd6):

    openhands-ext-v1/bench/runner/probes_embedder_multi_block.py:
      L111-135  _PY_SYMBOL_RE + _split_by_symbol_python  (per-symbol code splitter)
      L138-148  _split_by_heading_md                     (per-heading docs splitter)
      L151-194  _chunk_h2_structure_aware                (structure-aware chunker)
      L197-202  _chunk_file dispatcher

However, POOL COVERAGE FOR THIS FILE IS ZERO ACROSS ALL 4 CANDIDATES
(3 Qwens + nomic) for q-c09. Verified by scanning all 4 labeling_sessions
files: no pool row for probes_embedder_multi_block.py or
run_embedder_full_multi_block.py.

This is a legitimate retrieval failure signal: NONE of the embedders
retrieved the canonical file in their top-20. The pool for q-c09 is
composed entirely of noise chunks (top file: probes.py L881-938 which is
_probe_coder_fallback code — unrelated to chunking).

Per rubric G2 line 8: no chunk in the pool can be graded 3 -> mark
unanswerable_at_pinned_snapshot=true. Rubric line "The canonical file
existing in the corpus is not the same as pool coverage" (G2 note): if the
pool is missing the answer, the query is unanswerable AT THE POOL, not at
the corpus.

Semantic implication: q-c09 tests whether an embedder can locate a code
implementation from a semantic description ("structure-aware chunker per-
symbol code splitter"). The correct file has an explicit docstring calling
out "H2: structure-aware" and function name _split_by_symbol_python. All 4
candidates failed to retrieve it. This is data-worthy — it says the
embedders under test are weak on code-search-by-behavior queries — but it
cannot be used to RANK them since they all failed equally.

Effect on scoring: q-c09 contributes nothing to macro because all metrics
= 0 for all candidates when unanswerable_at_pinned_snapshot=true (per
rubric). It functions as a null-signal query.
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from _calibration_driver import emit_qrels


if __name__ == "__main__":
    path, counts, unans = emit_qrels(
        qid="q-c09",
        primaries_g3=[],
        secondaries_g2=[],
        marginals_g1=[],
        notes=(
            "UNANSWERABLE at pool. Canonical file exists at "
            "openhands-ext-v1@a9d5bd6:bench/runner/probes_embedder_multi_block.py "
            "L111-194 (H2 structure-aware chunker + per-symbol code splitter). "
            "Pool has ZERO rows for that file across all 4 candidates. "
            "Signal: all embedders failed this code-search-by-behavior query "
            "equally, so q-c09 provides no discriminative signal but IS a "
            "legitimate benchmark failure worth reporting."
        ),
    )
    print(f"wrote {path}")
    print(f"grades: {counts}")
    print(f"unanswerable: {unans}")
    assert unans, "expected unanswerable"
