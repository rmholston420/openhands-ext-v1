# OpenHands-Ext v1 — Session Handoff — 2026-08-11 23:22 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 9 (Loop Guard) — **SIGNED OFF**. Next up: **Phase 5 — GPU Telemetry MCP**.
- **Plugin / kernel component:** none active. Phase 5 will introduce a new MCP server (GPU telemetry: `nvidia-smi` samples + VRAM / thermal readings exposed as MCP tools/resources).
- **Port(s) in progress:** none.

## Completed this session

- ADR-0037 authored (near-identical StuckDetector scenario; string-anchored Python transformer; 4-sentinel verification).
- `scripts/apply-stuckdetector-patch.py` — idempotent transformer over vendored SDK `openhands/sdk/conversation/{types.py, stuck_detector.py}`.
- `scripts/vendor-openhands-sdk.sh` extended to run + verify the ADR-0037 patch after the ADR-0034 patch, then editable reinstall.
- Contract test suite `tests/sdk_patch/test_stuckdetector_near_identical.py` (9 cases: sentinel + positives + negatives).
- Smoke `bench/smoke-phase-9-loop-guard/run.sh` (deterministic in-process; no LLM / vLLM / Docker).
- **Bug fix** (commit `679e9af`): test + smoke fixtures rebuilt on SDK `MessageToolCall` (not raw litellm `ChatCompletionMessageToolCall`). Detector patch bytes unchanged.
- **Smoke PASS on Colossus**: 9/9 unit tests + end-to-end near-identical flag; below-threshold and different-content negatives correct.
- ADR-0037 status: Proposed → **Ratified** 2026-08-11.
- Verification matrix row 9.a → ✅.
- BUILD_LOG entries at 23:07, 23:19, 23:22 EDT. DEBUG_LOG entry at 23:18 EDT.
- PORTING_LEDGER: StuckDetector patch row (already VENDORED-PATCHED at 23:07 EDT).

## Remaining before current Definition of Done

- Phase 9 DoD met.

## Open questions / awaiting user answer

- Phase 5 (GPU Telemetry MCP) design not yet started. Open questions when we begin:
  1. Poll-based vs event-stream sampling cadence?
  2. Which telemetry fields are in scope? (util, VRAM used/free, temp, power, per-process VRAM) Suggest all five as MVP.
  3. Transport: SSE (matches upstream OpenHands MCP defaults) vs stdio? SSE preferred for a long-running host telemetry server.
  4. Vendor candidate: are there permissively-licensed nvidia-smi MCP servers already? Should scan before hand-building.

## Exact next action

**When user resumes:**
1. Scope Phase 5 GPU Telemetry MCP against `Kosmos-Build-Spec-v25.md` (or its OpenHands-Ext analog).
2. Search for an existing permissively-licensed `nvidia-smi` MCP server before hand-building.
3. Confirm answers to the four open questions above.
4. Author ADR-0038 draft before any code.
