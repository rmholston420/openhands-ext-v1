# Kosmos Session Handoff — 2026-08-11 04:55 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.1 · Fast tier
- **Slice in progress:** planner-fast POOL (next: embedder-fast POOL)
- **Port(s) in progress:** none (bench harness only)

## Completed this session
- Coder-fast pool 4 → 3 (eliminated Coder-Instruct, ADR-0011 ratified v25) — commit `951f580`
- Coder-fast pool 3 → 2 (eliminated 27B Q6_K on R2 read-first stall) — commit `eeb4a1c`
- Coder-fast 2-cell smoke confirmation: 2/2 pass (thinker + 35B MoE)
- Authored `bench/candidates/planner-fast-pool.json` (3 cells)
- Authored `bench/candidates/embedder-fast-pool.json` (6 cells)

## Remaining before current Definition of Done
- Run planner-fast POOL (3 cells; §0.0b min=3 satisfied)
- Run embedder-fast POOL (6 cells; §0.0b min=4 satisfied)
- Apply R1/R2/R3 rubric to results; document eliminations
- If any survivor pool < min for its role, either author fresh candidates or use `--smoke` for confirmation runs (same pattern as coder-fast)

## Open questions / awaiting user answer
- none

## Exact next action

Pull latest, then run planner-fast POOL:

```bash
cd ~/dev/openhands-ext-v1
git fetch origin && git reset --hard origin/main
scripts/benchmark-tier-runner.py \
  --tier fast --role planner \
  --task-set bench/tasks/planner-fast.json \
  --rubric bench/rubrics/fast-elimination.json \
  --candidate-file bench/candidates/planner-fast-pool.json \
  --vllm-release 0.27.0
```

Then embedder-fast POOL:

```bash
scripts/benchmark-tier-runner.py \
  --tier fast --role embedder \
  --task-set bench/tasks/embedder-fast.json \
  --rubric bench/rubrics/fast-elimination.json \
  --candidate-file bench/candidates/embedder-fast-pool.json \
  --vllm-release 0.27.0
```

Paste both run logs. Agent scores against R1/R2/R3.
