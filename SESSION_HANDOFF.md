# OpenHands-Ext v1 · Session Handoff — 2026-08-11 06:57 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 (Medium-tier authoring paused; production endpoints all verified)
- **Plugin / kernel component:** serve infra · all three production roles live and healthy
- **Port(s) in progress:** none — all four deferred spec-compliance questions resolved

## Completed this session
- ADR-0017 amendments #1–#3 (coder 8000→8001→8100; embedder GPU→CPU per spec)
- Coder up on 8100 (PASS chat 192 ms, out_tokens=7). Embedder up on 8090 (CPU, dim=2560).
- Coder FlashInfer sampler workaround (`VLLM_USE_FLASHINFER_SAMPLER=0`) for Blackwell SM 12.0 + CUDA 12.8
- Four deferred spec-compliance questions resolved:
  1. ADR-0017 status label → `Ratified v25 · Amended ×3 (pre-Phase-0.3)`
  2. Config surface → env-vars-only through Phase 0.2 (POST-PHASE-0.3 ONLY rule preserved)
  3. Pre-commit hook → no action (existing `no-localworkspace.sh` already satisfies Phase-1; remaining Phase-1 checks are integration tests deferred until Phase-1 opens)
  4. Un-pause checklist → `docs/BENCHMARK_UNPAUSE_GATES.md` authored (this file references it)
- DEBUG_LOG entries: 3 (compressed-tensors, embedder GPU→CPU, FlashInfer sampler) with 7 reusable lessons total
- KNOWN_ISSUES entry: deferred 4B-CPU vs. 0.6B-GPU embedder decision

## Un-pause gates
See `docs/BENCHMARK_UNPAUSE_GATES.md` for the full 9-gate checklist. Current status: all 9 GREEN except **Gate 4 (planner VRAM budget)** which is UNVERIFIED — planner has not yet been started this session. Un-pause requires one clean planner start.

## Remaining before Medium-tier un-pause
- One successful `serve-planner.sh` → PASS on `check-production-endpoints.sh` → clean stop, to flip Gate 4 to GREEN.

## Open questions / awaiting user answer
- None from this session's queue.
- Deferred: 4B-CPU vs. 0.6B-GPU embedder benchmark (KNOWN_ISSUES, triggered by retrieval latency measurements).
- Deferred: CUDA 12.8 → 12.9 upgrade path (unlocks FlashInfer sampler + native SM 12.x kernels).

## Exact next action
Once user is ready to close Gate 4 (planner verification):
```bash
cd ~/dev/openhands-ext-v1
bash scripts/stop-large-model.sh coder    # co-residency Option 2
sleep 3
bash scripts/serve-planner.sh >/tmp/serve-planner.log 2>&1 &
sleep 60
bash scripts/check-production-endpoints.sh
# Expect planner PASS; coder FAIL (stopped, expected).
# Then to restore working state:
bash scripts/stop-large-model.sh planner
bash scripts/serve-coder.sh >/tmp/serve-coder.log 2>&1 &
```
