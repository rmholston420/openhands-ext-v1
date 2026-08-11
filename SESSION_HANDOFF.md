# OpenHands-Ext v1 Session Handoff — 2026-08-11 04:38 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.1 · Fast tier · coder pool
- **Plugin / kernel component:** bench runner (candidate list + rubric)
- **Port(s) in progress:** none (config-only change)

## Completed this session
- ADR-0011 amend 1 (per-cell tool-call parser) — plumbing wired (prior).
- ADR-0011 amend 2 (per-cell reasoning parser) — plumbing wired + verified via 4-cell POOL re-run.
- ADR-0011 ratified v25 (2026-08-11 04:38 EDT).
- Coder-Instruct (`qwen3-coder-30b-a3b-instruct-awq-4bit`) eliminated from `bench/candidates/coder-fast-pool.json`. Registry entry retained.
- BUILD_LOG + DEBUG_LOG entries appended.

## Fast-tier coder pool (locked, 3 cells)
1. `qwen3-30b-a3b-thinking-2507-awq` — vLLM, hermes tool-parser, qwen3 reasoning-parser (thinking).
2. `qwen3_6-27b-q6k-gguf` — llama.cpp, dense 27B Q6_K.
3. `qwen3_6-35b-a3b-q4kxl-gguf` — llama.cpp, MoE 35B/A3B Q4_K_XL UD.

## Remaining before current Definition of Done
- Re-run 3-cell coder-fast POOL to confirm all three pass with the reduced pool (fast smoke; ~2 min).
- Move on to next Phase 0.1 slice (planner tier, or slow tier — user decides).

## Open questions / awaiting user answer
- Whether to keep Coder-Instruct in scope for slow-tier evaluation (registry entry retained; not blocked either way).

## Exact next action
```bash
cd ~/dev/openhands-ext-v1 && git pull
scripts/benchmark-tier-runner.py \
  --tier fast --role coder \
  --task-set bench/tasks/coder-fast.json \
  --rubric bench/rubrics/fast-elimination.json \
  --candidate-file bench/candidates/coder-fast-pool.json \
  --vllm-release 0.27.0
```
