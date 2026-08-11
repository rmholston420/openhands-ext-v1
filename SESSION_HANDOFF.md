# Kosmos Session Handoff — 2026-08-11 16:37 EDT

## Current build-sequencing position
- **Project:** OpenHands-Ext v1 (this Space)
- **Stage / phase:** Phase 0.4 gate-4 (Full-tier embedder re-eval)
- **Component:** ADR-0030 fixture DoD, step 6d calibration COMPLETE; verdict decision pending

## Completed this session
- q-c01 real slice labeled (15 g3 / 3 g2 / 4 g1 / 81 g0)
- q-c02 calibration retained (driver validator)
- q-c09, q-c32 labeled UNANSWERABLE at pinned SHA (all grade 0)
- q-d29 (ADR-0030 L145 P1 rule): 2 g3 / 12 g2 / 8 g1 / 100 g0
- q-c40 (MemoryPort link_entities + TemporalIndex.record_event): 6 g3 / 6 g2 / 10 g1 / 86 g0
- q-d18 (SESSION_HANDOFF L26-35 exact next action): 3 g3 / 2 g2 / 20 g1 / 79 g0
- Combined `qrels.jsonl` locked (437 rows, SHA256 `f7137c7bebbf9b10da14091488c185921f4cda2e071880c838eefff4aaca48f8`)
- Offline scorer authored (`bench/scoring/embedder-full-multi-block-calibration/score_offline.py`) — reads step-6b per-cell top-20 files; no embedder re-run needed
- 4-query calibration scored on Colossus (numbers below)

## Calibration results — DO NOT interpret as V3/W3 verdict (N=4)

| cell | nDCG@10 | R@10 | MRR@10 | R@1 | composite |
|---|---|---|---|---|---|
| e006b_q8_cpu (0.6B Q8) | 0.126 | 0.051 | 0.494 | 0.017 | **16.41** |
| e04b_q8_cpu (4B Q8 incumbent) | 0.254 | 0.142 | 0.750 | 0.028 | **29.11** |
| e08b_q6k_cpu (8B Q6_K upsize) | 0.321 | 0.206 | 0.685 | 0.023 | **32.04** |
| enomicc_q6k_gpu (nomic · informational) | 0.283 | 0.126 | 0.702 | 0.028 | **28.94** |

Facts (not verdict):
- 8B leads on 3 of 4 metrics
- 0.6B has 1 all-zero sub-cell (H1 docs)
- nomic between 4B and 8B on composite
- Recall@1 near-zero on all cells at this pool depth

## Remaining before Definition of Done (ADR-0030 fixture)
- Decide whether to expand from 4 → 40 queries for a defensible V3/W3 verdict, or accept calibration + defer
- Step 7 ADR-0031 verdict decision (blocked on above)
- ADR-0030 ratification (blocked on step 7)

## Open questions / awaiting user answer
- **Expand to full 20 queries/block labeling** (~4-8 more labeling sessions) for defensible verdict?
- **Or accept 4-query calibration signal** as-is and defer full re-eval? Signal suggests 8B has an edge but N=4 is below the rubric's stability threshold.
- **Any post-hoc rubric changes needed?** e.g. if Recall@1 is consistently near-zero across all cells, is it discriminative enough to keep in composite (currently 15% weight)? Note: post_hoc_edit_locked=true per ADR-0016 + ADR-0022, so this would require a spec amendment ADR, NOT a silent rubric edit.

## Exact next action

Wait for user decision on scope. Do NOT proceed to ADR-0031 verdict at N=4.

## Reminders (binding)
- Rubric + gold `post_hoc_edit_locked=true` per ADR-0016 + ADR-0022
- 4-query calibration ≠ V3/W3 verdict; 20 queries/block needed for stable macro
- Nomic-embed-code informational only (cross-family sanity check, out of Qwen reversal scope)
