#!/usr/bin/env python3
"""q-d29 calibration: "chunker-agnostic primary key rule for qrels"

Canonical answer at pinned corpus SHA (openhands-ext-v1 @ a9d5bd6):

  openhands-ext-v1/adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md
    L145 (sub-decision 4): "Primary key rule (P1, chunker-agnostic): primary
        is at (repo, source_file_path, line_range) tuple. A retrieved chunk
        counts as MRR@1 hit if chunk.line_span ∩ gold.line_range ≠ ∅. Same
        qrel file for both H1 and H2 sub-cells within a block."
    L201 (Rationale for P1): "P1 primary key rule (line-range, chunker-
        agnostic) because using per-chunker primaries would require labeling
        twice and would blur chunker vs embedder attribution."
    L23, L40: amendment mentions "chunk_id primary key" is unchanged

Pool coverage verified:
  - L134-151 covers L145 (all 3 Qwens retrieved, nomic missed)
  - L136-144 in neighborhood (all 4 candidates)
  - L150-163 covers post-L145 (nomic only)
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from _calibration_driver import emit_qrels


PRIMARIES_G3 = [
    ("openhands-ext-v1", "adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md",
     (140, 150), "Sub-decision 4 §Primary key rule (P1, chunker-agnostic) — exact answer"),
    ("openhands-ext-v1", "adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md",
     (198, 205), "Rationale §P1 primary key rule — explains why chunker-agnostic"),
]

SECONDARIES_G2 = [
    ("openhands-ext-v1", "adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md",
     (139, 149), "Sub-decision 4 Gold labeling protocol — direct context of P1"),
    ("openhands-ext-v1", "adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md",
     (20, 25), "Amendment mention of chunk_id primary key non-change"),
    ("openhands-ext-v1", "adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md",
     (38, 42), "Amendment mention of primary key unchanged"),
    ("openhands-ext-v1", "BUILD_LOG.md",
     (1, 5000), "BUILD_LOG records the P1 chunker-agnostic primary key from step 6a — supports P1 provenance across implementation history"),
]

MARGINALS_G1 = [
    ("openhands-ext-v1", "adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md",
     (120, 138), "Sub-decision 3 Rubric — sets up why P1 matters (chunker attribution)"),
    ("openhands-ext-v1", "adrs/ADR-0016-medium-tier-scoring-rubric-hybrid.md",
     (1, 5000), "Earlier rubric doc that P1 is contrasted against — background only"),
]


if __name__ == "__main__":
    path, counts, unans = emit_qrels(
        qid="q-d29",
        primaries_g3=PRIMARIES_G3,
        secondaries_g2=SECONDARIES_G2,
        marginals_g1=MARGINALS_G1,
        notes=(
            "P1 primary key rule at ADR-0030 L145 (Sub-decision 4). "
            "Rationale at L201. Multiple pool spans cover both. All 3 Qwens "
            "retrieved L134-151 which contains L145. Answerable."
        ),
    )
    print(f"wrote {path}")
    print(f"grades: {counts}")
    print(f"unanswerable: {unans}")
    assert not unans, "expected answerable"
