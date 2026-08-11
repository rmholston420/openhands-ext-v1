# DEBUG_LOG.md — OpenHands-Ext v1

Append-only. Newest entries at the bottom. Do not edit prior entries.

**Hard rule (space custom instructions):** Before investigating any new error, `grep -in
"<symptom keywords>" DEBUG_LOG.md` first. If a matching or similar symptom exists, reuse
the recorded fix instead of re-diagnosing.

Entry format:

```markdown
## <YYYY-MM-DD HH:MM EDT> — <symptom summary>

- **Symptom:** <exact error text / behavior observed>
- **Affected stage / plugin / port:** <e.g. Phase 0.1 · llama.cpp coder cell>
- **Root cause:** <what was actually wrong>
- **Fix applied:** <what was changed>
- **Files changed:** <bullet list>
- **Related BUILD_LOG entry:** <timestamp or —>
```

---

## 2026-08-10 23:26 EDT — Pre-commit hook rejected initial commit (verification-matrix.md quotes LocalWorkspace)

- **Symptom:** `bash scripts/install-hooks.sh` self-check exited 1 with message "LocalWorkspace reference detected (mode: staged)" pointing at `docs/verification/verification-matrix.md:14` — a spec-verbatim quote in the Phase 1 row.
- **Affected stage / plugin / port:** ADR-0002 · pre-commit hook allow-list
- **Root cause:** Initial allow-list included `docs/specs/` and `docs/donor-inventory.md` but not `docs/verification/`, so the verification checklist (which necessarily quotes spec Phase 1's "Zero LocalWorkspace" language) triggered a false positive.
- **Fix applied:** Added `docs/verification/` to the allow-list regex in `hooks/pre-commit/no-localworkspace.sh`. The category of file is documentation that quotes spec sections verbatim — same rationale as `docs/specs/` and `adrs/`. Not a real policy violation.
- **Files changed:** `hooks/pre-commit/no-localworkspace.sh`
- **Related BUILD_LOG entry:** 2026-08-10 23:24 EDT (ADR-0002 filing)

## 2026-08-10 23:38 EDT — Phase -1 prep script killed the interactive bash shell

- **Symptom:** Colossus reported that pasting a Phase -1 prep script into an interactive `bash` shell caused the shell to die mid-script. The script had partially succeeded (apt install of cmake/ninja/gcc-13/g++-13 completed, `.venv/` created, pip upgraded, huggingface_hub installed) before the terminal was killed. Log at `/tmp/phase-1-prep-1786419502.log` shows the last visible line was a `hf`/`huggingface-cli` deprecation warning.
- **Affected stage / plugin / port:** Pre-Phase -1 · Colossus session-startup scripts
- **Root cause:** The script used two anti-patterns at interactive scope: (1) `set -euo pipefail` at the top of a pasted block runs in the *interactive* shell, so any non-zero exit terminates it; (2) `exec > >(tee -a "$LOG") 2>&1` redirects the interactive shell's own stdout/stderr through a subprocess `tee`, so when the pipeline received a nonzero exit under `pipefail`, the shell tore down its own fd redirection and died. The `huggingface-cli`/`hf_transfer` deprecation warnings from `huggingface_hub 1.27.0` were the likely trigger (they don't cause a nonzero exit themselves but the extras `[cli,hf_transfer]` are gone in 1.x, and any subsequent command that errored propagated into the killed tee pipeline).
- **Fix applied:** All new operational scripts under `scripts/*.sh` follow four rules: (a) instruct the user to invoke via `bash scripts/foo.sh` — never paste raw `set -e` blocks into an interactive shell; (b) redirect the *inside* of the script with `{ ...; } 2>&1 | tee "$LOG"` scoped to a single block, never `exec` at top-level; (c) use the modern `hf` CLI from `huggingface_hub>=1.0`, drop the deprecated `HF_HUB_ENABLE_HF_TRANSFER` env var; (d) each script is idempotent so a re-run after a crash resumes cleanly.
- **Files changed:** `scripts/bootstrap-venv.sh` (new, replaces the killed inline script), plus all other new `scripts/*.sh` files follow the same discipline. Added the constraint as a documented design principle in the top comment of `scripts/bootstrap-venv.sh`.
- **Related BUILD_LOG entry:** 2026-08-10 23:45 EDT (ADR-0003 mirror discipline + Phase -1 executable scripts)

## 2026-08-11 00:12 EDT — llama.cpp CUDA-12.8 build fails on Ubuntu 26.04 glibc 2.43 (math.h noexcept conflict)

- **Symptom:** `bash scripts/build-llama-cpp.sh` targeting `/usr/local/cuda-12.8` (nvcc 12.8.93) failed at the CMake CUDA-compiler-identification step, before any real llama.cpp source was compiled. Six errors of the form:

    /usr/include/x86_64-linux-gnu/bits/mathcalls.h(83): error: exception
    specification is incompatible with that of previous function "cospi"
    (declared at line 2601 of
     /usr/local/cuda-12.8/bin/../targets/x86_64-linux/include/crt/math_functions.h)

  for `cospi`, `sinpi`, `rsqrt` and their `f` variants. CMake output: "6 errors detected in the compilation of CMakeCUDACompilerId.cu". `ggml/src/ggml-cuda/CMakeLists.txt:59 (enable_language)` bailed. Configure aborted before any object file was produced.
- **Affected stage / plugin / port:** Phase -1 · llama.cpp build · CUDA toolchain choice
- **Root cause:** Ubuntu 26.04's glibc 2.43 declares the trigonometric-companion math functions with `noexcept(true)` exception specifications. CUDA 12.8's `/usr/local/cuda-12.8/targets/x86_64-linux/include/crt/math_functions.h` declares the same names without matching exception specifications. `cudafe++` treats the mismatch as a hard error under C++17. This is a known, widely reported glibc ≥ 2.41 vs CUDA ≤ 12.8 header conflict. It has nothing to do with SM_120, gcc-13-vs-gcc-15 host-compiler selection, or Blackwell — the errors fire during the CMake compiler-identification probe long before any arch flag is exercised.
- **Fix applied:** Switched `scripts/build-llama-cpp.sh` to `/usr/local/cuda-13.0` (nvcc 13.0.88). CUDA 13.0 ships updated `math_functions.h` headers that match glibc 2.43 prototypes. Also prepends the cuda-13.0 tree to `PATH`, `CUDA_PATH`, and `LD_LIBRARY_PATH` so child processes (ptxas, cuBLAS lookups) also use 13.0 rather than the 12.8 system default. Host compiler stays gcc-13 (CUDA 13 supports gcc-13/14/15). SM_120 unchanged. Decision recorded in ADR-0004.
- **Files changed:** `scripts/build-llama-cpp.sh`, `adrs/ADR-0004-llama-cpp-cuda-13-pin.md` (new), `adrs/README.md` (index).
- **Related BUILD_LOG entry:** 2026-08-11 00:15 EDT

## 2026-08-11 00:12 EDT — vLLM engine-core init crashed: "Free memory on device cuda:0 (2.49/31.39 GiB) < desired 18.84 GiB"

- **Symptom:** `bash scripts/smoke-test-vllm.sh` invoked `vllm serve` at `--gpu-memory-utilization 0.6` on Qwen2.5-1.5B-Instruct. The APIServer reached `wait_for_engine_startup` and the EngineCore subprocess raised:

    ValueError: Free memory on device cuda:0 (2.49/31.39 GiB) on startup
    is less than desired GPU memory utilization (0.6, 18.84 GiB). Decrease
    GPU memory utilization or reduce GPU memory used by other processes.

  raised at `.venv/lib/python3.14/site-packages/vllm/v1/worker/utils.py:419` (`request_memory`) → `vllm/v1/worker/gpu_worker.py:396` (`init_device`). APIServer then re-raised `RuntimeError: Engine core initialization failed`.
- **Affected stage / plugin / port:** Phase -1 · vLLM smoke test · GPU memory preflight
- **Root cause:** Not a vLLM bug and not a configuration bug per se — ~29 GiB of the 32 GiB on cuda:0 was already occupied at the moment `vllm serve` started. On a Kubuntu desktop workstation this is usually the compositor + browser + IDE + any orphaned CUDA processes from prior runs. The `--gpu-memory-utilization 0.6` flag asks for ~19 GiB, which is larger than the ~2.5 GiB actually free, so vLLM refuses.
- **Fix applied (two-part):**
  - Preventive: `scripts/smoke-test-vllm.sh` now performs an `nvidia-smi` **preflight** before spawning `vllm serve`. Refuses to proceed if free VRAM on cuda:0 < `VLLM_MIN_FREE_GIB` (default 20). On refusal it lists the current top VRAM consumers and suggests three remedies (close apps, lower the target with `VLLM_GPU_MEM_UTIL=0.3 VLLM_MIN_FREE_GIB=10`, or forcefully kill GPU users with `fuser -k /dev/nvidia*`).
  - Corrective: lowered the default `--gpu-memory-utilization` from `0.6` to `0.55` (roughly 17.3 GiB target on a 32 GiB card) so ordinary desktop VRAM overhead doesn't push us over. Both values are env-overridable (`VLLM_GPU_MEM_UTIL`, `VLLM_MIN_FREE_GIB`). Startup timeout bumped from 180 s to 240 s to survive slower cold starts observed on the Blackwell wheel path.
- **Files changed:** `scripts/smoke-test-vllm.sh` (rewritten with preflight, env-override, startup-timeout bump, `status: pass|fail` in metadata JSON), `scripts/smoke-test-llama-cpp.sh` (added matching `status: pass` field so `session-end.sh` truth gate can read both).
- **Related BUILD_LOG entry:** 2026-08-11 00:15 EDT

## 2026-08-11 00:12 EDT — Commit 535bc35 was pushed with misleading subject "§-1 Verification table all green"

- **Symptom:** `session-end.sh -m "phase(-1): §-1 Verification table all green"` produced a commit + push where the subject asserted Phase -1 verification passed, but at commit time the two smoke tests had actually just failed: `smoke-test-llama-cpp.sh` bailed with "llama-server not built" (build had errored) and `smoke-test-vllm.sh` bailed with the OOM ValueError above. Only the *installer* JSONs (`phase-neg-1-oh-sdk-*.json`, `phase-neg-1-vllm-*.json`) landed under `bench/results/`.
- **Affected stage / plugin / port:** Pre-Phase -1 · `scripts/session-end.sh` · commit-message honesty
- **Root cause:** `session-end.sh` accepted `-m "$msg"` as literal truth without cross-checking against the on-disk smoke-test evidence.
- **Fix applied:** ADR-0003 amendment (filed 2026-08-11). `session-end.sh` now scans `bench/results/phase-neg-1-smoke-{llama-cpp,vllm}-*.json` for the most recent `status` field and (a) refuses any commit subject claiming green/complete when both are not `pass`, (b) appends `smoke.llama-cpp: <status>` and `smoke.vllm: <status>` lines to every commit body. Bypass via `ALLOW_GREEN_OVERRIDE=1` is available but leaves an explicit marker. Commit 535bc35 is NOT rewritten (never rewrite pushed history); a corrective follow-up commit and this DEBUG_LOG entry are the audit trail.
- **Files changed:** `scripts/session-end.sh`, `adrs/ADR-0003-repo-colossus-mirror-discipline.md` (amendment block), `scripts/smoke-test-llama-cpp.sh` (added `status: pass` field), `scripts/smoke-test-vllm.sh` (added `status: pass` field).
- **Related BUILD_LOG entry:** 2026-08-11 00:15 EDT

## 2026-08-11 00:15 EDT — CUDA 13.0 still fails glibc 2.43 on rsqrt/rsqrtf

- **Symptom:** `/usr/include/x86_64-linux-gnu/bits/mathcalls.h(206): error: exception specification is incompatible with that of previous function "rsqrt" (declared at line 629 of /usr/local/cuda-13.0/bin/../targets/x86_64-linux/include/crt/math_functions.h)` — plus the same for `rsqrtf` at line 653. Emitted by cudafe++ during CMake's CUDA-compiler-identification probe. 2 errors instead of the earlier 6 under CUDA 12.8.
- **Affected stage / plugin / port:** Phase -1 · llama.cpp CUDA build
- **Root cause:** CUDA 13.0.88 fixed `cospi`/`sinpi` `noexcept` decls upstream but not `rsqrt`/`rsqrtf`. Ubuntu 26.04 glibc 2.43 declares both with `noexcept(true)`; CUDA's `crt/math_functions.h` still declares them without any exception spec. cudafe++ under C++17 treats this as a hard error. My ADR-0004 hypothesis (CUDA 13 alone resolves the issue) was PARTIAL — it eliminated 4 of 6 mismatches but not the last two.
- **Fix applied:** New `scripts/patch-cuda-headers.sh` — idempotent in-place patch that wraps `rsqrt`, `rsqrtf`, and (for CUDA-12.8 fallback) `cospi`/`cospif`/`sinpi`/`sinpif` decls in `#if __GLIBC_MINOR__ >= 42` (rsqrt) / `>= 41` (cospi/sinpi) guards that add `noexcept(true)`. Backs up original to `<header>.orig`. Marker line prevents double-patching. `build-llama-cpp.sh` step 3.5 invokes it (with `sudo -E` fallback if header is root-owned). Approach documented in llama.cpp's own `docs/build.md` ("Fixing Compatibility Issues with Old CUDA and New glibc") and the joanbm Gentoo gist for glibc 2.42.
- **Files changed:**
  - `scripts/patch-cuda-headers.sh` (new)
  - `scripts/build-llama-cpp.sh` (added step 3.5 call, removed deprecated `-DLLAMA_CURL=ON`)
- **Related BUILD_LOG entry:** 2026-08-11 00:20 EDT
- **Supersedes hypothesis in:** 2026-08-11 00:12 EDT (CUDA-12.8/glibc entry — the "fix" of moving to CUDA 13 was insufficient on its own)
