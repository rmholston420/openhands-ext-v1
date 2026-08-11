# OpenHands-Ext v1 · Session Handoff — 2026-08-11 07:12 EDT

## Current build-sequencing position
- **Stage / phase:** Phase −1 verified COMPLETE (drift-tolerant baseline). All 3 production endpoints PASS. All 9 un-pause gates GREEN.
- **Plugin / kernel component:** none in flight
- **Port(s) in progress:** none

## Completed this session
- ADR-0017 amendments #1–#3 (coder 8000→8001→8100; embedder GPU→CPU per spec)
- Coder LIVE on 8100 (vLLM 0.27.0, `VLLM_USE_FLASHINFER_SAMPLER=0` for Blackwell+CUDA-12.8)
- Embedder LIVE on 8090 (llama.cpp CPU, ctx 4096, dim 2560)
- Planner boot-verified on 8082 (llama.cpp, `chat_template_kwargs.enable_thinking=false` per ADR-0008)
- `check-production-endpoints.sh` fixed: now forwards ADR-0008 kwarg (commit 4a2a66f)
- 4 deferred spec-compliance questions resolved (Q1–Q4 in commit 120ebb8)
- Un-pause complete: all 9 gates GREEN, `docs/BENCHMARK_UNPAUSE_GATES.md` header updated
- **Phase −1 verification complete** (this session's headline):
  - Live-fetched top-of-releases for openhands ecosystem + llama.cpp + vLLM
  - Colossus install state captured; drift logged (llama.cpp 3 tags, vLLM 1 patch)
  - Category-7 metadata artifact written: `bench/run-metadata/version-pins-20260811T111235Z.json`
  - Verification checklist written: `docs/PHASE-MINUS-1-VERIFICATION.md`
  - ADR-0018 filed (drift-tolerant policy)
  - SDK-to-runtime smoke PASSes both runtimes via existing production endpoints

## Remaining before current Definition of Done
- Phase −1 DoD: MET. Nothing remains.

## Open questions / awaiting user answer
- None from this session.
- Deferred (recorded in KNOWN_ISSUES.md):
  - llama.cpp b10356 → b10359 drift (leave until a fix motivates upgrade)
  - vLLM 0.27.0 → 0.27.1 drift (leave until 0.27.1 changelog reviewed for SM 12.0 sampler)
  - CUDA 12.8 → 12.9 upgrade path (unlocks FlashInfer sampler + native Blackwell kernels)
  - 4B-CPU vs. 0.6B-GPU embedder benchmark (triggered by retrieval-latency observations)

## Exact next action
Phase 0.1 opens next per spec sequencing. Before it starts, restate Phase 0.1 scope from `docs/specs/integration-execution-plan-v16.md` and flag any ambiguity for user confirmation. Do not begin Phase 0.1 code without the standard scope-restate.
