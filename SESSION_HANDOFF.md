# Kosmos Session Handoff — 2026-08-11 13:08 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.4 gate-4 OPEN (ADR-0030 Proposed). Awaits fixture lock-in before probes.
- **Plugin / kernel component:** bench harness · embedder Full-tier re-eval
- **Port(s) in progress:** none yet (runner extension `probe_embedder_full_multi_block` is next hand-build)

## Verdict

Phase 0.3 CLOSED (ADR-0029: CONFIRM AWQ coder; ADR-0025: CONFIRM 27B-Q6_K planner).

Phase 0.4 OPEN (ADR-0030 Proposed): three-way embedder Full-tier re-eval.
- Incumbent: `qwen3-embedding-4B-Q8_0` llama.cpp CPU (3.99 GiB)
- Challenger upsize: `qwen3-embedding-8B-Q6_K` llama.cpp CPU (5.79 GiB, HF-verified)
- Challenger downsize: `qwen3-embedding-0.6B-Q8_0` llama.cpp CPU (0.60 GiB)

All three on CPU (co-residency contract inherited from ADR-0017 amend #3; coder+planner saturate 32 GB VRAM).

Bench shape: 3 candidates × 2 chunkers × 2 blocks = **12 cells**, 40 queries total, top-20 retrieval, composite of nDCG@10 + Recall@10 + MRR@10 + Recall@1. Pre-locked V3+W3 reversal criteria.

## Completed this session

- ADR-0028 F05 amendment (12:17 EDT)
- Full-tier runner verification (12:24 EDT)
- Both Full-tier coder probes executed with real SDK+Docker path (commit 7a03d49)
- ADR-0029 filed (Ratified · CONFIRM AWQ) with per-task scoring rationale (commit 3da7033)
- Phase 0.3 gate-3 CLOSED
- Phase 0.4 gate-4 OPENED with ADR-0030 (Proposed) + candidate pool + task-set + pre-locked reversal criteria

## Remaining before current Definition of Done (gate-4)

Steps 3-6 BLOCK progression. Do not run any embedder cell until all four commit:

- **Step 3:** commit `bench/corpus/embedder-full-multi-block/MANIFEST.json` with pinned repo SHAs (openhands-ext-v1, Kosmos, Rigpa-LMS) and file lists frozen for both blocks
- **Step 4:** commit `bench/tasks/embedder-full-multi-block.queries.json` with 40 queries authored blind (20 code + 20 docs)
- **Step 5:** commit `bench/rubrics/full-embedder-scored.json` with `post_hoc_edit_locked=true`
- **Step 6:** commit `bench/gold/embedder-full-multi-block/qrels.jsonl` (labeled by Perplexity-Max over pooled union-of-top-20) + `QRELS.locked.sha256`

Steps 7-9 come after fixture lock-in:

- **Step 7:** extend `bench/runner/probes.py` with `probe_embedder_full_multi_block`; run all 12 cells
- **Step 8:** compute composite + component metrics per cell; per-block macros
- **Step 9:** apply reversal criteria mechanically; file ADR-0031 verdict

## Open questions / awaiting user answer

1. **Kosmos snapshot commit SHA** — I don't have direct access to `~/dev/kosmos`. When you're ready for step 3 (corpus manifest lock-in), give me the Kosmos HEAD SHA to pin. Same for Rigpa-LMS.
2. **Query authoring cadence** — 40 queries authored blind is a session on its own. Do you want me to draft 40 candidate queries for your review, or draft 60-80 and cut to 40? (More drafting = better coverage, more of my session budget.)
3. **Gold labeling session budget** — pooled labeling is ~600-2400 judgments. Do this in one long session, or spread across 2-4 sessions? (I recommend 2-4.)

## Exact next action

If you want to proceed with fixture lock-in immediately, give me:

```bash
# From ~/dev on Colossus:
cd ~/dev/openhands-ext-v1 && git pull --ff-only origin main
cd ~/dev/kosmos && git rev-parse HEAD
cd ~/dev/rigpa-lms && git rev-parse HEAD
# Also confirm openhands-ext-v1 HEAD SHA (post-pull) is the one to pin
git -C ~/dev/openhands-ext-v1 rev-parse HEAD
```

Paste the three SHAs and I'll build the corpus manifest.

If you want to hold gate-4 here and open a fresh session for fixture lock-in, that's fine — this handoff captures the entry point exactly.

## Key file references (Phase 0.4)

- `adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md` — Proposed opener (V3+W3 criteria)
- `bench/candidates/embedder-full-pool.json` — three-way pool
- `bench/tasks/embedder-full-multi-block.json` — task-set spec (queries TBD)
- `bench/gold/embedder-full-multi-block/` — qrels destination (empty)
- `bench/scoring/full-embedder/` — runs destination (empty)

## Key file references (Phase 0.3 closed)

- `adrs/ADR-0029-phase-0-3-gate-3-coder-verdict-confirm-awq.md`
- `adrs/ADR-0025-planner-migration-probe-verdict-confirm-adr-0023.md`
- `bench/scoring/full-coder/SCORING_20260811.md`
