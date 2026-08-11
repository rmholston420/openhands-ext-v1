# Gold rubric — coder-full-09-unused-import-cluster-analysis

**Task prompt (verbatim):**
> In /workspace/repo, several source files under src/ import symbols they never use. DO NOT modify any file. Analyze the sources and, in your Finish message, list every unused import as 'path/to/file.py: <import statement>'. Be exhaustive across all files under src/. If a symbol is exported via __all__ or re-exported, it counts as used.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Report-style task · DO NOT MODIFY**
**Locked:** post_hoc_edit_locked per ADR-0028

## Expected unused imports (6 total)

1. `src/a.py: import sys`
2. `src/a.py: import json`
3. `src/b.py: from typing import Any, Optional` (both `Any` and `Optional` unused; either "from typing import Any, Optional" or two separate entries acceptable)
4. `src/c.py: import math`
5. `src/c.py: import statistics`
6. `src/c.py: from collections import defaultdict` (only `defaultdict` — `Counter` IS used)

**Used symbols (must NOT be flagged):**
- `src/a.py: import os` — used in `os.environ.get`
- `src/b.py: from pathlib import Path` — used in return type + body
- `src/b.py: import re` — used in `re.sub`
- `src/c.py: from collections import Counter` — used in `count()` body
- `src/c.py: __all__` contains `"count"` — the `count` function is exported

## Correctness criteria

- Files under `src/` MUST be byte-identical at task end (immutable check).
- FinishAction MUST list all 6 unused imports (or 7 if `Any` and `Optional` split into separate entries).
- FinishAction MUST NOT list any used import as unused.
- Path format `path/to/file.py: <import statement>` preferred; other clear formats acceptable.

## Scoring bands

### 90-100 — Exemplary
- All 6 unused imports listed. No used imports flagged.
- Files untouched.
- Turn count minimal (list src/ → read files → finish).

### 75-89 — Correct with minor process flaws
- 5 of 6 unused imports listed (missed one).
- OR listed all 6 but format inconsistent.

### 60-74 — Partially correct
- 4 of 6 listed.
- OR listed all 6 but ALSO flagged 1-2 used imports (e.g. flagged `Counter` because misread `__all__`).

### 40-59 — Substantially incorrect
- Files modified (band cap).
- OR ≤3 of 6 unused imports listed.
- OR flagged 3+ used imports as unused.

### 20-39 — Mostly failed
- No coherent list; agent tried to "fix" by removing imports (files modified → band cap).

### 0-19 — Failed
- **No FinishAction present.** (Automatically triggers reversal rule 2 clause 3.)
- OR FinishAction present but empty.

## Deductions
- −10 for omitting FinishAction on this report-style task
- −5 hit max_iter=20
- −5 (band cap) file modification

## Bonuses
- +2 minimum turn count
- +2 perfect adherence to "DO NOT modify"

## Reversal-criteria signal
- **Absent FinishAction on this task auto-fires confirm-AWQ rule (rule 2 clause 3).**
