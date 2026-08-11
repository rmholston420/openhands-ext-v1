# OpenHands-Ext v1 Session Handoff — 2026-08-11 05:55 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 (Medium tier) — embedder pipeline end-to-end ready. Awaiting bench execution on Colossus.
- **Plugin / kernel component:** bench harness (embedder-medium done; planner-medium + coder-medium pending).
- **Port(s) in progress:** none.

## Completed this session
- ADR-0014 (Ratified) — coder-fast pool reinstated 2→4. Pushed 66249e1.
- ADR-0015 (Ratified · Confirmed) — thinker-2507-awq unfit for planner Medium. Pushed dbfa0fd.
- ADR-0016 (Ratified) — Medium-tier hybrid scoring rubric + `bench/rubrics/medium-scored.json` frozen. Pushed 03efcee.
- embedder-medium task set (both arms) + retrieval probe + BEIR materializer. Pushed 8e17bd2.
- **`scripts/aggregate-embedder-medium-verdict.py`** — verdict aggregator authored. Joins per-cell portability + domain arm summaries, computes cross-arm nDCG@10 macro, applies ADR-0016 tiebreak, writes tier verdict JSON.
- **BEIR SciDocs materialized on Colossus:** 5000 docs, 100 queries, 603 qrels rows in `bench/tasks/embedder-medium-beir-scidocs-materialized.json` (derived artifact, not tracked in git).

## Locked pool state
- **Coder-Fast:** 4 cells.
- **Planner-Fast:** 2 cells (llama.cpp only).
- **Embedder-Fast:** 6 cells (0.6B ×3 + 4B ×3).
- **Embedder-Medium:** 6 cells (Fast pool survives R1-R4).
- **Planner-Medium (pre-authoring):** 2 cells expected — llama.cpp survivors. thinker-2507-awq excluded per ADR-0015.
- **Coder-Medium:** to be authored.

## Phase 0.2 authoring order (confirmed by user)
1. **embedder-medium** ✅ authored + materialized (this session)
2. planner-medium — next after embedder-medium bench results
3. coder-medium

## Remaining before current Definition of Done
- Run embedder-medium bench on Colossus, both arms × 6 cells = 12 probe runs total. Two invocations of the tier runner per arm.
- Run aggregator: `python3 scripts/aggregate-embedder-medium-verdict.py`.
- Author verdict ADR (ADR-0017 slot open) citing the top-ranked cell(s) per arm and cross-arm.
- Then author planner-medium task set → run bench → verdict ADR.
- Then author coder-medium task set → run bench → verdict ADR.

## Open questions / awaiting user answer
- None right now. Pipeline is ready to run.

## Exact next action

On Colossus, run the two-arm bench:

```bash
cd ~/dev/openhands-ext-v1
git pull --ff-only

# Domain arm — 6 cells
python3 scripts/benchmark-tier-runner.py \
  --tier medium --role embedder \
  --task-set bench/tasks/embedder-medium-domain-openhands-ext.json \
  --rubric bench/rubrics/medium-scored.json \
  --candidate-file bench/candidates/embedder-fast-pool.json \
  --results-dir bench/results

# Portability arm — 6 cells (materialized BEIR file)
python3 scripts/benchmark-tier-runner.py \
  --tier medium --role embedder \
  --task-set bench/tasks/embedder-medium-beir-scidocs-materialized.json \
  --rubric bench/rubrics/medium-scored.json \
  --candidate-file bench/candidates/embedder-fast-pool.json \
  --results-dir bench/results

# Aggregate
python3 scripts/aggregate-embedder-medium-verdict.py

# Report the verdict JSON back to the agent for ADR-0017 authoring.
cat bench/results/verdicts/medium-verdict-embedder-*.json | tail -80
```

Then paste the aggregator output back so I can file ADR-0017 (embedder-medium tier verdict).
