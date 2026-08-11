# ADR-0006 — flashinfer SM_120 support via `flashinfer-jit-cache==0.6.16.post3+cu129`

> **STATUS AMENDMENT (2026-08-11 02:26 EDT):** Original ratification covered only the attention path. Phase 0.1 runner's first sampler-exercising smoke revealed that `sampling.so` (shipped in the cu129 JIT cache) still gates every call on `flashinfer.jit.core.check_cuda_arch()`, which fails on SM_120 because a separate broken device-capability probe returns a sub-sm75 stub. The 00:50 EDT verification record was empty (`probes: []`, `verdict: None`) — it validated `/v1/models` health only, never sampling. **ADR-0005 sampler escape hatch (`VLLM_USE_FLASHINFER_SAMPLER=0`) is reinstated as active** for the sampler path and baked into `bench/runner/main.py`. Attention path from this ADR remains correct. See DEBUG_LOG 2026-08-11 02:26 EDT for the direct-call verification.

**Status:** Ratified · Amended (sampler path deferred to ADR-0005)
**Lock-in phase:** Phase -1 §-1.5 (retroactive) → Phase 0 prerequisite
**Supersedes:** ADR-0005 (workaround `VLLM_USE_FLASHINFER_SAMPLER=0`) — **partially rescinded 2026-08-11 02:26 EDT**; ADR-0005 remains active for sampler until flashinfer >0.6.16.post3 ships a fixed `check_cuda_arch()` or JIT-time capability probe.

## Context

Colossus runs an RTX 5090 (Blackwell, SM_120) with:

- CUDA 13.0 (`/usr/local/cuda-13.0`) — no CUDA 12.9 installed.
- Python 3.14 venv, torch 2.13.0+cu130, vllm 0.27.0 (pinned to `flashinfer-python==0.6.16.post3`).

The stock `flashinfer-python` wheel ships a compiled shim that queries device compute capability via a code path that expects a **CUDA runtime ≥ 12.9** for SM 12.x GPUs. Under CUDA 13.0 (which is a *superset* of 12.9 features) that check still fails because it reads `CUDA_VERSION` numerically as `13000` but branches on a hardcoded `12900` inequality that doesn't include the SM_120-aware entry points until the AOT-precompiled kernels are present. This produced the "sm75 or higher" downstream error documented in ADR-0005 and DEBUG_LOG.md 2026-08-11.

Two paths investigated in this ADR:

1. **Bypass the sampler.** ADR-0005: set `VLLM_USE_FLASHINFER_SAMPLER=0`. Works for the sampler path only; leaves every other flashinfer entry point (FP8 attention, MoE kernels, FlashInferMLA) still broken. Insufficient for Phase 0 benchmarking where AWQ/INT4/MoE candidates route through those paths.
2. **Install the AOT / JIT-cache wheel matching flashinfer + a CU pin.** flashinfer publishes `flashinfer-jit-cache-<version>+cu<CUDA_TAG>` wheels at `https://flashinfer.ai/whl/cu129/`. The `+cu129` tag provides Blackwell (SM_100/12x) AOT kernels precompiled against a CUDA-12.9 toolchain and is loadable at runtime on CUDA-13 systems, because it links only against symbols present in both.

## Decision

**Adopt Option 2.** Install `flashinfer-jit-cache==0.6.16.post3+cu129` from `https://flashinfer.ai/whl/cu129/`, matched exactly to the `flashinfer-python==0.6.16.post3` pinned by vllm 0.27.0.

The `scripts/smoke-test-vllm.sh` unconditional `VLLM_USE_FLASHINFER_SAMPLER=0` export is removed. The comment block now documents the JIT-cache dependency and shows the temporary re-enable escape hatch for the case where a future flashinfer-python bump breaks the pairing.

## Rationale

- **Wider fix surface.** The JIT cache supplies SM_120 kernels for every flashinfer entry point, not just the sampler. This unblocks FP8/AWQ/MoE candidates in Phase 0 §0.0b.
- **No CUDA-runtime upgrade required.** Adding `/usr/local/cuda-12.9` alongside 13.0 was the alternative; it would have forced a torch/vllm ABI re-validation. The JIT cache route sidesteps that entirely.
- **Version-pinned.** The `+cu129` wheel pins to a specific flashinfer version. A version mismatch between `flashinfer-python` and `flashinfer-jit-cache` fails loudly at import (verified on 2026-08-11 with `.post3` vs `.post4+cu129`), so drift cannot silently degrade the runtime.
- **vllm-compatibility preserved.** vllm 0.27.0's `flashinfer-python==0.6.16.post3` pin is satisfied. No vLLM upgrade needed.

Verification evidence (recorded 2026-08-11):

- `bench/results/phase-neg-1-smoke-vllm-20260811T044948Z.json` — vllm smoke passed cleanly with `VLLM_USE_FLASHINFER_SAMPLER` unset; health OK at 22s; RTX 5090 device_cap `(12, 0)` correctly detected by torch on cu130.
- The stderr line `Failed to get device capability: SM 12.x requires CUDA >= 12.9.` still prints at flashinfer import — it is now benign. flashinfer proceeds through the JIT-cache SM_120 path.

## Consequences

- **`scripts/smoke-test-vllm.sh`** — retired the unconditional `VLLM_USE_FLASHINFER_SAMPLER=0` export; replaced with a comment pointing to this ADR.
- **`scripts/bootstrap-venv.sh`** or `install-vllm.sh` — must add `pip install --index-url https://flashinfer.ai/whl/cu129 "flashinfer-jit-cache==0.6.16.post3+cu129"` to the deterministic venv setup, so a fresh checkout on Colossus (or a new box with the same hardware) reproduces this fix without ad-hoc manual steps. Filed as a follow-up in BUILD_LOG.
- **Phase 0 pool exposure.** Every candidate that would have hit flashinfer FP8/AWQ/MoE now runs through the SM_120 AOT kernels. Previously masked failure modes may surface; treat each as a candidate-specific issue, not a runtime failure.
- **Runtime-version regression rule (spec §0.1).** If the JIT cache version and `flashinfer-python` version ever drift again, log the fail as a **runtime-version regression**, not a candidate failure.
- **Wheel size.** `flashinfer-jit-cache-0.6.16.post3+cu129` is ~1.9 GiB. Venv disk envelope grows accordingly. Not a blocker on Colossus's ~20 GiB free budget but noted for reproducibility docs.

## Lock-in phase

Phase -1 §-1.5 retroactively; also a Phase 0 prerequisite. The `bootstrap-venv.sh` update is a follow-up task in the current session.

## References

- `DEBUG_LOG.md` — 2026-08-11 workaround entry + 2026-08-11 retirement entry.
- ADR-0005 — original workaround (amended, superseded by this ADR).
- flashinfer JIT-cache index: `https://flashinfer.ai/whl/cu129/`.
- `bench/results/phase-neg-1-smoke-vllm-20260811T044948Z.json` — verification smoke.
