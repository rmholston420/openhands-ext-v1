# OpenHands-Ext v1 · Session Handoff — 2026-08-11 06:49 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 (Medium-tier authoring paused)
- **Plugin / kernel component:** serve infra · production endpoints bring-up
- **Port(s) in progress:** coder (8100) restart pending — one more push then retry

## Completed this session
- ADR-0017 amendments #1–#3 (coder 8000→8001→8100; embedder GPU→CPU per spec)
- Coder `--quantization` flag removed (compressed-tensors auto-detect)
- Coder VRAM contention diagnosed and resolved (embedder now on CPU; ~30 GiB free at coder startup)
- Coder FlashInfer sampler crash diagnosed (SM 12.0 + CUDA 12.8 < 12.9); patch: `VLLM_USE_FLASHINFER_SAMPLER=0` in `scripts/serve-coder.sh`
- DEBUG_LOG updated with 4 reusable Blackwell/vLLM lessons
- KNOWN_ISSUES filed: deferred 4B-CPU vs. 0.6B-GPU embedder decision

## Remaining before current Definition of Done
- User pulls + retries coder → expect success at 0.90 util
- Run `check-production-endpoints.sh` → expect coder PASS, planner FAIL (not started, expected)
- If coder passes: return to 4 deferred spec-compliance questions
- If coder fails: harvest new root cause from `/tmp/serve-coder.log`

## Open questions / awaiting user answer
- Four deferred spec-compliance questions (ADR-0017 status label, env-vars vs. configs/dev-current/, Phase-1 pre-commit hook, un-pause checklist location) — resume once coder healthy
- Deferred: eventual 4B-CPU vs. 0.6B-GPU embedder benchmark (KNOWN_ISSUES 2026-08-11)
- Deferred: whether to upgrade Colossus CUDA 12.8 → 12.9 to unlock FlashInfer sampler + native Blackwell kernels

## Exact next action
On Colossus (`~/dev/openhands-ext-v1`):
```bash
git pull
# Coder retry (embedder already CPU-resident from prior step)
bash scripts/serve-coder.sh >/tmp/serve-coder.log 2>&1 &
sleep 45
bash scripts/check-production-endpoints.sh
# If any FAIL besides planner (expected):
tail -100 /tmp/serve-coder.log
```
