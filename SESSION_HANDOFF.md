# Kosmos Session Handoff — 2026-08-11 05:15 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.1 · Fast tier · **complete for planner and embedder**
- **Next slice:** Phase 0.1 · Fast-tier confirmation smoke (optional) OR move to Phase 0.2 Medium tier queue.
- **Port(s) in progress:** none.

## Completed this session
- Coder-fast pool 4 → 3 → 2 (commits `951f580`, `eeb4a1c`) with confirmation smoke 2/2 pass.
- Planner-fast POOL executed (harness `35382dd`); rescored under `3022385` after harness rubric-compliance fix. **Locked at 2 survivors:**
  - `qwen3_6-27b-q6k-gguf` (llama.cpp/gpu)
  - `qwen3_6-35b-a3b-q4kxl-gguf` (llama.cpp/gpu)
  - Eliminated: `qwen3-30b-a3b-thinking-2507-awq` (vLLM/gpu) — R2 (2 malformed), legitimate on merit; Thinking-2507 checkpoint cannot honor `enable_thinking=false` at 4096-token budget.
- Embedder-fast POOL: **6/6 pass, locked.**
- Rubric-compliance harness fix committed (`9d4f6b0` + `3022385`) with rescore tool.
- BUILD_LOG appended (three entries this session); DEBUG_LOG appended (rubric-compliance bug + Thinking-2507 unfit); rescore tool ergonomic fix.

## Fast-tier survivors (both roles)

| Role | Survivor | Runtime | Median wall | tok/s | VRAM peak |
|---|---|---|---|---|---|
| Planner | qwen3_6-27b-q6k-gguf | llama.cpp/gpu | 4.44s | 60 | 24135 MiB |
| Planner | qwen3_6-35b-a3b-q4kxl-gguf | llama.cpp/gpu | 0.86s | 255 | 23266 MiB |
| Embedder | qwen3-embedding:0.6b bf16 | vllm/gpu | — | — | small |
| Embedder | qwen3-embedding:0.6b Q8 | llama.cpp/gpu | — | — | small |
| Embedder | qwen3-embedding:0.6b Q8 | llama.cpp/cpu | — | — | — |
| Embedder | qwen3-embedding:4b bf16 | vllm/gpu | — | — | ≤6708 MiB |
| Embedder | qwen3-embedding:4b Q8 | llama.cpp/gpu | — | — | ≤6708 MiB |
| Embedder | qwen3-embedding:4b Q8 | llama.cpp/cpu | — | — | — |

## Remaining before current Definition of Done
- Nothing spec-blocking for planner-fast or embedder-fast — both stop conditions met.
- Optional Fast-tier confirmation smoke on planner (`--smoke` mode) to catch any regression under fresh cold-starts. Not required by spec.

## Open questions / awaiting user answer
- Confirmation smoke: run one, or move directly to Medium-tier queue?
- Medium-tier task-set authoring: which role first — planner or embedder?

## Exact next action

```bash
cd ~/dev/openhands-ext-v1 && git fetch origin && git reset --hard origin/main

# Sanity: re-run the rescore glob now that .probe.json is silently skipped —
# should show only real result rows, no [ERR] lines.
python3 scripts/rescore-fast-verdicts.py bench/results/phase-0-fast-*.json
```

Then decide: confirmation smoke or Medium-tier authoring.
