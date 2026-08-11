# OpenHands-Ext v1 — Session Handoff — 2026-08-11 00:30 EDT

## Current build-sequencing position

- **Stage / phase:** Phase -1 §-1 Verification table — **truly green**. Both §-1.5 smokes (llama.cpp + vLLM) status: pass on Colossus. Ready for session-end commit and Phase 0 kickoff.
- **Plugin / kernel component:** none (governance + toolchain).
- **Port(s) in progress:** none.

## Completed this session

- **llama.cpp built + smoke green.** CUDA-13 pin + `patch-cuda-headers.sh` (perm preservation fix `0600 → 0644`) landed. `build-llama-cpp.sh` completed in 185 s; tag b10356 @ `0666ad2b2`. Smoke: 2328 tok/s prompt, 599 tok/s decode on Qwen 1.5B q4_k_m, GPU peaked 30735/32607 MiB — CUDA backend confirmed active.
- **vLLM smoke green.** Diagnosed engine-core init crash as flashinfer 0.6.16 rejecting SM_120 under CUDA <12.9 (misleading "sm75 or higher" error was a downstream artifact of `Failed to get device capability: SM 12.x requires CUDA >= 12.9`). Applied Phase -1 workaround: `VLLM_USE_FLASHINFER_SAMPLER=0` baked default-if-unset into `scripts/smoke-test-vllm.sh`. Smoke passed: /health 30 s, chat completion returned, 18.86 GiB GPU used.
- **ADR-0005** filed and indexed — flashinfer Blackwell workaround; permanent fix (flashinfer upgrade + CUDA >=12.9) deferred to Phase 0.
- **DEBUG_LOG** entry appended (2026-08-11 00:27 EDT) with the misleading-error root-cause trail.
- **BUILD_LOG** entries appended for the llama.cpp smoke pass and the vLLM smoke pass.

## Remaining before current Definition of Done

**Done.** Phase -1 §-1 Verification table is green.

Only remaining task: on Colossus, run session-end with a truthful subject. `session-end.sh` will validate both `bench/results/phase-neg-1-smoke-*.json` files show `status: pass` before allowing the commit.

## Open questions / awaiting user answer

- None.

## Exact next action

On Colossus, after `git pull origin main`:

```bash
cd ~/dev/openhands-ext-v1
git pull origin main
bash scripts/session-end.sh -m "phase(-1): §-1 Verification table green (llama.cpp + vLLM smokes both pass; flashinfer SM_120 workaround via VLLM_USE_FLASHINFER_SAMPLER=0, ADR-0005)"
```

If the truth gate refuses, paste its output; otherwise Phase -1 is closed and next session opens Phase 0 planning (flashinfer + CUDA >=12.9 upgrade, docs collection via `scripts/pull-docs.sh`, `docs/config/proposed-config.md`).
