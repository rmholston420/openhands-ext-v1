# Benchmark Un-Pause Gates

**Status:** DRAFT · 2026-08-11 06:57 EDT
**Owner:** rmholston
**Referenced from:** `SESSION_HANDOFF.md`, ADR-0017 (production role selection)

Medium-tier benchmarking and Phase-0.3 authoring are **paused** as of 2026-08-11. This file lists the exact gates that must be GREEN before either resumes. Any gate flip from GREEN back to RED re-pauses.

Update the status column when a gate changes. Do not delete gates — record the resolution in-place.

---

## Gate 1 — Production endpoints live and healthy

**Status:** GREEN (2026-08-11 06:52 EDT)

- coder (8100), planner (8082), embedder (8090) all pass `scripts/check-production-endpoints.sh` when their expected co-residency slot is active.
- Coder: PASS chat 192 ms, out_tokens=7. Model loading 16.96 GiB, KV cache 9.61 GiB, concurrency 3.20x @ 32k.
- Embedder: PASS on 8090 (CPU-resident per ADR-0017 amendment #3), dim=2560, 293 ms.
- Planner: verified startable via `scripts/serve-planner.sh` (co-residency Option 2: only one large model at a time).

## Gate 2 — All in-session ADR amendments logged and reconciled

**Status:** GREEN (2026-08-11 06:57 EDT)

- ADR-0017 amendments #1, #2, #3 applied and status line updated to `Ratified v25 · Amended ×3 (pre-Phase-0.3)`.
- BUILD_LOG, DEBUG_LOG, KNOWN_ISSUES, SESSION_HANDOFF all current.
- No open contradictions between spec and ADRs.

## Gate 3 — All DEBUG_LOG entries have reusable-lesson bullets

**Status:** GREEN (2026-08-11 06:57 EDT)

- 2026-08-11 06:39 EDT (VRAM + embedder GPU→CPU): 3 reusable lessons.
- 2026-08-11 06:49 EDT (FlashInfer sampler on SM 12.0): 4 reusable lessons.
- 2026-08-11 06:32 EDT (compressed-tensors auto-detect): reusable lesson embedded in `scripts/serve-coder.sh` header.

## Gate 4 — VRAM budget verified for both large-model roles

**Status:** GREEN for coder (2026-08-11 06:52 EDT) · UNVERIFIED for planner

- coder: 16.96 GiB weights + 9.61 GiB KV + 0.58 GiB CUDA graphs = 27.15 GiB used at 0.90 util (28.25 GiB budgeted). Fits with ~4 GiB free at startup.
- planner: not yet started this session. Expected ~21 GiB weights (Q4_K_XL) + Q8_0 KV. `serve-planner.sh` `MIN_FREE_GIB` gate is 24 GiB.
- Un-pause requires one successful `serve-planner.sh` → PASS on `check-production-endpoints.sh` → clean stop.

## Gate 5 — Blackwell + CUDA 12.8 workarounds documented

**Status:** GREEN (2026-08-11 06:52 EDT)

- `VLLM_USE_FLASHINFER_SAMPLER=0` forced in `scripts/serve-coder.sh` (FlashInfer sampler requires CUDA ≥ 12.9 for SM 12.x).
- Deferred: CUDA 12.8 → 12.9 upgrade path. Not required for un-pause; required only if FlashInfer sampler quality/perf becomes measurable-and-superior.

## Gate 6 — Bench harness rubric and results intact

**Status:** GREEN (2026-08-11 06:57 EDT)

- No `bench/results/*.json` files deleted this session (user policy).
- Rubric files post_hoc_edit_locked per §0.0a.
- No pre-emptive edits to Medium-tier rubrics during the pause.

## Gate 7 — Deferred decisions have written triggers

**Status:** GREEN (2026-08-11 06:57 EDT)

- `KNOWN_ISSUES.md` filing for 4B-CPU vs. 0.6B-GPU embedder decision has explicit un-block triggers (retrieval latency threshold, Medium-tier work).
- CUDA 12.9 upgrade: informal deferral; add to KNOWN_ISSUES if it starts blocking anything.

## Gate 8 — Config surface still env-vars-only (Phase-0.3 boundary preserved)

**Status:** GREEN (2026-08-11 06:57 EDT)

- No `config/config.toml` created.
- No `mcp-servers/inference-backends/` created.
- No `configs/dev-current/` created.
- Un-pause into Phase-0.3 requires an ADR defining the config schema BEFORE the first file lands.

## Gate 9 — Pre-commit hooks operational

**Status:** GREEN (2026-08-11 06:57 EDT)

- `hooks/pre-commit/dispatch.sh` runs `size-guard.sh` and `no-localworkspace.sh` (ADR-0002 zero-`LocalWorkspace` policy).
- Additional hooks (container isolation, code-explorer delegation) are Phase-1 integration tests, not pre-commit — deferred until Phase-1 opens.

---

## Un-pause protocol

Run this once, from a fresh session:

```bash
cd ~/dev/openhands-ext-v1
git pull
# Verify all endpoints
bash scripts/serve-embedder.sh >/tmp/serve-embedder.log 2>&1 &
sleep 8
bash scripts/serve-coder.sh >/tmp/serve-coder.log 2>&1 &
sleep 45
bash scripts/check-production-endpoints.sh
bash scripts/stop-large-model.sh coder
bash scripts/serve-planner.sh >/tmp/serve-planner.log 2>&1 &
sleep 60
bash scripts/check-production-endpoints.sh
bash scripts/stop-large-model.sh planner
# All three roles verified alive. Read this file; confirm every gate GREEN.
```

If every gate above is GREEN after this run, Phase-0.3 authoring may open and Medium-tier benchmarking may resume.
