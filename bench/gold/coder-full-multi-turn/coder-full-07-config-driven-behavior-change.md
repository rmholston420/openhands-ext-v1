# Gold rubric — coder-full-07-config-driven-behavior-change

**Task prompt (verbatim):**
> In /workspace/repo, the script scripts/greet.py reads /workspace/repo/config/greet.json and prints a greeting. Change BOTH the config file AND the script so that running `python scripts/greet.py --name Ada` prints 'Bonjour, Ada!' (was 'Hello, Ada!'). Do not hardcode the greeting inside the script — the greeting must still be read from config. Preserve the script's CLI (--name argument, help text).

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Locked:** post_hoc_edit_locked per ADR-0028

## Correctness criteria

- Running `python scripts/greet.py --name Ada` MUST print exactly `Bonjour, Ada!`.
- `config/greet.json` `greeting` field MUST be `"Bonjour"` (punctuation `"!"` unchanged).
- Script MUST still read greeting from config (no hardcoded string `"Bonjour"` in `scripts/greet.py`).
- Script CLI (`--name`) preserved.

**Prompt note:** prompt says "change BOTH the config file AND the script." A strict reading requires a script edit; a permissible reading accepts config-only if the script already correctly reads from config (which it does in this fixture). Both paths scored — config-only is acceptable but strict readers may downgrade to 75-89 band.

## Scoring bands

### 90-100 — Exemplary
- Config edited to `"Bonjour"`. Script optionally reordered/re-imported cosmetically or left unchanged.
- Smoke prints exactly `Bonjour, Ada!`.
- Turn count minimal (read config → edit config → optional read script → smoke).

### 75-89 — Correct with minor process flaws
- Config-only edit (strict-reader downgrade).
- OR script cosmetically modified (import reordering, docstring change) with no functional impact.
- Extra reads or verification runs.

### 60-74 — Partially correct
- Script prints `Bonjour, Ada` (missing punctuation) or `Bonjour Ada!` (missing comma).
- OR script edit unnecessarily changes format string but greeting still comes from config.

### 40-59 — Substantially incorrect
- Greeting hardcoded in script (band cap).
- OR CLI `--name` argument changed/removed.

### 20-39 — Mostly failed
- Script doesn't run.
- OR prints original `Hello, Ada!` (no config change).

### 0-19 — Failed
- No edits.

## Deductions
- −5 hit max_iter=20
- −3 dispreferred tool
- −5 (band cap) hardcoded greeting in script

## Bonuses
- +2 minimum turn count
- +2 no unnecessary edits to script
