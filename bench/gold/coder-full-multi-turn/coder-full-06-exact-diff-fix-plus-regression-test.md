# Gold rubric — coder-full-06-exact-diff-fix-plus-regression-test

**Task prompt (verbatim):**
> In /workspace/repo/src/parser/csv_lite.py, the function parse_line has a bug: it does not handle a trailing empty field (e.g. 'a,b,' should yield ['a','b',''] but currently drops the trailing ''). Fix it with the minimal possible change. Then add a regression test to tests/test_csv_lite.py named test_trailing_empty_field that asserts the fixed behavior. Do not modify any test other than to append this one test function. After your edits, `python -m pytest tests/ -q` must exit 0.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Locked:** post_hoc_edit_locked per ADR-0028

## Correctness criteria

### Fix (in src/parser/csv_lite.py)

- Minimal correct fix: change body from `return line.rstrip(",").split(",")` → `return line.split(",")`.
- Acceptable alternative: `return line.split(",") if not line.endswith(",") else line.split(",")` (functionally same; sloppy but correct).
- Disqualifying: hardcoding a special-case for a trailing comma.

### Regression test (appended to tests/test_csv_lite.py)

- Function name MUST be exactly `test_trailing_empty_field`.
- Body MUST assert `parse_line("a,b,") == ["a", "b", ""]` (semantically; exact literal encouraged).
- `test_basic` and `test_single_field` MUST remain byte-identical (or semantically identical if only whitespace).

### Smoke

- `python -m pytest tests/ -q` MUST exit 0. Expected 3 passing tests.

## Scoring bands

### 90-100 — Exemplary
- Minimal fix (`line.split(",")`). Regression test named exactly. Existing tests untouched. Smoke passes.
- Turn count near minimum (read → edit fix → edit test → smoke).

### 75-89 — Correct with minor process flaws
- Fix correct but slightly less minimal (e.g. conditional check instead of removing rstrip).
- Regression test name slightly off (`test_trailing_empty` instead of `test_trailing_empty_field`) — will fail correctness on name check but pass on assertion.

### 60-74 — Partially correct
- Fix correct; regression test asserts wrong expected value or not named correctly.
- OR fix works but regression test missing.

### 40-59 — Substantially incorrect
- `test_basic` or `test_single_field` modified (band cap).
- OR fix incorrect and smoke fails on original tests.

### 20-39 — Mostly failed
- Fix broke both new and old tests.

### 0-19 — Failed
- No fix + no regression test.

## Deductions
- −5 hit max_iter=20
- −3 dispreferred tool
- −2 whitespace drift on existing tests

## Bonuses
- +2 minimum turn count
- +2 perfect minimal correction (single-line body change)
