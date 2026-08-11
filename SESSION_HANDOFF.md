# Kosmos Session Handoff — 2026-08-11 15:50 EDT

## Current build-sequencing position
- **Project:** OpenHands-Ext v1 (this Space)
- **Stage / phase:** Phase 0.4 gate-4 (Full-tier embedder re-eval)
- **Component:** ADR-0030 fixture DoD, step 6b→6c transition

## Completed this session
- ADR-0030 amended twice: SCOPE-RESTORATION + PLACEMENT-SPLIT (14:55 EDT) supersedes prior SCOPE-REDUCTION; CROSS-FAMILY SANITY-CHECK (15:00 EDT) adds nomic-embed-code as 4th candidate
- ADR-0030b filed (Proposed) for co-residency viability methodology
- llama.cpp CUDA build (`~/llama.cpp/build-cuda/bin/llama-server`, CUDA 13.0, SM_120a Blackwell)
- 16-cell GPU cold bench executed one-at-a-time (~38 minutes total, 15:07-15:46 EDT)
- Pool union generated: `bench/gold/embedder-full-multi-block/pool.jsonl` (3324 rows)
- Diversity verified: nomic contributes 15-20% unique chunks; Qwen family clusters together with higher internal Jaccard than cross-family

## Remaining before current Definition of Done
- **Step 6c — Perplexity-Max qrels labeling** (GL2, 2-4 sessions). Labelers grade all 3324 pool rows 0-3 per the rubric's embedded G2 instructions. Produces `bench/gold/embedder-full-multi-block/qrels.jsonl` + `QRELS.locked.sha256`.
- **Step 6d — scoring pass.** Runner reads locked qrels, computes composite per cell, evaluates reversal criteria (Qwen 3-candidate scope only; nomic reported for observability), emits verdict artifact.
- **Step 7 — ADR-0031 verdict.** CONFIRM 4B / FLIP 8B / FLIP 0.6B / INTERMEDIATE. Nomic composite reported alongside as sanity check.
- **ADR-0030 Ratification** on step 7 filing (fixture lock-in complete).
- **ADR-0030b execution** — co-residency contention testing on surviving candidates (post-verdict).

## Open questions / awaiting user answer
- None. Pool artifact ready for step 6c whenever user resumes.

## Exact next action
1. User commits + pushes the pool artifact (agent cannot — file was generated on Colossus):
   ```bash
   cd ~/dev/openhands-ext-v1
   git add bench/gold/embedder-full-multi-block/pool.jsonl
   git commit -m "Phase 0.4 gate-4 step 6b: pool union of top-20 across 16 cells (3324 rows)"
   git push origin main
   ```
2. Then step 6c: hand pool.jsonl + rubric G2 section to Perplexity-Max for labeling. Agent will prep the labeling prompt when user is ready.
