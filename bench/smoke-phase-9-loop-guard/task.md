# Phase 9 smoke — ADR-0037 loop-guard near-identical scenario

**DoD (from spec):** Send 3+ identical/near-identical tool calls → loop-guard hook flags repetition.

## Scope

Verifies that ADR-0037's vendored+patched `StuckDetector` extension:

1. Adds a `near_identical: int = Field(default=3, ge=1)` field to
   `StuckDetectionThresholds`.
2. Adds a `_is_stuck_near_identical` scenario 6 to `StuckDetector.is_stuck()`.
3. Correctly flags tool-call sequences whose arguments differ only in
   whitespace, quoting, key-order, casing, or trailing punctuation —
   which upstream's exact-equality `_is_stuck_repeating_action_observation`
   would miss until the (higher) `action_observation=4` threshold.

## Method

**Deterministic in-process test.** No LLM, no vLLM, no Docker.
Faster and more reliable than a real-model retry loop (models don't
always loop on cue).

Three steps:

1. **Sentinel check** — imports the patched SDK and asserts the ADR-0037
   surface exists (`near_identical` field, `_is_stuck_near_identical`
   method, `_adr0037_action_key` helper).

2. **Contract test suite** — runs
   `tests/sdk_patch/test_stuckdetector_near_identical.py` via
   `unittest -v`. Covers 7 cases:
   - `near_identical` field default (3)
   - `near_identical_threshold` property
   - scenario 6 method present
   - whitespace/quotes/casing/key-order normalization → tripped
   - exact-equal calls → tripped
   - 2 calls (below threshold) → NOT tripped
   - different tools → NOT tripped
   - different content → NOT tripped
   - trailing punctuation → tripped

3. **End-to-end scenario** — constructs three near-identical `ActionEvent`s
   inline, instantiates a bare `StuckDetector`, asserts:
   - 3 near-identical calls trip `_is_stuck_near_identical`
   - 2 calls do NOT trip
   - 3 different-content calls do NOT trip

## PASS criteria

All three steps exit 0. Final line: `OK Phase 9 smoke PASSED (ADR-0037)`.

## FAIL modes → recovery

- **`near_identical field missing`** → vendor script did not apply
  ADR-0037 patch. Re-run `scripts/vendor-openhands-sdk.sh` and check
  sentinel log lines.
- **Contract test failure** → inspect the specific test case; the
  ADR-0037 code path may have regressed. Cross-check against
  `patches/apply-stuckdetector-patch.py` transform logic.
- **`3 different-content calls tripped`** → normalization is too
  aggressive; the `_adr0037_canonicalize` helper is collapsing
  more variance than intended. Bug in the canonicalizer.

## References

- `adrs/ADR-0037-stuckdetector-near-identical-scenario.md`
- `scripts/apply-stuckdetector-patch.py`
- `tests/sdk_patch/test_stuckdetector_near_identical.py`
- `docs/specs/integration-execution-plan-v16.md` §Phase 9
