# Gold rubric — coder-full-01-multifile-refactor-with-invariant

**Task prompt (verbatim):**
> In /workspace/repo, the class Order (in src/orders/order.py) exposes a method total() that returns a float. Change the return type to Decimal (from the decimal module) end-to-end: update the Order.total() signature and body to return Decimal, update every call site under src/ and tests/ to import Decimal and compare against Decimal values (never float), and update src/orders/__init__.py if needed. Do not rename Order.total. Do not change public method names. After your edits, `python -m pytest tests/ -q` must exit 0.

**Scoring model:** Perplexity-Max (Claude Sonnet 4.6 via Perplexity Computer)
**Range:** 0-100 per task
**Authored:** 2026-08-11 (ADR-0028 Full-tier)
**Locked:** post_hoc_edit_locked per ADR-0028

## Three-input rubric

Same three inputs as Medium multi-turn: tool trace, final file states, smoke test result.

## Task-specific correctness criteria

- `Order.total()` MUST return a `decimal.Decimal` (import from `decimal`).
- `Order.total()` MUST NOT be renamed.
- Callers in `src/reports/summary.py` may need adjustment if they use format specifiers assuming float; `test_summary.py` still asserts `"total=33.00"` — the summary must produce that exact string.
- Test `test_total_returns_decimal` asserts `isinstance(result, Decimal)` AND `result == Decimal("33.0")` — both must pass.
- Smoke test `python -m pytest tests/ -q` MUST exit 0.
- Preferred: `str_replace_editor` for edits, then `execute_bash` to run pytest.
- Dispreferred: `write_file` (would erase context of other functions).
- Disqualifying: renaming `total`, changing method signature name, hardcoding constants in tests, or modifying test assertions.

## Scoring bands

### 90-100 — Exemplary
- Smoke passes.
- `Order.total()` returns `Decimal`. Both existing tests pass.
- Minimal edits: `src/orders/order.py` modified; `src/reports/summary.py` unchanged or unchanged in a way that preserves the `"total=33.00"` output.
- No `AgentErrorEvent`s. Turn count minimal.

### 75-89 — Correct with minor process flaws
- Smoke passes.
- Extra unnecessary reads or one extra edit that does no harm.
- Docstring or comment additions beyond scope.

### 60-74 — Partially correct
- Smoke passes for `test_total_returns_decimal` but `test_format_total` fails because the `.2f` format spec was left applied to a Decimal (which raises).
- OR type change made but `Decimal` used incorrectly (e.g. from `Decimal(0.1)` producing binary-float artifacts and `Decimal("33.0")` assertion still passing by coincidence in this fixture but design is fragile).

### 40-59 — Substantially incorrect
- `Order.total()` renamed.
- OR tests modified to make them pass.
- OR type-change partial: return annotation says `Decimal` but body still returns float.

### 20-39 — Mostly failed
- Smoke fails on multiple tests.
- OR agent hit max_iter=20 without completing.

### 0-19 — Failed
- No FileEditorAction beyond viewing.
- OR abandoned the task.

## Deductions
- −5 hit max_iter=20
- −3 dispreferred tool used
- −2 whitespace drift on exact_diff (N/A here — mode is rubric_only)
- −2 extra read
- −1 per unnecessary tool call (cap −5)

## Bonuses
- +2 minimum turn count
- +2 perfect adherence to "do not rename total / do not change public method names"

## Notes
- Multiple correct implementations acceptable: return `Decimal(str(...))` OR `Decimal.from_float(...)` OR keep price/tax as int cents and use Decimal exact arithmetic. Any impl passing the smoke earns full marks.
- If `test_format_total` requires `f"total={order.total():.2f}"` — `Decimal` supports `.2f` format spec natively (returns `"33.00"`), so no change to `format_total` should be required. If the agent changed `format_total`, deduct only if it made behavior worse; not automatically disqualifying.
