# Kosmos Session Handoff — 2026-08-11 05:29 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 · Medium tier · planner budget-hypothesis probe (ADR-0015 Proposed)
- **Next slice:** run Probe A on Colossus; interpret against pre-registered criteria
- **Port(s) in progress:** none

## Fast-tier pools (locked, unchanged this slice)

| Role | Cells | Members |
|---|---:|---|
| Coder | 4 | thinker-2507-awq (vllm/gpu), coder-30b-a3b-instruct-awq-4bit (vllm/gpu), qwen3_6-27b-q6k-gguf (llama.cpp/gpu), qwen3_6-35b-a3b-q4kxl-gguf (llama.cpp/gpu) |
| Planner | 2 | qwen3_6-27b-q6k-gguf (llama.cpp/gpu), qwen3_6-35b-a3b-q4kxl-gguf (llama.cpp/gpu) |
| Embedder | 6 | 0.6B ×3 + 4B ×3 |

## Completed this slice
- Filed **ADR-0015** (Proposed): planner Medium-tier thinker-2507-awq budget-hypothesis probe. Pre-registered H0/H1 hypotheses, success criteria (malformed ≤ 1 of 3, median wall ≤ 60s, valid schema), sequential run plan (8k first, 16k only if 8k doesn't falsify H0).
- Authored two task-set files (`planner-medium-thinker-probe-b8k.json`, `-b16k.json`) identical to `planner-fast.json` except `budget_tokens` (8192, 16384).
- Authored 1-cell candidate file `planner-medium-thinker-probe.json` (thinker-2507-awq, role=planner override, reasoning_parser=qwen3).
- Added `scripts/inspect-raw-content.py` — read-only diagnostic on `.probe.json` sidecars (raw_chars, `<think>` char count, wall, truncation).
- Verified harness plumbing: `--smoke` bypasses §0.0b pool guard for a 1-cell diagnostic run; result JSONs are tagged `smoke=true` (not pool-decision evidence).

## Remaining before current Definition of Done
- Human runs Probe A (8k) on Colossus.
- If Probe A does NOT satisfy the Falsified criterion, human runs Probe B (16k).
- I read the resulting `.probe.json` sidecar (once pushed back or inspected via output), apply pre-registered criteria, then amend ADR-0015 to Ratified with either Falsified or Confirmed verdict.

## Open questions / awaiting user answer
- None. Optimal calls made per user direction: 60s SLO, sequential 8k → 16k.

## Exact next action

```bash
cd ~/dev/openhands-ext-v1 && git fetch origin && git reset --hard origin/main

# Probe A (8k)
.venv/bin/python scripts/benchmark-tier-runner.py --tier fast --role planner \
  --task-set bench/tasks/planner-medium-thinker-probe-b8k.json \
  --rubric bench/rubrics/fast-elimination.json \
  --candidate-file bench/candidates/planner-medium-thinker-probe.json --smoke

# After Probe A completes, paste the tail of the run output plus:
ls -1t bench/results/*thinker*b8k* 2>/dev/null | head -4
python3 scripts/inspect-raw-content.py bench/results/*thinker*b8k*.probe.json
```
