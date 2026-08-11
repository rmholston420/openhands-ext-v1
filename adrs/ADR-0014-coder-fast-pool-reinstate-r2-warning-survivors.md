# ADR-0014 — Coder-fast pool reinstates R2-warning survivors after harness rubric-compliance fix

**Status:** Ratified
**Lock-in phase:** Phase 0.1
**Supersedes:** — (partially overrides ADR-0011 AMENDMENT 3 and the coder-fast pool lock entries at BUILD_LOG 2026-08-11 04:36 EDT and 2026-08-11 04:45 EDT)

## Context

`bench/rubrics/fast-elimination.json` R2 states unambiguously:

> trigger: "more than 1 task returns malformed output for the candidate"
> action: "eliminate candidate"

Prior to 2026-08-11 05:10 EDT the runner's `_apply_fast_rubric` (`bench/runner/main.py`) had a code path that, when `malformed == 1` (a non-eliminating R2-warning per rubric text), delegated the run-level verdict to `verdict_from_probe`, which returns "fail" if *any* task's verdict != "pass". Effect: any single-task malformation produced a full-cell "fail" — a strictly-stricter policy than the ratified R2 threshold ">1".

Two coder-fast pool decisions were made under this buggy code path:

1. **BUILD_LOG 2026-08-11 04:36 EDT** eliminated `qwen3-coder-30b-a3b-instruct-awq-4bit` from the coder-fast pool. Justification recorded verbatim: "Task 02 fails on model semantic tool-selection (chose `execute_bash cat config.py` for a file-edit task instead of `str_replace_editor`/`write_file`). **Fast-elimination rubric = any-fail → cell fail.**" — precisely the misinterpretation the harness bug encoded.

2. **BUILD_LOG 2026-08-11 04:45 EDT** eliminated `qwen3_6-27b-q6k-gguf` from the coder-fast pool. Justification: single Task-02 tool-selection stall (`read_file` before `str_replace_editor`), treated as full-cell R2 fail.

The harness bug was fixed in commit `9d4f6b0` (2026-08-11 05:10 EDT). The rubric file itself was never edited (`post_hoc_edit_policy` honored). Existing result JSONs were rescored deterministically by `scripts/rescore-fast-verdicts.py` from their `.probe.json` sidecars against the corrected harness.

**Post-rescore evidence** (summary via `scripts/summarize-fast-verdicts.py`, runs with probes only):

| Candidate | Runtime | Runs w/probe | Pass | Fail |
|---|---|---:|---:|---:|
| qwen3-30b-a3b-thinking-2507-awq | vllm/gpu | 5 | 5 | 0 |
| qwen3-coder-30b-a3b-instruct-awq-4bit | vllm/gpu | 2 | 1 | 1 |
| qwen3_6-27b-q6k-gguf | llama.cpp/gpu | 4 | 4 | 0 |
| qwen3_6-35b-a3b-q4kxl-gguf | llama.cpp/gpu | 4 | 4 | 0 |

Under the ratified rubric R2 (">1 malformed → eliminate"), both previously-eliminated candidates now show at least one run that passes without R2 elimination triggering. `qwen3_6-27b-q6k-gguf` shows 4/4 pass across all rescored runs. `qwen3-coder-30b-a3b-instruct-awq-4bit` shows 1 pass with R2-warning + 1 fail; per the ratified rubric, a single passing run at Fast tier (which is triage-only, not stability-scored) meets the elimination threshold — Medium tier characterizes variance.

## Decision

The coder-fast pool is restored to include both previously-eliminated candidates, producing a 4-cell locked pool for Phase 0.1 coder-fast:

1. `qwen3-30b-a3b-thinking-2507-awq` — vllm/gpu (unchanged; dual-role per ADR-0012)
2. `qwen3-coder-30b-a3b-instruct-awq-4bit` — vllm/gpu (reinstated; parser `qwen3_coder` per ADR-0011)
3. `qwen3_6-27b-q6k-gguf` — llama.cpp/gpu (reinstated; dual-role per registry)
4. `qwen3_6-35b-a3b-q4kxl-gguf` — llama.cpp/gpu (unchanged; dual-role per registry)

**No re-run is required.** The rescored `.json` result files are authoritative evidence because:
- The rubric text was never edited.
- Rescoring is deterministic from persisted `.probe.json` sidecars.
- The rescore tool stamps the harness commit SHA into each rewritten JSON.

## Rationale

Alternatives considered:

- **Alt A — Reinstate 27B Q6_K only.** Rejected: same rubric bug drove both eliminations; correcting only the cleaner one leaves the other elimination standing on a bug-driven justification. That is inconsistent with §0.0a bullet 3 (post-hoc rubric editing prohibition) — the rubric text was NEVER edited; only the buggy code path was fixed. Reinstate scope must match the scope of the bug.

- **Alt B — Reinstate + require a fresh 3-repeat confirmation smoke.** Rejected: Fast tier is elimination-only by rubric design (scoring is off; see rubric `scoring.enabled=false`). Confirmation stability is a Medium-tier concern per spec §0.2 ("shortlist size 2–3 per role carried to Full tier"). Requiring a re-run at Fast tier before restoring evidence-supported pool membership would be inventing a stability gate not present in the ratified rubric.

- **Alt C — Keep the prior 2-cell lock as "good-faith interpretation".** Rejected: the eliminations were made under a code bug that violated the rubric text. §0.0a bullet 3 forbids post-hoc rubric edits precisely to prevent moving-the-goalposts; keeping a bug-driven pool contraction on the record inverts that discipline (it silently narrows the rubric via code rather than text). The rubric text is authoritative; the harness must comply. Now it does.

Quality-over-speed rule (saved user preference) applied at pool-scope level: quality is served by carrying the broadest evidence-supported candidate set into Medium tier, not by narrowing it under a code artifact. Speed of Medium tier will not meaningfully suffer from 4 vs 2 candidates at that scope.

## Consequences

- `bench/candidates/coder-fast-pool.json` grows from 2 → 4 cells (add coder-instruct AWQ + 27B Q6_K llama.cpp).
- `adrs/ADR-0011-fast-tier-coder-tool-call-parser-hermes.md` receives a STATUS AMENDMENT block: AMENDMENT 3's eliminations are reversed under ADR-0014 by evidence rescored against the same ratified rubric. ADR-0011's parser-per-cell mechanism is unaffected.
- `BUILD_LOG.md` gains an entry recording the reinstate + ADR-0014 filing.
- `DEBUG_LOG.md` already carries the 2026-08-11 05:10 EDT rubric-compliance bug entry that is the root cause of both original eliminations.
- No `PORTING_LEDGER.md` change — no OSS component adopted, rejected, or replaced; both models were already vendored.
- No rubric-file change (`bench/rubrics/fast-elimination.json` untouched, `post_hoc_edit_policy` honored).
- No test change; no runner-code change beyond the already-committed `9d4f6b0`.
- Medium-tier queue: coder role now enters with a 4-cell shortlist, not 2. Spec §0.2 Verification "Shortlist size 2–3 per role" is exceeded by 1; that is a permitted overhead for Fast → Medium narrowing (spec bounds the Full-tier shortlist, not the Medium-tier admission set).

## Lock-in phase

Phase 0.1 (Fast tier). Locks the coder-fast pool going into Phase 0.2 Medium tier.

## References

- `bench/rubrics/fast-elimination.json` (R2 ratified 2026-08-11 05:51 UTC)
- `bench/runner/main.py::_apply_fast_rubric` (fixed commit `9d4f6b0` 2026-08-11 05:10 EDT)
- `scripts/rescore-fast-verdicts.py`, `scripts/summarize-fast-verdicts.py`
- `DEBUG_LOG.md` 2026-08-11 05:10 EDT — rubric-compliance bug diagnosis
- `BUILD_LOG.md` 2026-08-11 04:36 EDT — original coder-instruct elimination (reversed here)
- `BUILD_LOG.md` 2026-08-11 04:45 EDT — original 27B Q6_K elimination (reversed here)
- ADR-0007 (fast-tier methodology)
- ADR-0011 (parser-per-cell; AMENDMENT 3 partially reversed)
- ADR-0012 (30B thinker dual-role)
- Spec §0.0a bullet 3 (post-hoc rubric editing prohibition)
- Spec §0.2 Verification (shortlist size 2–3 per role at Full tier)
