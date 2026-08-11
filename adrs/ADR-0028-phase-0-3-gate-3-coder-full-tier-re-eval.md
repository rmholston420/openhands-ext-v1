# ADR-0028 — Phase 0.3 gate-3 coder Full-tier re-eval (AWQ vs 35b, pre-registered)

**Status:** Proposed
**Lock-in phase:** Phase 0.3 gate-3
**Supersedes:** —
**Extends:** ADR-0022, ADR-0023, ADR-0026, ADR-0027

## Context

Phase 0.3 gate-2 closed with ADR-0027: AWQ (`qwen3-coder-30b-a3b-instruct-awq-4bit`, vLLM, GPU, :8501) confirmed as production coder on the Medium multi-turn task set (macro 85.4 vs 88.7 for 35b; 35b failed T05/T08 by omitting FinishAction on report-style tasks; both readings of the "35b <70 on any 2 tasks" clause converged on CONFIRM AWQ).

Two live signals justify a Full-tier re-eval rather than sitting on gate-2:

1. **35b dominated 7 of 10 targeted-edit Medium tasks** (T01, T02, T03, T04, T07, T09, T10) with cleaner minimum-turn behavior. The confirmation of AWQ came from 2 report-style tasks (T05, T08), not from 35b losing the edit class. Full-tier will re-test whether the edit dominance survives higher difficulty and whether the finish-omission failure mode survives a rubric that penalizes it explicitly.
2. **The T05/T08 finish-omission** is a reproducible failure signal (ADR-0027 §Sub-decision 6). It needs to be characterized *inside* a rubric that scores for it, not chased as a separate ad-hoc investigation. Full-tier gets this for free by keeping report-style tasks in the mix and adding an explicit finish-action clause to the reversal criteria.

The Medium harness (ADR-0026 v1.1) is production-ready: DockerWorkspace SDK path, tool_trace v1.1 (`list[dict]`), final_states capture, Perplexity-Max scoring authority, `post_hoc_edit_locked` rubric + gold. Full-tier reuses the same harness contract; only the task set and rubric anchor change.

## Decision

Open Phase 0.3 gate-3 as a **coder Full-tier multi-turn re-eval** with the pre-registered plan below. Filing status is **Proposed** until the task fixtures land; on fixture lock-in this ADR flips to **Ratified** and the task set + rubric + gold become `post_hoc_edit_locked=true`.

### Sub-decision 1 — Task set

**File:** `bench/tasks/coder-full-multi-turn.json` (scaffolded this commit, fixtures TBD).

**Shape:** 10 tasks at ~2× the Medium difficulty envelope. Composition (locked here, exact prompts filled in the follow-up commit):

| # | Class | Difficulty signal |
|---|---|---|
| F01 | Multi-file refactor with cross-module invariant | Rename + type-signature change threading through 3+ files; imports and call sites must all update; smoke test verifies runtime. |
| F02 | Real bug hunt with failing test as oracle | Test fails; agent must locate root cause across ≥2 files, not just patch the assertion. |
| F03 | Feature addition requiring read-first of unfamiliar module | Add a method to a class the agent has not seen; must preserve public API + existing tests. |
| F04 | Report-style: pytest failure summary with 3 failing tests across 2 files | **Report-style · DO NOT MODIFY.** Requires FinishAction with per-test breakdown. Direct successor to Medium T05, harder. |
| F05 | Report-style: git status + git log summary | **Report-style · DO NOT MODIFY.** Requires FinishAction with modified files + last 3 commit subjects. Direct successor to Medium T08, harder. |
| F06 | Exact-diff bug fix with regression test to be written after | Fix + add regression test that would have caught the bug. Both artifacts scored. |
| F07 | Configuration-driven behavior change | Modify config + code together such that a smoke command produces new expected output; test-set-scale change (not one line). |
| F08 | Error-handling addition to existing function | Add try/except path preserving happy-path bytes exactly; smoke tests both paths. |
| F09 | Dependency-graph reasoning: identify unused import cluster | Read-only analysis + FinishAction listing unused imports across N files. Report-style hybrid. |
| F10 | Docstring-driven implementation with 2 correct impls both accepted | Rubric_only. Same shape as Medium T10 but harder edge cases. |

- **3 report-style tasks (F04, F05, F09)** vs 2 at Medium — deliberate over-weight to force the T05/T08 failure mode to surface if it exists.
- **F02, F06, F07** are new classes not represented at Medium.
- All 10 use the same `expected_final_state` / `expected_final_state_mode` / `smoke_test_command` schema as Medium.

**Field schema:** identical to `bench/tasks/coder-medium-multi-turn.json` (harness_version v1.1, budget_tokens 8192, max_iteration_per_run 20, docker_image_expected + openhands_sdk_version_expected same, gold_hashes populated at fixture lock-in).

### Sub-decision 2 — Rubric

**File:** `bench/rubrics/full-scored.json` (created at fixture lock-in; **not** in this commit).

**Bands:** identical to `medium-scored.json` (90–100 Exemplary, 75–89 Correct-minor-flaws, 60–74 Partial, 40–59 Substantially-incorrect, 20–39 Mostly-failed, 0–19 Failed).

**Deductions/bonuses:** identical to Medium plus one new deduction class:

- **−10** for omitting a FinishAction on any report-style task (F04, F05, F09). This encodes the ADR-0027 §Sub-decision 6 signal directly into the rubric.
- **+2** minimum turn count (as Medium).
- **+2** perfect adherence to "do not modify" (as Medium).

**Scoring authority:** Perplexity Max (Claude Sonnet 4.6 via Perplexity Computer). Self-scoring by candidates prohibited. `post_hoc_edit_locked=true` at fixture lock-in.

### Sub-decision 3 — Candidates

Two candidates, no new runtimes:

- **AWQ (production):** `qwen3-coder-30b-a3b-instruct-awq-4bit`, vLLM, GPU, port :8501. Cell definition mirrors `bench/candidates/coder-medium-stage2-awq.json`; new file `bench/candidates/coder-full-awq.json` at fixture lock-in.
- **35b (challenger):** `qwen3_6-35b-a3b-q4kxl-gguf`, llama.cpp, GPU, port :8082. Cell definition mirrors `bench/candidates/coder-medium-stage2-35b.json`; new file `bench/candidates/coder-full-35b.json` at fixture lock-in.

No third candidate is opened at gate-3. Introducing one requires a separate ADR.

### Sub-decision 4 — Pre-registered reversal criteria (locked before scoring)

Post-hoc reinterpretation prohibited. Applied at run aggregation, not per-task.

**Rule 1 — Flip to 35b:**
- ALL 10 per-task scores of 35b ≥ 80
- AND 35b macro exceeds AWQ macro by ≥ 5 points
- AND 35b delivered a FinishAction on every report-style task (F04, F05, F09)

Notes: the ≥80 gate is stricter than Medium's ≥85 flip gate in absolute terms only because Full-tier bands allow more room in the 80–89 zone (harder tasks). The 5-pt lead threshold is stricter than Medium's >3 to reflect the seriousness of overturning a confirmed production selection (AWQ was just confirmed at gate-2).

**Rule 2 — Confirm AWQ:**
- AWQ macro exceeds 35b macro by ≥ 3 points
- OR 35b scores < 70 on any 2 of the 10 tasks
- OR 35b omits a FinishAction on ANY report-style task (F04, F05, F09)

The finish-action clause is the ADR-0027 §Sub-decision 6 follow-up made mechanical. Any recurrence auto-confirms AWQ.

**Rule 3 — Intermediate (confirm AWQ + log per-task mix):**
- Rules 1 and 2 do not both cleanly fire.

Ambiguity resolution rule (learned from ADR-0027): boundary values on inequality thresholds default to the interpretation that preserves the incumbent (confirms AWQ). Recorded here so it does not need to be re-litigated during scoring.

### Sub-decision 5 — Definition of Done

Phase 0.3 gate-3 DoD:

1. `bench/tasks/coder-full-multi-turn.json` fixtures locked; gold_hashes populated; `post_hoc_edit_locked=true` at lock-in.
2. `bench/gold/coder-full-multi-turn/` per-task rubric files written and hash-locked.
3. `bench/rubrics/full-scored.json` written and hash-locked.
4. `bench/candidates/coder-full-awq.json` and `bench/candidates/coder-full-35b.json` land.
5. Both candidate probes on disk: v1.1 shape, 10/10 R1/R2 verdict=pass, agent_errors=0, run_errors=0, harness_commit_sha recorded.
6. Perplexity-Max scoring pass complete against gold; per-task scores + macro means logged.
7. Reversal criteria applied mechanically; verdict ADR filed (new ADR-0029 for the verdict, following the ADR-0024→ADR-0025 pattern).

### Sub-decision 6 — Reservation

- **ADR-0029 reserved** for the Full-tier verdict (follows the ADR-0024→ADR-0025 verdict-of-a-probe pattern).
- No cascading amendment to ADR-0017 / ADR-0023 / ADR-0026 / ADR-0027 pre-emptively; only the verdict ADR may amend those rows.

## Rationale

Alternatives considered:

- **Skip Full-tier; promote coder-medium result and freeze coder role.** Rejected: Medium result depended on 2 report-style failures out of 10 tasks. Freezing without stressing the harness at Full-tier leaves the 35b edit dominance uncharacterized and the finish-omission failure class un-instrumented in a scored rubric.
- **Open embedder Full-tier or planner Full-tier as gate-3.** Rejected as this gate's target: planner is double-confirmed (ADR-0023 → ADR-0025) with low re-eval information gain; embedder needs a different rubric class (recall-mode signals, not correctness bands) than the coder/planner Medium harness — wrong tool for this gate. Both remain valid future gates.
- **Introduce a third coder candidate at Full-tier** (e.g. a Q6_K coder variant, or a coder-planner-hybrid cell). Rejected: adds candidate-orthogonal complexity and would need its own ADR. Full-tier's job is to characterize the AWQ vs 35b signal already surfaced at Medium.
- **Loosen the finish-action rule** to a soft deduction instead of a hard auto-confirm trigger. Rejected: silent exit without answering is a quality-first veto class, not a nuance. Mechanical rule is the correct instrument.

## Consequences

- **Files created this commit:**
  - `adrs/ADR-0028-phase-0-3-gate-3-coder-full-tier-re-eval.md` (this file)
  - `adrs/README.md` (index row added)
  - `bench/tasks/coder-full-multi-turn.json` (scaffold; UNFROZEN)
- **Files created at fixture lock-in (follow-up commit):**
  - `bench/tasks/coder-full-multi-turn.json` — fixtures + prompts + gold_hashes populated; `post_hoc_edit_locked=true`
  - `bench/gold/coder-full-multi-turn/*.md` — per-task rubric files
  - `bench/rubrics/full-scored.json`
  - `bench/candidates/coder-full-awq.json`
  - `bench/candidates/coder-full-35b.json`
- **ADR status transition:** Proposed → Ratified on fixture lock-in commit; index row updated.
- **PORTING_LEDGER:** no change (no new vendor).
- **BUILD_LOG:** one entry for gate-3 opener; second entry at fixture lock-in.
- **SESSION_HANDOFF:** overwritten with gate-3 pointer and current fixture status.
- **ADR-0029:** reserved for the verdict, filed after scoring.

## Lock-in phase

Phase 0.3 gate-3. Fixtures + rubric become `post_hoc_edit_locked=true` at the lock-in commit; verdict lands in ADR-0029.

## References

- ADR-0022 (medium task set + gold protocol)
- ADR-0023 (Phase 0.3 router selection)
- ADR-0026 (coder multi-turn correctness harness v1, amendment 3)
- ADR-0027 (Phase 0.3 gate-2 verdict: CONFIRM AWQ)
- `bench/tasks/coder-medium-multi-turn.json` (Medium schema donor)
- `bench/rubrics/medium-scored.json` (rubric shape donor)
- `bench/candidates/coder-medium-stage2-awq.json` and `bench/candidates/coder-medium-stage2-35b.json` (candidate cell donors)
