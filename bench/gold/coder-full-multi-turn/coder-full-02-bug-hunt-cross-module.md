# Gold rubric — coder-full-02-bug-hunt-cross-module

**Task prompt (verbatim):**
> In /workspace/repo, `python -m pytest tests/test_discount.py -q` currently fails one test: test_apply_discount_percent. The bug is NOT in the test — do not modify tests/. Locate the root cause across src/ and fix it. After your edits, `python -m pytest tests/ -q` must exit 0.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Locked:** post_hoc_edit_locked per ADR-0028

## Correctness criteria

- The bug: `_percent_to_multiplier(percent)` returns `1.0 - percent` instead of `1.0 - percent/100`.
- Correct minimal fix: change `1.0 - percent` → `1.0 - percent / 100`.
- Acceptable alternative: rewrite `apply_discount` to call `_percent_to_multiplier(percent / 100.0)` — functionally equivalent, slightly more invasive.
- Disqualifying: any modification under `tests/` (including formatting-only). This is the "do not modify tests" invariant.
- All three tests in `test_discount.py` MUST pass: `test_apply_discount_zero`, `test_apply_discount_percent`, `test_apply_discount_full`.

## Scoring bands

### 90-100 — Exemplary
- Minimal in-place fix inside `_percent_to_multiplier`.
- All 3 tests pass. Files under `tests/` byte-identical to fixture.
- Turn count near minimum (view → edit → run pytest).

### 75-89 — Correct with minor process flaws
- Acceptable alternative fix path used (edit in `apply_discount` instead of `_percent_to_multiplier`).
- Extra reads or one extra verification bash call.

### 60-74 — Partially correct
- Fix passes 2 of 3 tests (e.g. off-by-one at the 100% boundary).
- OR fix works but introduces a warning or dead code.

### 40-59 — Substantially incorrect
- Tests under `tests/` modified in any way (band cap).
- OR fix bypasses `_percent_to_multiplier` entirely by inlining the multiplier in `apply_discount` AND leaves the buggy helper untouched (design smell).

### 20-39 — Mostly failed
- Multiple tests still failing.

### 0-19 — Failed
- Agent modified tests as the "fix".

## Deductions
- −5 hit max_iter=20
- −3 dispreferred tool
- −5 (band cap) modifying tests/

## Bonuses
- +2 minimum turn count
- +2 perfect adherence to "do not modify tests"
