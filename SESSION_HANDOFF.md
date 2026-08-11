# OpenHands-Ext v1 Session Handoff — 2026-08-11 04:45 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.1 · Fast tier · coder pool
- **Plugin / kernel component:** bench runner (candidate list)
- **Port(s) in progress:** none (config-only change)

## Completed this session
- ADR-0011 amend 1 (per-cell tool-call parser) — plumbing wired (prior).
- ADR-0011 amend 2 (per-cell reasoning parser) — plumbing wired + verified via 4-cell POOL re-run.
- ADR-0011 ratified v25 (2026-08-11 04:38 EDT).
- Coder-Instruct (`qwen3-coder-30b-a3b-instruct-awq-4bit`) eliminated from fast pool (task 02 forbidden_tools violation: execute_bash).
- 27B Q6_K GGUF (`qwen3_6-27b-q6k-gguf`) eliminated from fast pool (task 02 expected_tool_sequence violation: read_file stall before edit).
- BUILD_LOG + DEBUG_LOG entries appended for both eliminations.

## Fast-tier coder pool (locked, 2 cells)
1. `qwen3-30b-a3b-thinking-2507-awq` — vLLM, hermes tool-parser, qwen3 reasoning-parser (thinking).
2. `qwen3_6-35b-a3b-q4kxl-gguf` — llama.cpp, MoE 35B/A3B Q4_K_XL UD.

## Remaining before current Definition of Done
- Confirmation run of 2-cell fast-tier POOL — verify both pass on a clean invocation.
- Advance to next Phase 0.1 slice (planner tier or slow tier — user decides).

## Open questions / awaiting user answer
- Whether to keep Coder-Instruct and 27B Q6_K in scope for slow-tier evaluation (registry entries retained; not blocked either way).

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
