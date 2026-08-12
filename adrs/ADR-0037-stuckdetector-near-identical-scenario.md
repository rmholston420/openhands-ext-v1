# ADR-0037 — Extend `StuckDetector` with a near-identical scenario (Phase 9 Loop Guard)

**Status:** Proposed
**Lock-in phase:** Phase 9 (Loop Guard)
**Supersedes:** —

## Context

Phase 9 of `docs/specs/integration-execution-plan-v16.md` calls for an
always-on, agent-server-side loop-guard hook (per §1.1: *"outside the
container — not disable-able by anything inside the sandbox they
police"*). Definition of Done: *"Send 3+ identical/near-identical tool
calls → loop-guard hook flags repetition."*

Inspection of the vendored SDK
(`vendor/openhands-sdk/openhands-sdk/openhands/sdk/conversation/stuck_detector.py`)
shows that upstream **already ships a `StuckDetector`** wired into
`LocalConversation._check_stuck_or_nudge` (lines 655–680). It covers
five scenarios:

1. same-action + same-observation loops (`_is_stuck_repeating_action_observation`)
2. same-action + error loops (`_is_stuck_repeating_action_error`)
3. agent monologue
4. alternating A/B/A/B action-observation
5. context-window error loop (upstream-open, placeholder)

Configurable thresholds via `StuckDetectionThresholds`; nudge text via
`get_action_error_nudge()`; runs in the host process (not inside the
sandbox), satisfying §1.1.

The gap vs Phase 9 DoD is the **"near-identical"** clause. Upstream's
`_event_eq` compares `Action` fields with `==`; agents that retry the
same call with only cosmetic arg reformatting (whitespace, quoting,
key-order, casing, trailing punctuation) escape detection until the
`action_observation` threshold of 4 exact-equal calls fires.

## Decision

Vendor + patch `StuckDetector` (same discipline as ADR-0034) to add a
sixth scenario, `_is_stuck_near_identical`, plus a `near_identical: int
= Field(default=3, ge=1, ...)` threshold on
`StuckDetectionThresholds`. The patch is delivered as an idempotent
Python transformer script
(`scripts/apply-stuckdetector-patch.py`) rather than a unified diff,
because the change touches two files at five anchor points and
line-anchored hunks would be fragile.

The new scenario:

- Collects the last N (default 3) consecutive `ActionEvent`s.
- Normalizes each `(tool_name, tool_call.arguments)` pair by:
  - Case-folding `tool_name`.
  - Parsing `tool_call.arguments` as JSON, sorting keys, collapsing
    whitespace and trailing punctuation on all string scalars,
    case-folding string scalars.
  - Falling back to a whitespace-normalized raw string if JSON parsing
    fails, so we still catch loops on malformed LLM output.
- Flags the loop when all N normalized keys match.

Wired automatically: since `is_stuck()` is called from
`LocalConversation._check_stuck_or_nudge` (line 672), adding a new
branch inside `is_stuck()` is picked up without further wiring. On
detection, upstream's existing behavior fires: state set to
`ConversationExecutionStatus.STUCK` and the run loop stops.

Nudge behavior: retained upstream nudge-then-stop semantics.
`get_action_error_nudge()` continues to fire on action-error streaks
(scenario 2); near-identical detection (scenario 6) uses the same
stop-the-run outcome as scenarios 1, 3, 4.

## Rationale

- **Vendor-before-hand-build** (per project instructions + Kosmos port
  workflow): upstream ships 95% of the work. Extending its existing
  detector adds one scenario, not a parallel system.
- **§1.1 invariant met**: `StuckDetector` is instantiated by
  `LocalConversation` at construction and runs in the host process.
  Nothing inside the sandbox can disable it.
- **DoD threshold**: near-identical threshold defaults to 3 (matches
  spec DoD directly), while upstream's `action_observation` default
  stays at 4.
- **Additive, not disruptive**: existing five scenarios unchanged;
  only `is_stuck()`'s branch list and `StuckDetectionThresholds`'s
  field list grow.
- **Idempotent transformer script > unified diff**: two-file, five-hunk
  patches are line-fragile; string-anchored edits with sentinel checks
  are more robust and fail-loud on upstream drift.

## Alternatives considered

1. **Path A — do nothing** (declare upstream sufficient, add smoke
   only). Rejected: leaves the "near-identical" DoD clause unmet.
   Cosmetic arg reformatting is a real failure mode we've observed.

2. **Path C — full custom rewrite** (`LoopGuardCallback` alongside
   `StuckDetector`). Rejected: duplicates upstream, violates Kosmos
   port workflow, adds a parallel code path that can drift from
   upstream's `is_stuck` semantics.

3. **Ship as a `ConversationCallback`**. Rejected: callback signature
   is `Callable[[Event], None]` — it can observe but not directly
   invoke the same stop-the-run status transition that `is_stuck()`
   triggers via `LocalConversation._check_stuck_or_nudge`. Wiring a
   callback to reproduce that behavior would be a partial re-implementation.

4. **`.patch` file** (matching ADR-0034 style). Rejected: two files, five
   hunks, and any upstream drift on line offsets would silently fail
   `patch -p1 --dry-run` in the vendor script or produce a partial
   apply. String-anchored transformer with sentinel checks is more
   robust for this shape.

## Consequences

- `patches/openhands-sdk-llm-discriminated-union.patch` — unchanged
  (ADR-0034 remains authoritative for its LLM patch).
- `scripts/apply-stuckdetector-patch.py` — new. Idempotent transformer.
- `scripts/vendor-openhands-sdk.sh` — extended to invoke the new
  transformer script and verify ADR-0037 sentinels alongside the
  existing ADR-0034 anchors.
- `PORTING_LEDGER.md` — new entry: openhands-sdk StuckDetector patch,
  status `VENDORED`, ADR-0037.
- `tests/sdk_patch/test_stuckdetector_near_identical.py` — new contract
  test asserting: (a) `near_identical_threshold` property returns
  the configured default (3); (b) three consecutive `ActionEvent`s
  with cosmetically-different args produce `is_stuck() == True`; (c)
  three exact-equal calls also trigger; (d) two calls do not; (e)
  three different-tool calls do not.
- `bench/smoke-phase-9-loop-guard/` — new smoke bench. In-process
  deterministic: instantiate `LocalConversation`, inject three
  crafted near-identical `ActionEvent`s into `_state`, assert
  `is_stuck() == True` and stop-run wiring fires the expected
  `ConversationExecutionStatus.STUCK`.
- `docs/verification/verification-matrix.md` — new row for Phase 9.
- `BUILD_LOG.md`, `DEBUG_LOG.md`, `SESSION_HANDOFF.md` — appended /
  overwritten per Kosmos log discipline.

## Lock-in phase

Phase 9 (Loop Guard). Ratifies on smoke bench PASS.

## References

- `docs/specs/integration-execution-plan-v16.md` §Phase 9, §1.1
- `adrs/ADR-0034-llm-discriminated-union-vendored-sdk-patch.md` (vendor+patch pattern)
- `adrs/ADR-0003-vendor-tree-regenerable.md` (vendor category 2)
- `vendor/openhands-sdk/openhands-sdk/openhands/sdk/conversation/stuck_detector.py` (upstream)
- `vendor/openhands-sdk/openhands-sdk/openhands/sdk/conversation/types.py` (upstream)
