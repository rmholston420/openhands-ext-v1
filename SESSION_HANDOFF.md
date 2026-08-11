# OpenHands-Ext v1 Session Handoff — 2026-08-11 05:52 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 (Medium tier) — embedder task set authored; ready for first embedder-medium bench run.
- **Plugin / kernel component:** bench harness (Medium-tier embedder path complete; planner/coder task sets pending).
- **Port(s) in progress:** none.

## Completed this session
- ADR-0014 filed (Ratified); coder-fast pool reinstated 2→4 cells. Pushed 66249e1.
- ADR-0015 filed (Proposed) + probe runs. **Ratified · Confirmed** — thinker-2507-awq unfit for planner Medium. Pushed dbfa0fd.
- ADR-0016 filed (Ratified) — Medium-tier scoring rubric = hybrid (embedder programmatic; planner/coder Perplexity-gold). `bench/rubrics/medium-scored.json` frozen. Pushed 03efcee.
- **embedder-medium task set authored (both arms):**
  - `bench/tasks/embedder-medium-beir-scidocs.json` — portability arm (BEIR SciDocs config).
  - `bench/tasks/embedder-medium-domain-openhands-ext.json` — domain arm (42 corpus chunks + 10 queries + 26 qrels rows, hand-labeled).
- **`bench/runner/probes_retrieval.py`** — new module implementing `probe_embedder_retrieval` (batched embed, cosine ranking, recall@k / MRR / nDCG@k, macro-average summary).
- **`bench/runner/main.py`** extended — additive dispatch by task-shape (`corpus` + `qrels` → retrieval probe; else Fast-tier probe).
- **`scripts/materialize-beir-scidocs-subset.py`** — one-shot BEIR materializer (deterministic SHA-256 hash-rank sampling).
- **`bench/tasks/README.md`** extended with Medium-tier embedder shape section.

## Locked pool state (Fast tier)
- **Coder-Fast:** 4 cells.
- **Planner-Fast:** 2 cells (llama.cpp only).
- **Embedder-Fast:** 6 cells (0.6B ×3 + 4B ×3).

## Locked pool state (Medium tier)
- **Embedder-Medium:** 6 cells (same as Fast pool — all survive R1-R4 at Fast tier per ADR-0007).
- **Planner-Medium (pre-authoring):** 2 cells expected — llama.cpp survivors only. thinker-2507-awq excluded (ADR-0015).
- **Coder-Medium:** to be authored. thinker-2507-awq retains eligibility (dual-role per ADR-0012).
- **Rubric:** locked at `bench/rubrics/medium-scored.json` per ADR-0016.

## Phase 0.2 authoring order (confirmed by user)
1. **embedder-medium** ✅ authored (this session)
2. planner-medium — next
3. coder-medium

## Remaining before current Definition of Done
- Install `beir` on Colossus: `pip install beir` (or add to the harness venv requirements).
- Run BEIR materializer once: `python3 scripts/materialize-beir-scidocs-subset.py`. Produces `bench/tasks/embedder-medium-beir-scidocs-materialized.json`.
- Run embedder-medium bench (domain arm + BEIR arm) against the 6-cell embedder-fast pool.
- Record results, apply ADR-0016 scoring, produce embedder-medium tier verdict ADR.
- Then author planner-medium task set, then coder-medium.

## Open questions / awaiting user answer
- None right now; embedder-medium authoring is complete.
- User may want to review the domain-arm query list and qrels labels before the first materialized run.

## Exact next action
- On Colossus: `pip install beir` (if not already present), then `python3 scripts/materialize-beir-scidocs-subset.py` (one-time), then run the embedder-medium benchmark. Report per-cell scores back for tier-verdict ADR authoring.
