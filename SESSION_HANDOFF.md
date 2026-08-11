# OpenHands-Ext v1 — Session Handoff — 2026-08-11 00:25 EDT

## Current build-sequencing position

- **Stage / phase:** Phase -1 execution — **partial**, corrective fixes landed, awaiting re-run on Colossus.
- **Plugin / kernel component:** none (governance + toolchain).
- **Port(s) in progress:** none.

## Completed this session

- Filed **ADR-0004** — llama.cpp CUDA toolchain pin: `/usr/local/cuda-13.0` + `/usr/bin/gcc-13` + `SM_120`. CUDA 12.8 rejected due to `math_functions.h` `noexcept` conflict with Ubuntu 26.04's glibc 2.43.
- Amended **ADR-0003** — added the commit-message truth gate; documented that commit `535bc35`'s subject "§-1 Verification table all green" was inaccurate.
- Rewrote `scripts/build-llama-cpp.sh` to use CUDA 13.0 (with `PATH`/`CUDA_PATH`/`LD_LIBRARY_PATH` prefixed to the cuda-13.0 tree) and to emit a `status: pass` metadata JSON on success.
- Rewrote `scripts/smoke-test-vllm.sh` — `nvidia-smi` VRAM preflight (refuses < 20 GiB free by default), env-overridable `VLLM_GPU_MEM_UTIL` (default lowered to `0.55`), `VLLM_MAX_MODEL_LEN`, `VLLM_STARTUP_TIMEOUT` (240 s), `VLLM_MIN_FREE_GIB`, and a `status: pass|fail` metadata JSON.
- Rewrote `scripts/session-end.sh` — reads the two Phase -1 smoke JSONs, refuses subjects claiming "all green" / "complete" when they aren't `pass`, appends `smoke.llama-cpp:` and `smoke.vllm:` lines to every commit body.
- Added `status: pass` field to `scripts/smoke-test-llama-cpp.sh` metadata JSON.
- Appended three DEBUG_LOG entries (CUDA-12.8/glibc conflict, vLLM VRAM OOM, commit-535bc35 misleading subject) and a BUILD_LOG entry for all of the above.

## Remaining before current Definition of Done

**Phase -1 §-1 Verification table is still NOT green.** To close it out, on Colossus:

1. `git pull origin main`
2. `bash scripts/install-hooks.sh` (installs updated session-end truth gate)
3. `bash scripts/build-llama-cpp.sh` — should now succeed under CUDA 13.0. Expect 5-15 min. On success this writes `bench/results/phase-neg-1-build-llama-cpp-*.json` with `status: pass`.
4. **Free VRAM before smoke-test-vllm** — close Chrome / IDE / other GPU apps. Verify with `nvidia-smi --query-gpu=memory.free --format=csv,noheader`. Need ≥ 20 GiB free (out of 32 GiB total).
5. `bash scripts/smoke-test-llama-cpp.sh` — port 8082.
6. `bash scripts/smoke-test-vllm.sh` — port 8083. If VRAM preflight still fails, use `VLLM_GPU_MEM_UTIL=0.3 VLLM_MIN_FREE_GIB=10 bash scripts/smoke-test-vllm.sh` (Qwen 1.5B needs ~4 GiB of weights + KV cache; 10 GiB budget is plenty).
7. `bash scripts/session-end.sh -m "phase(-1): §-1 Verification table green (corrected)"` — this will now be *allowed* only if both smoke JSONs report `status: pass`. Otherwise it will refuse with a truthful error.

## Open questions / awaiting user answer

- None. Recommendations from prior turn accepted.

## Exact next action

On Colossus. The previous run left the CUDA header patched but with mode
`0600 root:root`, which cmake can't read. The updated patch script detects
this on its idempotent path and repairs perms to `0644` (still needs sudo
because the file is root-owned).

```bash
cd ~/dev/openhands-ext-v1
git pull origin main
bash scripts/install-hooks.sh
bash scripts/build-llama-cpp.sh    # sudo prompt: patch script fixes perms
```

Expected first-run output (patch step):

```
--- patching CUDA headers (idempotent, requires sudo) ---
[sudo] password: ...
[fix] corrected mode on already-patched header to 0644
[ok] /usr/local/cuda-13.0/.../math_functions.h already patched (marker present; mode 644 root:root)
```

Then cmake configure should proceed past the CUDA-identification probe and ninja build should complete in 5-15 min.

If the build succeeds, paste the tail of its log (or say "build ok") and I'll walk you through freeing VRAM + running the two smoke tests. If it fails again, paste the error.
