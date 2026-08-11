# Gold rubric — coder-medium-06-rename-symbol-across-files

**Task prompt (verbatim):**
> Rename the function compute_total to calculate_total across /workspace/repo/src/math_ops.py (definition + docstring) and /workspace/repo/src/main.py (import + call site). Preserve all behavior.

**Scoring model:** Perplexity-Max (Claude Sonnet 4.6 via Perplexity Computer)
**Range:** 0-100 per task; macro = mean of 10 task scores
**Authored:** 2026-08-11 (ADR-0026 v1 harness)
**Locked:** post_hoc_edit_locked per ADR-0016 + ADR-0022

## Three-input rubric

The scorer receives, per task-run:

1. **Tool-call trace:** ordered list of tool names invoked by the agent, plus argument shapes.
2. **Final file state:** post-run content of every file the task touches (from the harness's `execute_command('cat ...')` reads), plus the diff vs. fixture.
3. **Smoke test result (where available):** exit code + stdout/stderr of `smoke_test_command`, or null if the task has no smoke.

Additionally exposed to the scorer:

- `expected_tool_sequence`, `preferred_tools`, `dispreferred_tools` from the task JSON
- `expected_final_state` and `expected_final_state_mode` from the task JSON
- Turn count (number of `ActionEvent`s) + whether `max_iteration_per_run` was hit

## Task-specific correctness criteria

- BOTH files must be updated (exact_diff enforced on both).
- `math_ops.py`: `compute_total` -> `calculate_total` in the def line. Body unchanged.
- `main.py`: BOTH the import (`from math_ops import calculate_total`) AND the call site (`calculate_total([1,2,3])`).
- Common failure: forgetting to update `main.py` — band 40-59 (only one file correct).
- Common failure: only updating the definition, not the docstring reference — task said 'definition + docstring'; strict reading: since there's no docstring in the fixture, this is moot.
- Tool order tolerance: 'order_preserved_extra_reads_allowed' — extra reads OK.

## Scoring bands (apply to this task)

### 90-100 — Exemplary

- Correct final file state (matches `expected_final_state` per its mode).
- Tool sequence matches `expected_tool_sequence` (or is a valid variant per `expected_tool_sequence_tolerance`).
- Preferred tools used; dispreferred tools NOT used.
- Smoke test (if any) passes.
- Turn count is minimal (no unnecessary reads or edits).
- No `AgentErrorEvent`s.

### 75-89 — Correct with minor process flaws

- Correct final file state.
- Tool sequence differs from expected in a non-material way (e.g. one extra read, tool order slightly different but functionally equivalent).
- Smoke test passes.
- No functional defects; only style / efficiency deductions.

### 60-74 — Partially correct

- Final file state is close but has one non-trivial defect (e.g. off-by-one still present in a fix task, missing edge case, extra line preserved that should have been removed).
- OR tool sequence used a dispreferred tool (e.g. `execute_bash` sed on a task where `str_replace_editor` was preferred) but final state is still correct.
- Smoke test passes OR fails on a single non-critical case.

### 40-59 — Substantially incorrect

- Final file state has multiple defects, OR
- Correct field was changed but with collateral damage to other fields / formatting, OR
- Tool sequence violated a "do not modify" instruction (e.g. modified files on medium-05 or medium-08).
- Smoke test fails on the main case.

### 20-39 — Mostly failed

- Final file state does not achieve the task goal, OR
- Agent did not converge (e.g. hit `max_iteration_per_run=20`), OR
- Repeated `AgentErrorEvent`s.

### 0-19 — Failed

- No meaningful attempt, OR
- Fixture-seed failure (harness-side), OR
- Agent produced output but no file changes AND no diagnostic report (for medium-05/08).

## Deductions (applied on top of band selection)

- **-5**: hit `max_iteration_per_run=20` cap AND still landed in correct band.
- **-3**: used a dispreferred tool (per task) when preferred was available.
- **-2**: single trailing-whitespace / final-newline drift on an `exact_diff` task (whitespace-normalized would have matched).
- **-2**: extra read of a file already read this task.
- **-1 per unnecessary tool call** beyond the expected sequence, up to -5.

## Bonuses

- **+2**: solved in the minimum possible turn count (e.g. 2 turns for a read+edit task).
- **+2**: perfect adherence to instruction constraints ("do not modify", "minimal correction", "preserve behavior").

## Notes

- The scorer must ground each score in specific evidence from the trace + final state + smoke result. No "vibes" scoring.
- If the trace and final state disagree (e.g. tools ran but final state unchanged), score primarily on final state; note the discrepancy.
- If the smoke test fails but final state is correct per rubric, prefer rubric (smoke may have false-negative false alarms — e.g. environment differences).
