# OpenHands-Ext v1 — Session Handoff (2026-08-11 23:07 EDT)

## Current build-sequencing position
- **Stage / phase:** Phase 9 (Loop Guard) — in progress; awaits smoke PASS.
- **Plugin / kernel component:** vendored `openhands-sdk` `StuckDetector` extension (ADR-0037).
- **Port(s) in progress:** none new. Extends the same vendored openhands-sdk tree already ported by ADR-0034; the new scenario slots into `is_stuck()` via `LocalConversation._check_stuck_or_nudge`.

## Completed this session
- Chose Phase 9→5 ROI order; committed to Phase 9 first.
- Design: **Fork A** (host-process, LocalWorkspace scope) + **option (b)** exact+normalized detection + **option (ii)** stop-the-run via `is_stuck()`.
- Inspected vendored SDK — confirmed upstream already ships `StuckDetector` with 5 scenarios, wired in `LocalConversation._check_stuck_or_nudge` (line 655). Gap vs Phase 9 DoD is only the "near-identical" clause.
- Selected **Path B** (vendor+patch upstream) over Path A (do nothing) or Path C (full rewrite). Selected idempotent Python transformer over unified diff for the two-file, five-hunk shape.
- Filed **ADR-0037** (Proposed): extend `StuckDetector` with a `near_identical: int = Field(default=3)` threshold + `_is_stuck_near_identical` scenario 6.
- Added `scripts/apply-stuckdetector-patch.py` (idempotent, string-anchored, sentinel-verified).
- Extended `scripts/vendor-openhands-sdk.sh` to invoke the transformer after the ADR-0034 patch and verify four ADR-0037 sentinels.
- Added contract test `tests/sdk_patch/test_stuckdetector_near_identical.py` (7 cases).
- Added smoke bench `bench/smoke-phase-9-loop-guard/{run.sh, task.md}` — deterministic in-process, no LLM.
- Updated `adrs/README.md`, `PORTING_LEDGER.md`, `docs/verification/verification-matrix.md` (Phase 9 row), `BUILD_LOG.md`.

## Remaining before current Definition of Done
- User: `cd ~/dev/openhands-ext-v1 && git pull`.
- User: `bash scripts/vendor-openhands-sdk.sh` — expected: both ADR-0034 (3 anchors) and ADR-0037 (4 sentinels) verified; SDK re-installed editable.
- User: `bash bench/smoke-phase-9-loop-guard/run.sh` — expected: all 3 steps PASS, final line `OK Phase 9 smoke PASSED (ADR-0037)`.
- On smoke PASS: flip ADR-0037 status to **Ratified**, flip verification-matrix row 9.a to ✅, commit + push, then move to Phase 5 (GPU Telemetry MCP).

## Open questions / awaiting user answer
- None.

## Exact next action
User (on Colossus):
```bash
cd ~/dev/openhands-ext-v1 && git pull && \
  bash scripts/vendor-openhands-sdk.sh && \
  bash bench/smoke-phase-9-loop-guard/run.sh
```
Paste the last ~40 lines of output back — I'll flip ADR-0037 / matrix to Ratified/✅ and hand off to Phase 5.
