# OpenHands-Ext v1 Session Handoff — 2026-08-11 09:49 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.3 gate-1 (router-selection lock-in)
- **Plugin / kernel component:** production role selection (coder + planner + embedder)
- **Port(s) in progress:** none (planner endpoint 8082 unchanged; model file swap only)

## Completed this session
- Phase 0.2 Medium-tier verdicts filed for coder (3 cells, single-turn capture, ceiling 85) and planner (2 cells, full-plan capture). Pushed as commit `8681ebb`.
- ADR-0023 filed as post-Medium Phase 0.3 router-selection ADR. Amends ADR-0017 planner row per rubric quality-first tiebreak rule.
  - **Coder:** UNCHANGED (`qwen3-coder-30b-a3b-instruct-awq-4bit/vllm/gpu:8100`). Wins 3-point tiebreak on wall time.
  - **Planner:** CHANGED — `qwen3_6-35b-a3b-q4kxl-gguf` → `qwen3_6-27b-q6k-gguf` (llama.cpp/gpu:8082). Quality delta 4.3 pts outside tiebreak band.
  - **Embedder:** UNCHANGED (CPU-resident per ADR-0017 amendment #3).
- Coder pool cleanup: `qwen3_6-27b-q6k-gguf` removed from `bench/candidates/coder-medium-pool.json` (dominated). Retained in planner pool.
- Files updated (commit pending): ADR-0023 new, ADR-0017 status amendment #4, `adrs/README.md`, `bench/candidates/production-selection.json`, `bench/candidates/coder-medium-pool.json`, `scripts/serve-planner.sh`, `BUILD_LOG.md`.
- Phase 0.3 planner re-eval: migration-ordering probe (3–5 tasks) pre-registered in ADR-0023 §5.

## Remaining before current Definition of Done
- Commit + push ADR-0023 fan-out.
- User pull on Colossus.
- User verifies planner GGUF present at `models/qwen3_6-27b-q6k-gguf/Qwen3.6-27B-Q6_K.gguf`. If missing, run:
  `huggingface-cli download unsloth/Qwen3.6-27B-GGUF Qwen3.6-27B-Q6_K.gguf --local-dir ~/dev/openhands-ext-v1/models/qwen3_6-27b-q6k-gguf`
- Author Phase 0.3 planner migration-ordering probe task-set (3–5 tasks). Then re-eval 35b-a3b-q4kxl on it — if it passes all, reconsider planner ordering.
- Open items from Phase 0.2 (deferred to Phase 0.3+):
  - Coder multi-turn correctness harness upgrade (currently captures only first tool call per task; ceiling 85 applied to Medium coder scores as a consequence).

## Open questions / awaiting user answer
- None. All post-Medium decisions taken under rubric locked in ADR-0016 + ADR-0022.

## Exact next action
Pull on Colossus and verify planner model file exists before next planner start:

```bash
cd ~/dev/openhands-ext-v1
git pull
ls -lh models/qwen3_6-27b-q6k-gguf/Qwen3.6-27B-Q6_K.gguf 2>/dev/null || \
  huggingface-cli download unsloth/Qwen3.6-27B-GGUF Qwen3.6-27B-Q6_K.gguf \
    --local-dir models/qwen3_6-27b-q6k-gguf
```
