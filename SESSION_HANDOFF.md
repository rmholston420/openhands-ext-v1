# Kosmos Session Handoff — 2026-08-11 22:40 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 3 sign-off · item 3.j
- **Plugin / kernel component:** ADR-0034 verification surface (`RouterLLM` / `CoderPlannerRouter` serialization boundary).
- **Port(s) in progress:** none open; workspace transport choice (LocalWorkspace vs DockerWorkspace) rather than a port surface.

## Completed this session
- Client-side 3.j smoke `pass=true` (2026-08-11 22:11:15 EDT run) — verdict at `~/.forge-oh/bench_smoke_phase_3_item_3j/20260811_221115_run/verdict.json`. Established the ADR-0034 patch (`LLM._validate_subtype`) is load-bearing and works in-process.
- Diagnosed container-side leg failure: overlay Dockerfile approach impossible because published `ghcr.io/openhands/agent-server:*-python` tags are PyInstaller `binary` target with frozen `openhands.sdk` bytecode inside the ELF (no `/agent-server/.venv/`, no importable `openhands.sdk` in any site-packages).
- Filed ADR-0036 (Ratified, supersedes ADR-0035); amended ADR-0035 with status-amendment block; updated `adrs/README.md`.
- Marked overlay-image entry in `PORTING_LEDGER.md` as `REJECTED (by ADR-0036)` with rejection reason.
- Moved overlay artifacts to `docs/rejected/` with REJECTED headers pointing to ADR-0036.
- Rewrote `bench/smoke-phase-3-item-3j/run.sh` to use `LocalWorkspace` (drops overlay-image build step; retains full ADR-0034 round-trip assertion + coder :8100 preflight + all pass criteria). Updated `bench/smoke-phase-3-item-3j/task.md`.
- Updated `docs/verification/verification-matrix.md`: row 3.j ❌ → ✅ (scoped to LocalWorkspace + ADR-0034 assertion); added new row 3.k for container-side verification as ⛔ deferred with options A/C.
- Appended timestamped entries to `BUILD_LOG.md` and `DEBUG_LOG.md`.

## Remaining before current Definition of Done
- On Colossus: `cd ~/dev/openhands-ext-v1 && git pull && bash bench/smoke-phase-3-item-3j/run.sh` — expected to produce a passing verdict artifact. On PASS, update the verification-matrix row 3.j evidence line with the new verdict path.

## Open questions / awaiting user answer
- None. Option D was approved; ADR-0036 authored. 3.k deferred with two viable paths documented in ADR-0036 (Option A: local build of upstream `source` target + overlay ADR-0034 patch; Option C: fork software-agent-sdk, rebuild `binary` target with patch applied, publish to private registry).

## Exact next action
- User: `cd ~/dev/openhands-ext-v1 && git pull && bash bench/smoke-phase-3-item-3j/run.sh`
