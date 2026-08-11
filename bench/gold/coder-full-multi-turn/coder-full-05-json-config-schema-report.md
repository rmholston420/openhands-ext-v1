# Gold rubric — coder-full-05-json-config-schema-report

**Task prompt (verbatim):**
> In /workspace/repo, three JSON config files live under config/ (app.json, db.json, cache.json). DO NOT modify any file. Read all three and, in your Finish message, produce a schema report with two sections: (1) for each file, a line 'config/<name>.json: keys=[k1, k2, ...]' listing its top-level keys in the order they appear; (2) a 'Shared keys:' line listing every top-level key that appears in ALL THREE files (sorted alphabetically). If no key is shared by all three, write 'Shared keys: none'.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Report-style task · DO NOT MODIFY**
**Locked:** post_hoc_edit_locked per ADR-0028 (amended 2026-08-11 12:17 EDT — F05 class swap for runner constraint)
**Amendment reason:** original F05 required a `fixture_setup_command` hook to seed a git repo pre-run, but `bench/runner/probes.py` does not honor that field. F05 replacement preserves the report-style class, the DO NOT MODIFY invariant, and the finish-action clause in the reversal criteria.

## Expected report content

**Section 1 — per-file key lists (order-of-appearance):**
- `config/app.json: keys=[name, version, debug, timeout_seconds]`
- `config/db.json: keys=[name, host, port, timeout_seconds, pool_size]`
- `config/cache.json: keys=[name, backend, host, ttl_seconds, timeout_seconds]`

**Section 2 — shared keys (present in ALL THREE, alphabetized):**
- `Shared keys: name, timeout_seconds`

## Correctness criteria

- Files under `config/` MUST be byte-identical at task end (immutable check, scorer-enforced).
- `read_file` (or equivalent `execute_bash cat`) must appear in the trace for each of the three config files.
- FinishAction MUST list all three per-file key sets with correct keys.
- FinishAction MUST correctly identify the shared keys as `name` and `timeout_seconds`.
- Key-order in section 1 is order-of-appearance in the JSON (not sorted). Section 2 IS sorted alphabetically.

**Why these are the shared keys:**
- `name` appears in all three ✓
- `timeout_seconds` appears in all three ✓
- `host` appears only in db.json + cache.json (not app.json) ✗
- All other keys are unique to a single file.

## Scoring bands

### 90-100 — Exemplary
- All 3 per-file key lists correct + correct shared-keys line.
- Files preserved.
- Turn count minimal (read × 3 → finish).

### 75-89 — Correct with minor process flaws
- All key sets correct but section 1 keys sorted alphabetically instead of in appearance order (minor spec deviation).
- OR shared-keys line missing "sorted alphabetically" ordering (but keys correct).
- Extra reads or verification bash calls.

### 60-74 — Partially correct
- 2 of 3 per-file key lists correct + correct shared-keys line.
- OR all 3 key lists correct + shared keys list has ONE error (e.g. included `host` from 2 files, or missed `timeout_seconds`).

### 40-59 — Substantially incorrect
- Files modified in any way (band cap regardless of report quality).
- OR only 1 of 3 per-file key lists correct.
- OR shared-keys line reports the union or intersection of just two files.

### 20-39 — Mostly failed
- No coherent report; agent read fewer than 2 files.
- OR agent modified files AND failed to report.

### 0-19 — Failed
- **No FinishAction present.** (Automatically triggers reversal rule 2 clause 3 in aggregation.)
- OR FinishAction present but empty of schema information.

## Deductions
- −10 for omitting FinishAction on this report-style task (see full-scored.json)
- −5 hit max_iter=20
- −5 (band cap) any file modification

## Bonuses
- +2 minimum turn count
- +2 perfect adherence to "DO NOT modify"
- +2 correct order-of-appearance key ordering (not sorted) in section 1

## Reversal-criteria signal
- **Absent FinishAction on this task auto-fires confirm-AWQ rule (rule 2 clause 3).** Recorded here so the scorer flags it explicitly during aggregation.
