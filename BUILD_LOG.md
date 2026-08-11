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

## 2026-08-11 00:57 EDT — Phase 0 §0.0b candidate registry + table-driven pull-models.sh

- **Stage / plugin / port:** Phase 0 · §0.0b candidate pool acquisition
- **What changed:**
  1. **`bench/candidates/registry.json`** — new file, authoritative candidate registry for Phase 0. 9 candidates across coder/planner/embedder pools. Every entry lists `slug`, `hf_repo`, optional `hf_files`, `format`, `runtime`, `role_pool` (which pools the candidate participates in — coder+planner sharing enforces spec §0.0b's no-double-download rule), `approx_size_gib`, and notes.
  2. **Old `pull-models.sh` renamed to `pull-smoke-model.sh`** — preserves the Phase -1 smoke fetch for regression re-runs; unchanged content.
  3. **New `scripts/pull-models.sh`** — table-driven, `--role coder|planner|embedder|all`, `--dry-run` supported. Live-resolves each HF repo's `main` revision, computes a rollup SHA256 of key files, appends to `models/manifest.json` with `resolved_revision`, `files_requested`, `actual_size_bytes`, `rollup_sha256`, `local_dir`, `resolved_at_utc`, `source_url`. Idempotent: skip on complete local dir, replace-in-place on re-download. Disk preflight refuses to start if free < 1.25× approx sum. Per-role snapshot vs single-file mode selected from `hf_files` in the registry. For Qwen embedding GGUF repos, prefers `Qwen3-Embedding-<size>-Q8_0.gguf` and falls back to full snapshot.
- **Canonical HF repo IDs baked in (verified via Perplexity web search 2026-08-11):**
  - `Qwen/Qwen3.6-27B`, `unsloth/Qwen3.6-27B-GGUF` (`Qwen3.6-27B-Q6_K.gguf`), `Intel/Qwen3.6-27B-int4-AutoRound`
  - `Qwen/Qwen3.6-35B-A3B`, `unsloth/Qwen3.6-35B-A3B-GGUF` (`Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`), `QuantTrio/Qwen3.6-35B-A3B-AWQ`
  - `cpatonn/Qwen3-30B-A3B-Thinking-2507-AWQ-4bit` (chosen over 235B — that variant does not fit 32 GiB VRAM)
  - `Qwen/Qwen3-Embedding-0.6B`, `Qwen/Qwen3-Embedding-0.6B-GGUF`, `Qwen/Qwen3-Embedding-4B`, `Qwen/Qwen3-Embedding-4B-GGUF`
- **Files touched:**
  - `bench/candidates/registry.json` (new)
  - `scripts/pull-models.sh` (rewritten)
  - `scripts/pull-smoke-model.sh` (renamed from prior `pull-models.sh`)
- **Ports / adapters affected:** none (Phase 0 pre-tier scaffolding).
- **PORTING_LEDGER / ADR updated:** none. Registry is authored code, not a vendored port. No ADR required — candidate-list content is deliberately hot-editable per spec §0.0b (never pre-narrow the pool).
- **Stop-condition status:** Phase 0 pool-acquisition machinery in place; downloads not yet run.

## 2026-08-11 01:05 EDT — Phase 0 embedder pool downloaded + pull-models.sh polish

- **Stage / plugin / port:** Phase 0 · §0.0b candidate pool acquisition (embedder complete)
- **What changed:**
  1. **Embedder pool pulled on Colossus** (166 s wall). 4 candidates now on disk with pinned HF revisions:
     - `qwen3-embedding-0_6b-bf16` @ `97b0c614be4d` (1.21 GB, rollup `20eb5b26865a`)
     - `qwen3-embedding-0_6b-q8-gguf` @ `370f27d7550e` (639 MB, rollup `f6a9ca9ef8a4`)
     - `qwen3-embedding-4b-bf16` @ `5cf2132abc99` (8.06 GB, rollup `a5b2bd10961d`)
     - `qwen3-embedding-4b-q8-gguf` @ `f4602530db1d` (4.28 GB, rollup `4400f3a437bf`)
  2. **`scripts/pull-models.sh` polish:** replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` (Python 3.14 DeprecationWarning eliminated); added HF-auth soft-check warning when `HF_TOKEN` is not set and no cached token at `~/.cache/huggingface/token`, noting that the ~155 GiB coder+planner batch benefits from an authenticated session. Warning only — script still runs unauthenticated.
- **Files touched:**
  - `models/manifest.json` (created by first pull; not committed — see .gitignore)
  - `scripts/pull-models.sh` (utcnow deprecation + HF-auth warning)
- **Ports / adapters affected:** none.
- **PORTING_LEDGER / ADR updated:** none.
- **Stop-condition status:** Embedder-pool half of Phase 0 §0.0b complete. Coder + planner pools pending (~155 GiB).

## 2026-08-11 01:52 EDT — Coder + planner pools downloaded

- **Stage / plugin / port:** Phase 0 · §0.0b candidate pool acquisition (complete)
- **What changed:** Coder pool pulled (~1541 s wall) and planner pool pulled (~194 s wall). Full 10-candidate pool now resident on Colossus with pinned HF revisions recorded in `models/manifest.json`:
  - Coder (5): `qwen3_6-27b-q6k-gguf` @ `82d411acf4a0` (22.5 GB), `qwen3_6-27b-bf16` @ `6a9e13bd6fc8` (55.6 GB), `qwen3_6-27b-int4-autoround` @ `abc86de19eb1` (19.0 GB), `qwen3_6-35b-a3b-q4kxl-gguf` @ `a483e9e6cbd5` (22.4 GB), `qwen3_6-35b-a3b-awq` @ `119886a10723` (25.5 GB).
  - Planner (1 new; the 4 dual-role candidates already downloaded under coder): `qwen3-30b-a3b-thinking-2507-awq` @ `efd3cf20fe71` (18.1 GB).
- **Files touched:** `models/manifest.json` on Colossus (gitignored; not committed).
- **Ports / adapters affected:** none.
- **PORTING_LEDGER / ADR updated:** none.
- **Stop-condition status:** Phase 0 §0.0b candidate-pool acquisition COMPLETE for all three roles.

## 2026-08-11 01:52 EDT — Registry approx_size_gib calibration from measured manifest

- **Stage / plugin / port:** Phase 0 · §0.0b candidate registry maintenance
- **What changed:** Calibrated `approx_size_gib` in `bench/candidates/registry.json` against measured on-disk sizes recorded in `models/manifest.json`:
  - `qwen3_6-27b-int4-autoround`: 15 → 19 GiB
  - `qwen3_6-35b-a3b-q4kxl-gguf`: 20 → 22 GiB
  - `qwen3_6-35b-a3b-awq`: 20 → 25 GiB
  - `qwen3-30b-a3b-thinking-2507-awq`: 20 → 18 GiB
  Others already within ±1 GiB of measured. Notes updated to record the calibration date. This affects only the disk-preflight math in `pull-models.sh` (1.25× buffer); the pull was already successful under the old estimates.
- **Files touched:** `bench/candidates/registry.json`
- **Ports / adapters affected:** none.
- **PORTING_LEDGER / ADR updated:** none (registry is authored code, hot-editable per spec §0.0b).
- **Stop-condition status:** met.

## 2026-08-11 01:52 EDT — ADR-0007 filed; Fast-tier task sets + elimination rubric authored

- **Stage / plugin / port:** Phase 0.1 · Fast-tier methodology lock-in
- **What changed:**
  1. Filed **ADR-0007 — Fast-tier task authoring, sampling, and elimination-rubric methodology** (Ratified). Resolves two skill/spec conflicts: (a) llama.cpp cells use spec §0.1's uniform launch-flag sampling (Qwen planner preset); vLLM cells use per-role Qwen presets per-request from `local-llm-bench`. (b) Perplexity-gold-standard scoring is deferred to Medium tier — Fast tier is elimination-only per spec §0.1. Also ratifies a project-wide progress-visibility discipline for harness scripts (per-phase bookends, `[i/N]` prefixes, ≤10 s heartbeats on long phases, `PYTHONUNBUFFERED=1` on child processes).
  2. Wrote `bench/tasks/coder-fast.json` (5 synthetic tool-call probes: read_file, str_replace_editor, execute_bash, write_file, read→write chain — each with hard-coded expected tool sequence and file-state).
  3. Wrote `bench/tasks/planner-fast.json` (3 structured-plan prompts with fixed `{steps:[{id,desc,deps}]}` JSON schema; pass = valid JSON + DAG + no truncation at 4096 tokens).
  4. Wrote `bench/tasks/embedder-fast.json` (8 queries: identical-pair, orthogonal-pair, 6 realistic Forge-OH trajectory snippets; pass = identical cos ≥ 0.999, orthogonal cos ≤ 0.9, no null vectors).
  5. Wrote `bench/rubrics/fast-elimination.json` — timestamped elimination rubric (launch-failure, malformed-output >1, latency-outlier >5×, runtime-version-regression flag). Explicitly `scoring.enabled=false` with reference back to spec §0.1.
  6. Added progress-ticker output to `scripts/pull-models.sh` (`[i/N]` counter, per-candidate elapsed, cumulative batch elapsed, batch summary).
  7. Added progress-visibility clause to `scripts/benchmark-tier-runner.py` scaffold docstring (Guard #8) so the constraint travels with the code.
  8. Updated `adrs/README.md` index with ADR-0007 row.
- **Files touched:** `adrs/ADR-0007-fast-tier-task-methodology.md` (new), `adrs/README.md`, `bench/candidates/registry.json`, `bench/tasks/coder-fast.json` (new), `bench/tasks/planner-fast.json` (new), `bench/tasks/embedder-fast.json` (new), `bench/rubrics/fast-elimination.json` (new), `scripts/pull-models.sh`, `scripts/benchmark-tier-runner.py`.
- **Ports / adapters affected:** none.
- **PORTING_LEDGER / ADR updated:** ADR-0007 filed.
- **Stop-condition status:** Fast-tier task+rubric authoring complete. Next Phase 0.1 work item is implementing real serving in `scripts/benchmark-tier-runner.py` (replacing `build_dry_run_record` with a launcher that consumes the new task files and enforces the elimination rubric).

## 2026-08-11 02:10 EDT — Phase 0.1 real runner implemented (process-supervised)

- **Stage / plugin / port:** Phase 0.1 · Fast-tier benchmark runner
- **What changed:**
  1. Rewrote `scripts/benchmark-tier-runner.py` from scaffold into a thin CLI shim over new `bench/runner/` package. Real launch/probe/teardown loop, no more `build_dry_run_record` placeholder on the hot path.
  2. Runner adopts **inline Popen supervisor** design (not separate shell launchers). Rationale in ADR-0007 vs skill guidance: runner owns Popen as a child so `atexit`+SIGINT/SIGTERM handlers cleanly kill servers on any exit path, one log file per cell, no PID parsing brittleness, natural line-buffered tee. The four launcher scripts drafted earlier (`bench/launchers/*.sh`) were removed before commit — dead code, worse ownership semantics.
  3. New modules under `bench/runner/`:
     - `progress.py` — line-buffered timestamped `[i/N]` printer, per-phase context-manager with 5 s heartbeats (ADR-0007 §7).
     - `server.py` — `BaseServer` + `VLLMServer` + `LlamaCppServer`. Owns Popen, tees stdout to per-cell log file AND runner stdout with `[<cell_id>] ` prefix. Structured `ServerLaunchError` with reason enum (missing_binary / port_in_use / insufficient_vram / startup_timeout / early_exit) for R1/R4 tagging. Global `_LIVE` registry cleaned up via `atexit` and signal handlers.
     - `nvml.py` — background pynvml sampler at 250 ms interval; edge-triggered throttle counter; `nvml_coverage_pct` computed from `samples / (samples + failed_samples)`. Graceful no-op when pynvml is unavailable.
     - `probes.py` — `probe_planner` (raw `/v1/chat/completions` + JSON extraction + jsonschema + DAG check), `probe_embedder` (single `/v1/embeddings` batch call + cosine identical/orthogonal probes + norm check), `probe_coder` (OpenHands-SDK path stubbed with `NotImplementedError`; runtime falls back to raw tool-call `/v1/chat/completions` probe and tags the cell `degraded: openhands-sdk unavailable`). Per §0.0a, malformed calls stay in the denominator.
     - `candidates.py` — expands `bench/candidates/registry.json` × `models/manifest.json` into concrete cells; filters oversized models unless `include_oversized=True`; expands embedder role across `{gpu, cpu}` axis per spec §0.1.
     - `main.py` — end-to-end tier orchestration: guard checks (open-pool §0.0b, rubric-lock §0.0a, planner requires rubric), per-cell dispatch (launch → NVML start → probe → NVML stop → teardown), rubric R1/R2/R3/R4 application, `BenchRun` construction, schema validation before write.
  4. Added `bench/tasks/README.md` documenting the task-set JSON contract for coder/planner/embedder files (fields, pass conditions, amendment policy).
  5. Verified end-to-end with `--dry-run`: planner (5 candidates), coder (4 candidates), embedder (8 cells × runtime/device matrix), rubric-lock guard exit 2 when planner runs without `--rubric`. All 17 dry-run records validate cleanly against `run.schema.json`.
- **Files touched:** `scripts/benchmark-tier-runner.py` (rewritten as thin CLI), `bench/runner/__init__.py` (new), `bench/runner/progress.py` (new), `bench/runner/server.py` (new), `bench/runner/nvml.py` (new), `bench/runner/probes.py` (new), `bench/runner/candidates.py` (new), `bench/runner/main.py` (new), `bench/tasks/README.md` (new).
- **Ports / adapters affected:** none.
- **PORTING_LEDGER / ADR updated:** none. ADR-0007 §7 progress-visibility discipline honored throughout new modules.
- **Stop-condition status:** Phase 0.1 runner implemented and dry-run-verified. Remaining Phase 0.1 work on Colossus: (a) install `openhands-sdk` + `openhands-tools` into runner venv so `_probe_coder_sdk` can lift its `NotImplementedError`; until then coder cells run in fallback tool-call mode and are tagged accordingly. (b) `.versions/llama.cpp` and `.versions/vllm` files not yet materialized on Colossus; runner accepts `--llama-cpp-build` / `--vllm-release` as explicit args. (c) First real (non-dry-run) invocation on Colossus is the next stop condition.

## 2026-08-11 02:16 EDT — --smoke bypass added for single-candidate hardware verification

- **Stage / plugin / port:** Phase 0.1 · runner UX
- **What changed:** Added `--smoke` CLI flag to `scripts/benchmark-tier-runner.py`. When set, bypasses the §0.0b open-pool guard (allowing single-candidate runs) and prefixes result filenames with `smoke-` instead of `phase-0-`. Purpose: hardware verification runs against one model before firing a full role pool. Not for elimination decisions — smoke records are visually distinct from Fast-tier records.
- **Files touched:** `bench/runner/main.py`, `scripts/benchmark-tier-runner.py`.
- **Ports / adapters affected:** none.
- **PORTING_LEDGER / ADR updated:** none. Spec §0.0b guard remains the default; bypass is opt-in and self-labels its outputs.
- **Stop-condition status:** verified via dry-run — normal run still emits `phase-0-*.json`; `--smoke --candidate-file` on a 1-element list bypasses guard and emits `smoke-*.json`.

## 2026-08-11 02:26 EDT — Reinstate flashinfer sampler workaround for SM_120

- **Stage / plugin / port:** Phase 0.1 · Fast-tier runner · VLLMServer env.
- **What changed:** Added `VLLM_USE_FLASHINFER_SAMPLER=0` to `VLLMServer` env dict. Amended ADR-0006 to document sampler verification gap. Appended DEBUG_LOG entry.
- **Files touched:** `bench/runner/main.py`, `adrs/ADR-0006-flashinfer-jit-cache-cu129.md`, `DEBUG_LOG.md`.
- **Ports / adapters affected:** vLLM launcher only. llama.cpp path unchanged.
- **PORTING_LEDGER / ADR updated:** ADR-0006 amendment.
- **Stop-condition status:** in-progress — Phase 0.1 smoke test unblocked pending re-run verification.
