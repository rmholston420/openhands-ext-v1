# ADR-0018 — Phase −1 Version Pins (drift-tolerant baseline)

**Status:** Ratified · 2026-08-11 07:12 EDT
**Lock-in phase:** Phase −1
**Supersedes:** —

## Context

Spec §Phase −1 (`docs/specs/integration-execution-plan-v16.md`) mandates a live-verified version baseline before Phase 0 launches. It also acknowledges that llama.cpp uses a rolling build-tag stream (multiple tags per day, no semantic versioning) and vLLM releases frequently. This decision fixes the policy for how "pin" is interpreted when the current installed state and the top-of-releases diverge by hours to a day.

Two candidate interpretations exist:

- **Interpretation A — strict live-follow:** every Phase −1 pass re-installs to top-of-releases regardless of the working state. Matches spec §−1.4's literal `pip install …==<top-tag>` command.
- **Interpretation B — drift-tolerant record:** live-fetch, log installed vs. top, upgrade only when the delta is materially motivated (bugfix relevant to Colossus, feature required for planned work, or user-directed).

The Colossus environment has three production endpoints (coder/planner/embedder) currently PASSing all `check-production-endpoints.sh` probes. The coder runs with a documented Blackwell + CUDA-12.8 workaround (`VLLM_USE_FLASHINFER_SAMPLER=0`). Any strict live-follow upgrade risks breaking one of them for a drift-of-hours whose changelog has not been reviewed.

## Decision

**Adopt Interpretation B — drift-tolerant record.** Phase −1 verification requires:

1. Live-fetch top-of-releases for every listed component at execution time via GitHub API (`gh` CLI).
2. Record the installed version, the top-of-releases version, and the fetch timestamp (UTC) for every component in a Category-7 metadata artifact at `bench/run-metadata/version-pins-<utc-ts>.json`.
3. When drift is observed on a currently-working component, log the drift in `KNOWN_ISSUES.md` with the exact upgrade command; **do not upgrade unless the user explicitly directs it** or the changelog documents a fix that directly addresses a known Colossus issue.
4. Re-run Phase −1 verification any time a component is intentionally upgraded, or on demand.

## Rationale

- **Spec §−1.2 acknowledges the reality:** "There is no 'latest stable' — the top-of-releases tag at build time is current; never trust a cached tag." Chasing a rolling tag mechanically is spec-inconsistent even under a strict reading.
- **Working state has verified integration cost:** the current coder+CUDA-12.8+SM 12.0 combination required a documented workaround (DEBUG_LOG 2026-08-11 06:49 EDT). Re-doing that work for every daily vLLM patch is not justified by any spec goal.
- **Category-7 metadata still lands:** Interpretation B satisfies "version-pin metadata logged into Category 7" (spec §−1 verification row 6) because both the installed pin and the live top are captured with fetch timestamps.
- **Interpretation A alternative rejected:** upgrading solely to close drift would (a) trigger llama.cpp rebuild costs (~5–15 min), (b) risk untested Blackwell regressions in the new tag, and (c) be immediately drifted again within hours.
- **Interpretation C considered and rejected:** "upgrade only openhands-sdk semver-minor bumps and never bump runtimes" — insufficient because runtime bumps are sometimes required for Blackwell fixes (e.g., a hypothetical vLLM 0.27.1 that lands the FlashInfer sampler fix would motivate upgrade).

## Consequences

- New file: `bench/run-metadata/version-pins-<utc-ts>.json` per Phase −1 pass (one artifact per run).
- New file: `docs/PHASE-MINUS-1-VERIFICATION.md` (updatable checklist; overwrite each pass).
- `KNOWN_ISSUES.md` may carry drift entries with upgrade commands; entries clear when the drift is resolved.
- `scripts/build-llama-cpp.sh` continues to `curl` the top tag at build time (already implemented, L62). Rebuilds are user-triggered, not automatic on drift.
- No changes to `requirements.txt` — pip pins remain frozen at the installed versions.
- Every subsequent Phase (0.1 onward) MUST reference the Phase −1 metadata artifact in its own Category-7 run metadata (link by relative path).

## Lock-in phase

Phase −1. Amendments allowed as drift policy evolves, but any change to "auto-upgrade vs. record" behavior requires a new ADR that explicitly supersedes this one.

## References

- `docs/specs/integration-execution-plan-v16.md` § Phase −1
- `docs/PHASE-MINUS-1-VERIFICATION.md`
- `bench/run-metadata/version-pins-20260811T111235Z.json` (first Phase −1 pass)
- ADR-0008 (thinking-disabled probes — referenced in smoke evidence)
- ADR-0017 (production role selection)
- `KNOWN_ISSUES.md` (drift entries)
