#!/usr/bin/env python3
"""q-d18 calibration: "SESSION_HANDOFF exact next action for embedder gate-4"

Canonical answer at pinned corpus SHA (openhands-ext-v1 @ a9d5bd6):

  openhands-ext-v1/SESSION_HANDOFF.md L26-35:
    "## Exact next action
     1. User commits + pushes the pool artifact...
     2. Then step 6c: hand pool.jsonl + rubric G2 section to Perplexity-Max
        for labeling..."

The file header at L1-2 shows it's the Kosmos Session Handoff dated
2026-08-11 15:50 EDT for Phase 0.4 gate-4 (embedder Full-tier re-eval).
"Current build-sequencing position" L3-7 confirms embedder gate-4 context.

Pool coverage verified: all 3 Qwens + nomic retrieved L1-38 and L22-30
which straddle the Exact next action section. L31-45 is retrieved by e08b
and nomic (covers the tail of item 1 + item 2). L67-81 also retrieved by
all 4 (likely a longer span variant covering same section).

The query asks for the EXACT NEXT ACTION, so the g3 primary is L26-35
specifically. Broader spans covering the file's build-sequencing and
completed-work sections are g2 (context) or g1 (background).
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from _calibration_driver import emit_qrels


PRIMARIES_G3 = [
    ("openhands-ext-v1", "SESSION_HANDOFF.md",
     (26, 35), "Exact next action section: 2-step next action for embedder gate-4"),
]

SECONDARIES_G2 = [
    ("openhands-ext-v1", "SESSION_HANDOFF.md",
     (1, 8), "Header + build-sequencing position confirming Phase 0.4 gate-4 embedder context"),
    ("openhands-ext-v1", "SESSION_HANDOFF.md",
     (16, 26), "Remaining before DoD: lists step 6c/6d/7 that the next-action initiates"),
    ("openhands-ext-v1", "SESSION_HANDOFF.md",
     (23, 25), "Open questions confirming no blockers on the next action"),
]

MARGINALS_G1 = [
    ("openhands-ext-v1", "SESSION_HANDOFF.md",
     (8, 16), "Completed this session — historical context for what the next action follows"),
    ("openhands-ext-v1", "BUILD_LOG.md",
     (1, 5000), "BUILD_LOG cross-refs step 6b completion that the next action pushes to git"),
    ("openhands-ext-v1", "adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md",
     (1, 5000), "ADR-0030 defines the phase whose next action is in the handoff"),
]


if __name__ == "__main__":
    path, counts, unans = emit_qrels(
        qid="q-d18",
        primaries_g3=PRIMARIES_G3,
        secondaries_g2=SECONDARIES_G2,
        marginals_g1=MARGINALS_G1,
        notes=(
            "Exact next action at SESSION_HANDOFF.md L26-35. All 4 candidates "
            "retrieved L1-38 which contains it. Answerable."
        ),
    )
    print(f"wrote {path}")
    print(f"grades: {counts}")
    print(f"unanswerable: {unans}")
    assert not unans, "expected answerable"
