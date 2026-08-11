# BUILD_LOG.md — OpenHands-Ext v1

Append-only. Newest entries at the bottom. Do not edit prior entries. Timestamps in
America/Detroit (`EDT` / `EST`).

---

## 2026-08-10 23:19 EDT — Repo bootstrap

- **Stage / plugin / port:** Pre-Phase -1 · repo initialization
- **What changed:** Created `rmholston420/openhands-ext-v1` (private, MIT-licensed), committed initial README, Python+Node `.gitignore`, and pushed `integration-execution-plan-v16.md` to `docs/specs/`.
- **Files touched:** `README.md`, `.gitignore`, `docs/specs/integration-execution-plan-v16.md`
- **Ports / adapters affected:** none
- **PORTING_LEDGER / ADR updated:** —
- **Stop-condition status:** met (repo exists, spec pushed)

## 2026-08-10 23:24 EDT — Version baseline live-fetched

- **Stage / plugin / port:** Pre-Phase -1 · version currency check (author-side)
- **What changed:** Live-fetched current tags for openhands-sdk/tools/workspace/agent-server, OpenHands app, agent-canvas (GitHub + npm), llama.cpp, and vLLM. Committed `VERSIONS.lock` with fetch timestamp `2026-08-11T03:24:45Z`. This is a freshness reference — Colossus MUST re-fetch at Phase -1.
- **Files touched:** `VERSIONS.lock`
- **Ports / adapters affected:** none
- **PORTING_LEDGER / ADR updated:** —
- **Stop-condition status:** met (baseline recorded; Phase -1 gate still ahead on Colossus)

## 2026-08-10 23:24 EDT — Repo scaffolding + operational logs

- **Stage / plugin / port:** Pre-Phase -1 · directory structure
- **What changed:** Created directory scaffolding for all downstream phases (`adrs/`, `mcp-servers/{gpu-monitor,inference-backends,episodic-memory,repograph}`, `bench/{fast,medium,full,lib,schema,rubrics,results}`, `hooks/pre-commit`, `security/blast-radius`, `canvas-panel/repograph`, `scripts`, `config`, `docs/verification`). Initialized the four operational logs (`BUILD_LOG.md`, `DEBUG_LOG.md`, `KNOWN_ISSUES.md`, `SESSION_HANDOFF.md`) and `PORTING_LEDGER.md`.
- **Files touched:** entire scaffold, four operational logs, `PORTING_LEDGER.md`
- **Ports / adapters affected:** none yet (structure only)
- **PORTING_LEDGER / ADR updated:** initialized (empty)
- **Stop-condition status:** met

## 2026-08-10 23:24 EDT — ADR-0001 repo bootstrap decision

- **Stage / plugin / port:** Pre-Phase -1 · governance
- **What changed:** Authored `adrs/ADR-0001-repo-bootstrap.md` recording the decision to bootstrap a fresh private repo (rather than fork Forge-OH or OH-GUI) and to commit only the v16 spec on the first push. Alternatives (fork, monorepo-of-monorepos) explicitly rejected.
- **Files touched:** `adrs/ADR-0001-repo-bootstrap.md`, `adrs/README.md`
- **Ports / adapters affected:** —
- **PORTING_LEDGER / ADR updated:** ADR-0001 filed
- **Stop-condition status:** met

## 2026-08-10 23:24 EDT — ADR-0002 LocalWorkspace guard = pre-commit hook

- **Stage / plugin / port:** Phase 1 · governance
- **What changed:** Authored `adrs/ADR-0002-localworkspace-guard-pre-commit.md`. Decision: enforce spec §Phase 1's zero-LocalWorkspace policy via a local pre-commit hook, not a GitHub Actions workflow — aligns with space custom instructions ("no GitHub-native CI dependencies unless I explicitly ask") and the spec's local-first posture. GitHub Actions rejected as introducing cloud CI dependency.
- **Files touched:** `adrs/ADR-0002-localworkspace-guard-pre-commit.md`, `adrs/README.md`, `hooks/pre-commit/no-localworkspace.sh`, `scripts/install-hooks.sh`
- **Ports / adapters affected:** —
- **PORTING_LEDGER / ADR updated:** ADR-0002 filed
- **Stop-condition status:** met

## 2026-08-10 23:24 EDT — Donor repo inventory + PORTING_LEDGER pre-draft

- **Stage / plugin / port:** Pre-Phase -1 · port-source inventory
- **What changed:** Cloned `rmholston420/oh-gui` (HEAD `ef3ac1a5`) and `rmholston420/Forge-OH` (HEAD `df73ebed`). Verified MIT license on both. Located every file the v16 spec ports from and recorded per-file SHAs. Pre-drafted `PORTING_LEDGER.md` entries as `PLANNED` for: gpu_monitor (Phase 5), episodic_memory + inference_backends + openhands_client + event_normalize (Phase 6), repograph (index/parser/store, Phase 7), OH-GUI blast-radius logic (Phase 8).
- **Files touched:** `PORTING_LEDGER.md`, `docs/donor-inventory.md`
- **Ports / adapters affected:** GPUTelemetry, InferenceBackendHealth, EpisodicMemory, RepoGraph, SecurityAnalyzer (all PLANNED, not yet vendored)
- **PORTING_LEDGER / ADR updated:** ledger seeded with 9 PLANNED entries
- **Stop-condition status:** met (pre-Phase-1 scope complete; Colossus-side execution remains)

## 2026-08-10 23:26 EDT — Pre-commit hook allow-list extended to cover docs/verification/

- **Stage / plugin / port:** Phase 1 · pre-commit hook (ADR-0002)
- **What changed:** Added `docs/verification/` to the allow-list regex in `hooks/pre-commit/no-localworkspace.sh`. The verification checklist quotes spec Phase 1 verbatim ("Zero LocalWorkspace") and was blocking the initial commit as a false positive. See `DEBUG_LOG.md` 2026-08-10 23:26 EDT.
- **Files touched:** `hooks/pre-commit/no-localworkspace.sh`, `DEBUG_LOG.md`
- **Ports / adapters affected:** —
- **PORTING_LEDGER / ADR updated:** — (ADR-0002 language unchanged; allow-list is implementation detail)
- **Stop-condition status:** met (hook now green, commit proceeds)

## 2026-08-10 23:45 EDT — ADR-0003 mirror discipline + Phase -1 executable scripts

- **Stage / plugin / port:** Pre-Phase -1 · governance + Phase -1 execution scaffolding
- **What changed:**
  - Filed `adrs/ADR-0003-repo-colossus-mirror-discipline.md` (three-category rule: tracked / regenerable-by-script / ephemeral; HARD sync strictness).
  - Added `hooks/pre-commit/dispatch.sh` (chains all pre-commit checks).
  - Added `hooks/pre-commit/size-guard.sh` (10 MiB single-file limit, empty allow-list — ADR-0003).
  - Added `hooks/pre-push/no-diverged-remote.sh` (rejects push if origin/main advanced — ADR-0003).
  - Extended `scripts/install-hooks.sh` to install dispatcher + pre-push hook.
  - Added `scripts/session-start.sh` and `scripts/session-end.sh` (HARD-fail sync gates).
  - Added `scripts/bootstrap-venv.sh` (idempotent .venv creation; uses modern `hf` CLI; NO `exec > >(tee)` — see DEBUG_LOG 23:38 EDT).
  - Added `scripts/build-llama-cpp.sh` (CUDA 12.8 + gcc-13 host compiler + SM_120; re-fetches latest tag live).
  - Added `scripts/install-oh-sdk.sh` (re-fetches PyPI versions live per spec §-1.1; records to `bench/results/`).
  - Added `scripts/install-vllm.sh` (re-fetches latest vLLM version live).
  - Added `scripts/pull-models.sh` (Qwen2.5-1.5B-Instruct GGUF Q4_K_M + safetensors snapshot).
  - Added `scripts/smoke-test-llama-cpp.sh` (spec §-1.5 SDK-to-runtime, port 8082).
  - Added `scripts/smoke-test-vllm.sh` (spec §-1.5 SDK-to-runtime, port 8083).
  - Extended `.gitignore` to cover `vendor/` and `bench/results/*.log`.
  - Extended `hooks/pre-commit/no-localworkspace.sh` allow-list for new hook + script paths.
- **Files touched:** `adrs/ADR-0003-repo-colossus-mirror-discipline.md`, `adrs/README.md`, `hooks/pre-commit/{dispatch,size-guard,no-localworkspace}.sh`, `hooks/pre-push/no-diverged-remote.sh`, `scripts/{install-hooks,session-start,session-end,bootstrap-venv,build-llama-cpp,install-oh-sdk,install-vllm,pull-models,smoke-test-llama-cpp,smoke-test-vllm}.sh`, `.gitignore`
- **Ports / adapters affected:** none (governance + execution scaffolding only)
- **PORTING_LEDGER / ADR updated:** ADR-0003 filed
- **Stop-condition status:** met (Colossus can now run Phase -1 as a sequence of idempotent script invocations, each with hard sync + regeneration guarantees)

## 2026-08-11 00:15 EDT — Corrective Phase -1 fixes: CUDA-13 pin, vLLM VRAM preflight, session-end truth gate

- **Stage / plugin / port:** Phase -1 · llama.cpp build + vLLM smoke test + session-end truth
- **What changed:**
  - Filed **ADR-0004** pinning llama.cpp build to `/usr/local/cuda-13.0` + gcc-13 + SM_120 (see DEBUG_LOG.md 2026-08-11 00:12 EDT — glibc 2.43 vs CUDA 12.8 `math_functions.h` conflict).
  - Amended **ADR-0003** with the commit-message truth gate; documented that commit 535bc35's subject was inaccurate.
  - Rewrote `scripts/build-llama-cpp.sh` — CUDA_ROOT=/usr/local/cuda-13.0, prepends CUDA-13 to PATH/CUDA_PATH/LD_LIBRARY_PATH, records status:pass metadata JSON to bench/results/.
  - Rewrote `scripts/smoke-test-vllm.sh` — nvidia-smi VRAM preflight (refuses < VLLM_MIN_FREE_GIB=20 GiB free), env overrides (VLLM_GPU_MEM_UTIL default 0.55, VLLM_MAX_MODEL_LEN 4096, VLLM_STARTUP_TIMEOUT 240s), status:pass|fail in metadata JSON, actionable failure guidance.
  - Rewrote `scripts/session-end.sh` — reads smoke-test JSON status, refuses "all green"/"complete" subjects when smokes aren't pass, appends `smoke.*` truth lines to every commit body, ALLOW_GREEN_OVERRIDE=1 bypass documented but discouraged.
  - Added `status: pass` field to `scripts/smoke-test-llama-cpp.sh` metadata JSON so the truth gate can read it uniformly.
  - Added a new `scripts/pull-docs.sh` (previously drafted in the sandbox; unchanged in this commit — it's the still-untracked file for the docs-collection task that will run after Phase -1 is genuinely green).
- **Files touched:**
  - `adrs/ADR-0004-llama-cpp-cuda-13-pin.md` (new)
  - `adrs/ADR-0003-repo-colossus-mirror-discipline.md` (amendment header + status → Amended)
  - `adrs/README.md` (index row for ADR-0004; ADR-0003 status → Amended)
  - `scripts/build-llama-cpp.sh` (rewrite)
  - `scripts/smoke-test-vllm.sh` (rewrite)
  - `scripts/smoke-test-llama-cpp.sh` (status field only)
  - `scripts/session-end.sh` (rewrite: truth gate)
  - `scripts/pull-docs.sh` (new, unchanged since prior session)
  - `DEBUG_LOG.md` (three appended entries for 2026-08-11 00:12 EDT)
  - `SESSION_HANDOFF.md` (rewritten below)
- **Ports / adapters affected:** none — governance + toolchain only.
- **PORTING_LEDGER / ADR updated:** ADR-0003 amended, ADR-0004 ratified. PORTING_LEDGER.md not updated in this commit; a llama.cpp entry will land after the CUDA-13 build actually succeeds on Colossus.
- **Stop-condition status:** blocked pending re-execution on Colossus. Phase -1 §-1 Verification table is NOT green until both smoke tests emit `status: pass` JSONs.

## 2026-08-11 00:20 EDT — CUDA header patch for glibc 2.43 rsqrt/rsqrtf

- **Stage / plugin / port:** Phase -1 · llama.cpp CUDA build
- **What changed:** Added `scripts/patch-cuda-headers.sh` — idempotent, guarded, in-place patch of `crt/math_functions.h` to add `noexcept(true)` to rsqrt/rsqrtf (and cospi/sinpi fallbacks for CUDA 12.8) under `#if __GLIBC_MINOR__ >= 42/41` guards. Backs up original. `build-llama-cpp.sh` step 3.5 invokes it (sudo -E fallback). Removed deprecated `-DLLAMA_CURL=ON` from cmake configure (llama.cpp b6773+ ignores it). Amended ADR-0004: CUDA-13 pin alone is necessary but not sufficient; header patch is the completing measure.
- **Files touched:**
  - `scripts/patch-cuda-headers.sh` (new, 200 lines, tested against synthetic header for dry-run, real-apply, idempotency, restore-and-repatch)
  - `scripts/build-llama-cpp.sh` (step 3.5 + removed LLAMA_CURL)
  - `DEBUG_LOG.md` (rsqrt entry)
- **Ports / adapters affected:** none.
- **PORTING_LEDGER / ADR updated:** ADR-0004 amended below.
- **Stop-condition status:** blocked pending Colossus re-run. Phase -1 §-1 remains NOT green.

## 2026-08-11 00:25 EDT — CUDA header patch: perm preservation + probe fix

- **Stage / plugin / port:** Phase -1 · llama.cpp CUDA build
- **What changed:**
  - `scripts/patch-cuda-headers.sh`: preserves original file mode+owner via stat, tempfile lives in same directory as target for atomic mv, defensive `chmod 0644` after swap, idempotent path now also detects and repairs wrong-mode already-patched headers, compile-only (`-c`) verification probe with SUDO_USER drop-down.
  - `scripts/build-llama-cpp.sh`: `sudo CUDA_ROOT=... bash ...` invocation form (strict sudoers ignores `-E`).
  - `DEBUG_LOG.md`: two entries for the 0600 perm bug and the false-negative link-error probe.
- **Files touched:**
  - `scripts/patch-cuda-headers.sh`
  - `scripts/build-llama-cpp.sh`
  - `DEBUG_LOG.md`
  - `SESSION_HANDOFF.md`
- **Ports / adapters affected:** none.
- **PORTING_LEDGER / ADR updated:** —
- **Stop-condition status:** blocked pending Colossus re-run.

## 2026-08-11 00:20 EDT — llama.cpp built + smoke green (Phase -1 §-1.5 llama.cpp side)

- **Stage / plugin / port:** Phase -1 · §-1.5 llama.cpp smoke test
- **What changed:** With the CUDA-13 pin + `patch-cuda-headers.sh` fix (perm preservation) in place, `scripts/build-llama-cpp.sh` completed in 185 s on Colossus. Tag b10356 @ `0666ad2b2`, `bin/llama-server` links cleanly against `libggml-cuda.so.0.19.0` (65 MB). `scripts/smoke-test-llama-cpp.sh` then passed: 18 ms prompt (2328 tok/s), 26.7 ms/16 tokens (599 tok/s decode) on Qwen 1.5B q4_k_m. GPU peaked at 30735/32607 MiB during inference — confirms CUDA backend active. Assistant reply: "Hello! I am running on the RTX 5090." Metadata JSON `bench/results/phase-neg-1-smoke-llama-cpp-20260811T042026Z.json` (status: pass) written.
- **Files touched:** none (Colossus-side execution only; scripts already committed).
- **Ports / adapters affected:** none (Phase -1 pre-port scaffolding).
- **PORTING_LEDGER / ADR updated:** —
- **Stop-condition status:** llama.cpp side of §-1.5 green. vLLM side still blocked.

## 2026-08-11 00:30 EDT — vLLM smoke green (Phase -1 §-1.5 vLLM side, flashinfer Blackwell workaround)

- **Stage / plugin / port:** Phase -1 · §-1.5 vLLM smoke test
- **What changed:** Diagnosed engine-core init crash as flashinfer 0.6.16 vs SM_120/CUDA<12.9 incompatibility (see DEBUG_LOG 2026-08-11 00:27 EDT and ADR-0005). Baked `VLLM_USE_FLASHINFER_SAMPLER=0` default-if-unset `export` into `scripts/smoke-test-vllm.sh` right after `cd $REPO_ROOT`. Re-ran smoke on Colossus with the env override first (proof) then with the baked-in export (final): health OK 30 s, chat completion returned ("Hello! I am currently running on an NVIDIA RTX 5090 GPU."), 18.86 GiB GPU used, `bench/results/phase-neg-1-smoke-vllm-20260811T042731Z.json` written with status: pass.
- **Files touched:**
  - `scripts/smoke-test-vllm.sh` (workaround export)
  - `adrs/ADR-0005-flashinfer-blackwell-workaround.md` (new)
  - `adrs/README.md` (index row added)
  - `DEBUG_LOG.md` (root-cause entry)
  - `SESSION_HANDOFF.md` (overwritten)
- **Ports / adapters affected:** none (Phase -1 pre-port scaffolding).
- **PORTING_LEDGER / ADR updated:** ADR-0005 authored + indexed. PORTING_LEDGER unchanged (no vendored component).
- **Stop-condition status:** **§-1.5 fully green.** Both smokes (llama.cpp + vLLM) report status: pass. Phase -1 §-1 Verification table is truly green — session-end.sh truth gate will now permit a "green" commit subject.

## 2026-08-11 00:52 EDT — Phase 0 prereq: 7-category schema + tier-runner scaffold + flashinfer JIT-cache adopted (ADR-0006, retires ADR-0005)

- **Stage / plugin / port:** Phase 0 · pre-tier scaffolding + Phase -1 §-1.5 flashinfer resolution
- **What changed:**
  1. **7-category JSON schema per v16 spec §0.0c** — `bench/schema/run.schema.json` (Draft 2020-12), `bench/schema/run.py` (dataclasses + enums + validator), `bench/schema/__init__.py`, `bench/schema/README.md`. All seven categories required keys; category-2/3/4/6 nullable; rubric/notes/optional latency fields nullable via `oneOf`.
  2. **Tier-runner scaffold** — `scripts/benchmark-tier-runner.py` with §0.0a denominator-exclusion helper, §0.0a latency-must-be-measured guard, §0.0a rubric-lock guard, §0.1/0.3 tier-scope guard for category 6, §0.0b open-pool guard, §0.1 runtime-version-regression flag path.
  3. **Schema smoke tests** — `bench/tests/test_schema.py` (round-trip + validation).
  4. **flashinfer SM_120 fix** — ADR-0005 retired, ADR-0006 ratified (`flashinfer-jit-cache==0.6.16.post3+cu129`). `scripts/smoke-test-vllm.sh` unconditional workaround export removed. `scripts/install-vllm.sh` extended to install the matching JIT cache.
- **Files touched:**
  - `bench/schema/{run.schema.json,run.py,__init__.py,README.md}`
  - `bench/tests/{__init__.py,test_schema.py}`
  - `scripts/benchmark-tier-runner.py`
  - `scripts/smoke-test-vllm.sh` (workaround retired)
  - `scripts/install-vllm.sh` (JIT-cache install added)
  - `adrs/ADR-0005-flashinfer-blackwell-workaround.md` (amended · superseded)
  - `adrs/ADR-0006-flashinfer-jit-cache-cu129.md` (new)
  - `adrs/README.md` (index updates)
  - `DEBUG_LOG.md` (retirement entry)
- **Ports / adapters affected:** none (scaffolding + venv config; no formal ports touched).
- **PORTING_LEDGER / ADR updated:** ADR-0005 amended; ADR-0006 authored + indexed. PORTING_LEDGER unchanged (no vendored component adopted or replaced).
- **Stop-condition status:** Phase 0 scaffolding in place; harness/loader/task-set work remains. Phase -1 §-1.5 vLLM smoke re-verified without any workaround (`bench/results/phase-neg-1-smoke-vllm-20260811T044948Z.json`).
