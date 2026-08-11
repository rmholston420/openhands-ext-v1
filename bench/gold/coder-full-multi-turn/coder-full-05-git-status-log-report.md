# Gold rubric — coder-full-05-git-status-log-report

**Task prompt (verbatim):**
> In /workspace/repo, report the current git working-tree state and recent history. DO NOT modify, add, or commit anything. In your Finish message, list: (1) every file shown as modified or staged, with its status letter (M/A/D/R/etc), and (2) the last 3 commit subjects (newest first). Do not run `git add`, `git commit`, `git reset`, `git checkout`, or `git stash`.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Report-style task · DO NOT MODIFY**
**Locked:** post_hoc_edit_locked per ADR-0028

## Fixture setup

- The harness runs `bash /workspace/repo/.setup_script.sh` before the agent starts, which initializes the git repo, creates 3 commits, and leaves 2 files dirty in the working tree.

## Expected report content

**Modified files (2):**
- `M src/main.py`
- `M README.md`

**Last 3 commit subjects (newest first):**
1. `changelog: v2 release note`
2. `update main to v2`
3. `initial import`

## Correctness criteria

- `execute_bash` must be used to inspect (`git status`, `git log`, or equivalent).
- Working tree at task end must be byte-identical to the post-setup state (immutable check): 2 dirty files, same 3-commit history, no new commits.
- FinishAction MUST list both modified files with M status letter AND all 3 commit subjects in the correct newest-first order.
- No `git add`, `git commit`, `git reset`, `git checkout <path>`, or `git stash` in the trace.

## Scoring bands

### 90-100 — Exemplary
- Both files named with M. All 3 commit subjects in correct order.
- Turn count near minimum (git status → git log → finish).

### 75-89 — Correct with minor process flaws
- Both files + 3 subjects correct but commits listed oldest-first instead of newest-first.
- Extra bash calls (e.g. `git diff`).

### 60-74 — Partially correct
- Only 1 of 2 modified files listed.
- OR only 2 of 3 commit subjects listed.

### 40-59 — Substantially incorrect
- Any of: `git add`, `git commit`, `git reset`, `git checkout <path>`, `git stash` executed (band cap).
- OR working tree state changed (files were staged, unstaged, or reset).
- OR wildly wrong commit list.

### 20-39 — Mostly failed
- Multiple prohibited git commands executed.
- OR working tree corrupted.

### 0-19 — Failed
- **No FinishAction present.** (Automatically triggers reversal rule 2 clause 3.)
- OR FinishAction present but reports nothing structured.

## Deductions
- −10 for omitting FinishAction on this report-style task
- −5 hit max_iter=20
- −5 (band cap) any prohibited git write command

## Bonuses
- +2 minimum turn count
- +2 perfect adherence to "DO NOT modify/add/commit"

## Reversal-criteria signal
- **Absent FinishAction on this task auto-fires confirm-AWQ rule (rule 2 clause 3).**
