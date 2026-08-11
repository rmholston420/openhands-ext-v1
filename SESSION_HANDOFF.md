# OpenHands-Ext v1 Session Handoff — 2026-08-11 09:56 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.3 gate-1 (post-ADR-0023 planner re-eval; probe authored, awaiting run)
- **Plugin / kernel component:** planner role · migration-ordering probe
- **Port(s) in progress:** none (probe is bench-only)

## Completed this session
- Phase 0.2 Medium-tier verdicts filed (commit `8681ebb`).
- ADR-0023 filed: Phase 0.3 router-selection post-Medium (commit `40255c4`).
  - Planner flipped `qwen3_6-35b-a3b-q4kxl-gguf` → `qwen3_6-27b-q6k-gguf` on quality-first tiebreak (4.3-pt gap, outside 3-pt band).
  - Coder + embedder unchanged.
- ADR-0024 filed: planner migration-ordering probe (pending push).
  - 4 tasks: expand-migrate-contract, rename via expand-contract, FK with cleanup, CONCURRENTLY index rebuild.
  - 4 gold references authored, SHA-256 hashed and frozen in task-set JSON.
  - 5-branch pre-registered reversal criteria locked in `bench/tasks/planner-medium-migration-probe.json#/reversal_criteria`.
  - Cells: 27b-q6k (current planner) + 35b-a3b-q4kxl (fallback on trial).

## Remaining before current Definition of Done
- Commit + push ADR-0024 fan-out.
- User pull on Colossus.
- Run the probe on both cells (sequential-block co-residency; ~30 min per cell):
  - `bash scripts/stop-large-model.sh coder` (if coder is hot)
  - Cell 1: 27b-q6k on `bench/tasks/planner-medium-migration-probe.json` (all 4 tasks)
  - `bash scripts/stop-large-model.sh planner`
  - Cell 2: 35b-a3b-q4kxl on same task-set (all 4 tasks)
  - Save outputs under `bench/scoring/planner-migration-probe-<ts>/<cell>/*.json`
- Dump stripped outputs and score via Perplexity Max against the 4 gold files.
- File follow-up ADR (0025 or later) that either **confirms ADR-0023 planner ordering** (27b-q6k retained) or **flips planner back to 35b-a3b-q4kxl** — decision fully determined by the pre-registered reversal criteria; no post-hoc interpretation.
- Open items unchanged from prior session:
  - Coder multi-turn correctness harness upgrade (Medium coder ceiling 85 stems from single-turn capture).

## Open questions / awaiting user answer
- None. Probe is fully specified.

## Exact next action
Pull the ADR-0024 commit and inspect the probe artifacts:

```bash
cd ~/dev/openhands-ext-v1
git pull
ls -1 bench/tasks/planner-medium-migration-probe.json bench/gold/planner-medium-migration-probe/
```

Then when ready to run the probe, ping this thread for the exact bench harness invocation.
