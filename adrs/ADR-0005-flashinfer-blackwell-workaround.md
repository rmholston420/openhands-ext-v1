# ADR-0005 — flashinfer Blackwell (SM_120) workaround via `VLLM_USE_FLASHINFER_SAMPLER=0`

> **STATUS AMENDMENT (2026-08-11):** Retired. Superseded by [ADR-0006](ADR-0006-flashinfer-jit-cache-cu129.md), which installs `flashinfer-jit-cache==0.6.16.post3+cu129` and removes the need for the sampler override. The `scripts/smoke-test-vllm.sh` unconditional export has been removed; a comment in that file now points to ADR-0006 with instructions for temporary re-enable if the JIT cache pairing breaks in a future upgrade. Original decision text preserved below for historical record.

> **STATUS AMENDMENT (2026-08-11 02:26 EDT):** **Reinstated (partial) for the sampler path.** ADR-0006's cu129 JIT cache fixes attention on SM_120, but its `sampling.so` still calls `flashinfer.jit.core.check_cuda_arch()` on every invocation, which fails on SM_120 because the JIT-side capability probe is broken. Verified 2026-08-11 by direct `top_k_top_p_sampling_from_logits` call outside vLLM. `VLLM_USE_FLASHINFER_SAMPLER=0` is now baked into `bench/runner/main.py` VLLMServer env dict. Remains active until flashinfer >0.6.16.post3 ships a fixed capability probe.

**Status:** Ratified (reinstated 2026-08-11 02:26 EDT for sampler path) · ADR-0006 remains authoritative for attention
**Lock-in phase:** Phase -1 §-1.5
**Supersedes:** —

## Context

Colossus runs an RTX 5090 (Blackwell, SM_120). The venv-installed vllm 0.27.0 bundles flashinfer 0.6.16.post3, whose compiled shim cannot query SM_120 device capability under a CUDA runtime older than 12.9. When invoked during `compile_or_warm_up_model` it prints:

```
Failed to get device capability: SM 12.x requires CUDA >= 12.9.
```

then falls back to a stub value, and `flashinfer.jit.core.check_cuda_arch()` rejects that as `sm < 75`, raising `RuntimeError: FlashInfer requires GPUs with sm75 or higher`. The outer vLLM APIServer wraps this as `Engine core initialization failed. See root cause above. Failed core proc(s): {}`, which is misleading — the empty dict means the engine-core worker died before registering, and the sm75 message is a downstream artifact of the earlier CUDA-version failure.

Two options were considered:

1. **Disable the flashinfer sampler.** Set `VLLM_USE_FLASHINFER_SAMPLER=0`. vLLM routes top-k/top-p sampling through its native PyTorch implementation. Slightly slower per-sample than flashinfer but functionally identical for our smoke test. Zero binary changes.
2. **Upgrade flashinfer.** flashinfer >=0.7.0 has SM_120 support. On Python 3.14 (Colossus system Python) this risks torch ABI conflicts against the vllm 0.27.0 pinned torch 2.13.0. Would require rebuilding the venv against a newer torch/CUDA combination and re-validating every kernel path.

## Decision

Adopt Option 1 as the **Phase -1 workaround**: export `VLLM_USE_FLASHINFER_SAMPLER=0` unconditionally in `scripts/smoke-test-vllm.sh` (default-if-unset so callers can override for testing). Defer Option 2 to Phase 0 once CUDA >=12.9 is on the system and torch/flashinfer/vllm versions can be co-upgraded cleanly.

## Rationale

- Phase -1's Definition of Done is a green smoke test — not a production-optimal sampler path.
- The workaround is a single env var with no code change, easily reverted.
- Blocking Phase -1 on a full CUDA + flashinfer + torch + vllm upgrade contradicts the "minimal working system first" build discipline.
- The permanent fix (Option 2) belongs in Phase 0 alongside the other version-alignment tasks and needs its own smoke matrix.

## Consequences

- `scripts/smoke-test-vllm.sh` gains an unconditional `export VLLM_USE_FLASHINFER_SAMPLER=0` (default-if-unset), commented with a pointer to this ADR and DEBUG_LOG 2026-08-11.
- Any future script that invokes `vllm serve` directly must reproduce this export or ensure flashinfer is upgraded first. A Phase 0 task will remove this export once flashinfer is upgraded.
- Sampling perf on vLLM is slightly reduced (native path); acceptable for smoke/dev but must be revisited before production benchmarking.
- `PORTING_LEDGER.md` unaffected (no vendored component adopted or replaced).

## Lock-in phase

Phase -1 §-1.5. Superseded by Phase 0 flashinfer upgrade when that ADR is authored.

## References

- `DEBUG_LOG.md` — 2026-08-11 entry with the full traceback and root-cause line.
- vllm 0.27.0 release notes (bundled flashinfer 0.6.16.post3).
- flashinfer upstream SM_120 / Blackwell support: to be linked in Phase 0 follow-up ADR.
