# OpenHands-Ext v1 Session Handoff — 2026-08-11 10:12 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.3 gate-1 — **planner cell locked (ADR-0023 confirmed by ADR-0025)**
- **Plugin / kernel component:** production router role assignments finalized
- **Port(s) in progress:** none

## Completed this session
- Phase 0.2 Medium-tier verdicts filed (commit `8681ebb`).
- ADR-0023 filed: Phase 0.3 router-selection post-Medium (commit `40255c4`).
- ADR-0024 filed: planner migration-ordering probe task-set + gold + pre-registered reversal criteria (commit `15fd2cd`).
- Probe run at 10:07-10:08 EDT (commit `012e8b1`):
  - 27b-q6k: 4 tasks, 35.16s wall, all `verdict=pass`.
  - 35b-a3b-q4kxl: 4 tasks, 8.05s wall, all `verdict=pass`.
- ADR-0025 filed: probe verdict CONFIRMS ADR-0023 (pending push).
  - Scores: 27b macro-avg 91.75, 35b macro-avg 86.50 (27b +5.25 pts).
  - Reversal rule fired: `27b leads by ≥3 pts` → confirm.
  - 35b's probe-03 reproduced same skipped-verification failure class as planner-medium-02.

## Production router role assignments (locked)
- **coder:** `qwen3-coder-30b-a3b-instruct-awq-4bit` (vLLM, :8100, tiebreak winner on wall)
- **planner:** `qwen3_6-27b-q6k-gguf` (llama.cpp, :8082) — locked by ADR-0025
- **embedder:** `qwen3-embedding-4b-q8-gguf` (llama.cpp, CPU, :8090)
- **Fallbacks retained (viable, not eliminated):**
  - coder fallback: `qwen3_6-35b-a3b-q4kxl-gguf`
  - planner fallback: `qwen3_6-35b-a3b-q4kxl-gguf` (86.5 avg; ≥78 on all 4 probe tasks)

## Remaining before current Definition of Done (Phase 0.3)
- Choice point (make-optimal-choice on next user turn):
  - Option A: coder multi-turn correctness harness upgrade (Medium coder ceiling 85 stems from single-turn capture)
  - Option B: proceed to Phase 1 router wiring using locked role assignments
- No unresolved probe follow-up.

## Open questions / awaiting user answer
- None. Planner decision locked.

## Exact next action
Pull the ADR-0025 fan-out and inspect the verdict:

```bash
cd ~/dev/openhands-ext-v1
git pull
cat adrs/ADR-0025-planner-migration-probe-verdict-confirm-adr-0023.md
```

Then choose next Phase 0.3 direction (harness upgrade vs router wiring) — or say "make optimal choice" and I will proceed.
