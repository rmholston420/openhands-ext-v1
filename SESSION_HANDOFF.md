# OpenHands-Ext v1 — Session Handoff — 2026-08-10 23:45 EDT

## Current build-sequencing position

- **Stage / phase:** Pre-Phase -1 complete; **Phase -1 execution ready on Colossus**.
- **Plugin / kernel component:** governance (ADR-0003 mirror discipline filed); Phase -1 execution scripts landed.
- **Port(s) in progress:** none.

## Completed this session

- Filed **ADR-0003** — three-category mirror discipline (tracked / regenerable-by-script / ephemeral) with HARD sync strictness.
- Added pre-commit dispatcher (`hooks/pre-commit/dispatch.sh`) chaining size-guard + LocalWorkspace checks.
- Added pre-commit size-guard (`hooks/pre-commit/size-guard.sh`, 10 MiB limit, empty allow-list).
- Added pre-push hook (`hooks/pre-push/no-diverged-remote.sh`).
- Extended `scripts/install-hooks.sh` to install all three hooks; idempotent.
- Added `scripts/session-start.sh` (fetches, verifies clean tree + non-diverged remote, tails handoff + BUILD_LOG).
- Added `scripts/session-end.sh` (commits + pushes with hard-fail on divergence, marks Colossus authorship).
- Added `scripts/bootstrap-venv.sh` (idempotent replacement for the previous inline block that killed the interactive shell — see `DEBUG_LOG.md` 2026-08-10 23:38 EDT).
- Added `scripts/build-llama-cpp.sh` (CUDA 12.8 + `/usr/bin/gcc-13` host compiler + `-DCMAKE_CUDA_ARCHITECTURES=120`; re-fetches latest tag).
- Added `scripts/install-oh-sdk.sh` (re-fetches PyPI versions, installs pinned).
- Added `scripts/install-vllm.sh` (re-fetches vllm version, installs pinned, records torch/CUDA versions).
- Added `scripts/pull-models.sh` (Qwen2.5-1.5B-Instruct in GGUF Q4_K_M + safetensors, both via modern `hf` CLI).
- Added `scripts/smoke-test-llama-cpp.sh` (spec §-1.5, port 8082, records GPU snapshot).
- Added `scripts/smoke-test-vllm.sh` (spec §-1.5, port 8083, records GPU snapshot).
- Extended `.gitignore` for `vendor/` and `bench/results/*.log`.
- Extended LocalWorkspace hook allow-list for new hook + script paths.

## Remaining before current Definition of Done

**Phase -1 Definition of Done (spec §-1 Verification table) — execute on Colossus in this order:**

1. `git pull` (or `bash scripts/session-start.sh` which does this plus checks).
2. `bash scripts/install-hooks.sh` — install the updated hooks (idempotent).
3. `bash scripts/bootstrap-venv.sh` — the `.venv/` from the killed run is likely usable but re-running is safe.
4. `bash scripts/install-oh-sdk.sh` — installs pinned OpenHands SDK stack, records to `bench/results/`.
5. `bash scripts/install-vllm.sh` — installs pinned vLLM, records torch/CUDA versions.
6. `bash scripts/build-llama-cpp.sh` — clones + builds llama.cpp with SM_120 (5-15 min).
7. `bash scripts/pull-models.sh` — pulls Qwen2.5-1.5B in both formats (~4 GB total).
8. `bash scripts/smoke-test-llama-cpp.sh` — spec §-1.5 verification (llama.cpp).
9. `bash scripts/smoke-test-vllm.sh` — spec §-1.5 verification (vLLM).
10. `bash scripts/session-end.sh -m "phase(-1): all §-1 Verification table rows green"` — commits the `bench/results/*.json` metadata files and pushes.

**Report Phase -1 Verification table row-by-row after step 9.** Metadata JSONs under `bench/results/` will be the authoritative record.

## Open questions / awaiting user answer

None. ADR-0003 ratified with optimal choices per user directive.

## Exact next action

On Colossus:

```bash
cd ~/dev/openhands-ext-v1
git pull origin main
bash scripts/session-start.sh
```

`session-start.sh` will refuse to run if the tree is dirty. Colossus previously had modified `.gitignore` (from the killed script). If session-start fails on dirty tree, resolve first:

```bash
cd ~/dev/openhands-ext-v1
git diff .gitignore              # inspect (probably matches what's now on origin)
git checkout .gitignore          # discard local changes; new .gitignore comes from git pull
git pull origin main
bash scripts/session-start.sh
```

Then step through steps 3-10 above, one script at a time. If any script fails, its output is at `/tmp/openhands-ext-v1-<script>-<timestamp>.log`; paste the tail and I'll diagnose.
