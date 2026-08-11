# Gold rubric — coder-full-04-pytest-multi-failure-report

**Task prompt (verbatim):**
> In /workspace/repo, run the pytest suite and report the results. DO NOT modify any files. In your Finish message, list every failing test (by test name) and, for each, one-line why it failed. Return exit-code style summary: 'N passed, M failed'.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Report-style task · DO NOT MODIFY**
**Locked:** post_hoc_edit_locked per ADR-0028

## Correctness criteria

- `execute_bash` run of pytest must appear in the trace.
- Files under `/workspace/repo/src/` and `/workspace/repo/tests/` MUST be byte-identical to fixture at task end (immutable check).
- FinishAction MUST be present and MUST contain:
  1. All three failing test names: `test_div_float`, `test_div_by_zero`, `test_titlecase`.
  2. A one-line reason for each (e.g., "`div` uses `//` so returns int, expected float 3.5" / "`div` doesn't wrap ZeroDivisionError in ValueError" / "`titlecase` returns upper() not title()").
  3. Summary `2 passed, 3 failed` (or a semantically equivalent restatement).

## Scoring bands

### 90-100 — Exemplary
- Files preserved. FinishAction present with all 3 test names, all 3 reasons, correct summary.
- Turn count minimal (bash → finish, or bash → optional read → finish).

### 75-89 — Correct with minor process flaws
- All 3 tests named and correctly summarized but one reason is vague ("some assertion failure").
- Extra reads or verification runs.

### 60-74 — Partially correct
- Only 2 of 3 failing tests named.
- OR summary count wrong ("1 failed" instead of "3 failed") but tests correctly identified.

### 40-59 — Substantially incorrect
- Files modified in any way (band cap regardless of report quality).
- OR only 1 failing test named.
- OR agent tried to "fix" the bugs instead of reporting.

### 20-39 — Mostly failed
- No test names in FinishAction.
- OR agent modified files AND failed to report.

### 0-19 — Failed
- **No FinishAction present.** (Automatically triggers reversal rule 2 clause 3 in aggregation.)
- OR FinishAction present but empty of test information.

## Deductions
- −10 for omitting FinishAction on this report-style task (see full-scored.json)
- −5 hit max_iter=20
- −5 (band cap) any file modification

## Bonuses
- +2 minimum turn count
- +2 perfect adherence to "DO NOT modify"

## Reversal-criteria signal
- **Absent FinishAction on this task auto-fires confirm-AWQ rule (rule 2 clause 3).** Recorded here so the scorer flags it explicitly during aggregation.
