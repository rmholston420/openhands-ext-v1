# ADR-0029 — Phase 0.3 gate-3 coder verdict: CONFIRM AWQ

**Status:** Ratified
**Lock-in phase:** Phase 0.3 gate-3
**Supersedes:** —
**Related:** ADR-0027 (gate-2 verdict CONFIRM AWQ, superseded by this Full-tier re-eval), ADR-0028 (gate-3 opener; task-set + rubric + reversal criteria lock-in), ADR-0022 (gold protocol), ADR-0026 (coder harness v1)

## Context

ADR-0028 committed a Full-tier re-eval of the coder role (AWQ vs 35b-q4kxl) with a 10-task multi-turn Full task-set including 3 report-style tasks (F04, F05, F09). Reversal criteria were **pre-registered and locked** in `bench/tasks/coder-full-multi-turn.json` before any Full-tier scored run. Post-hoc interpretation of criteria is prohibited.

Runner verification (SESSION_HANDOFF 2026-08-11 12:24 EDT) established that both cells would take the real SDK + Docker path (SDK 1.41.0, docker0=172.17.0.1, digest resolved) — no stubbed fallback. Both probes then executed end-to-end with ws_boot ~4.4s and `sdk_version=1.41.0` in metadata.

## Decision

**Retain `Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` (vLLM) as the production coder.** The Full-tier retest re-confirms ADR-0027's gate-2 verdict.

## Rationale

### Per-task scores (Perplexity-Max scored against locked gold)

| Task | AWQ | 35b | Δ | Report-style |
|---|---:|---:|---:|:---:|
| F01 multifile-refactor-with-invariant | 60 | 78 | +18 | |
| F02 bug-hunt-cross-module | 92 | 94 | +2 | |
| F03 feature-add-read-first-unfamiliar | 94 | 96 | +2 | |
| F04 pytest-multi-failure-report | 78 | 5 | −73 | ✓ (no finish) |
| F05 json-config-schema-report | 94 | 5 | −89 | ✓ (no finish) |
| F06 exact-diff-fix-plus-regression-test | 93 | 95 | +2 | |
| F07 config-driven-behavior-change | 92 | 94 | +2 | |
| F08 error-handling-addition | 92 | 93 | +1 | |
| F09 unused-import-cluster-analysis | 92 | 5 | −87 | ✓ (no finish) |
| F10 docstring-driven-impl-two-accepted | 94 | 95 | +1 | |
| **Macro** | **88.1** | **66.0** | **−22.1** | |

Detailed per-task scoring rationale: `bench/scoring/full-coder/SCORING_20260811.md`.

### Reversal-criterion evaluation (mechanical, ADR-0028 §pre-locked)

**`flip_to_35b_a3b_q4kxl_if`** (requires all three; ALL FAIL):
1. All 10 35b scores ≥80 — **FAILS** (F04=5, F05=5, F09=5)
2. 35b macro − AWQ macro ≥5 — **FAILS** (35b LOWER by 22.1)
3. 35b delivered FinishAction on every report-style task — **FAILS** (missing on all 3)

**`confirm_awq_if`** (requires any one; ALL THREE FIRE):
1. AWQ macro exceeds 35b macro by ≥3 — **FIRES** (Δ=22.1)
2. 35b scores <70 on any 2 of 10 tasks — **FIRES** (3 tasks at score=5)
3. 35b omits FinishAction on ANY report-style task — **FIRES** (missing on F04, F05, F09)

**Verdict: CONFIRM AWQ** (three independent clauses fire; unambiguous).

### Failure-mode signal (informational, not a criterion)

The Full-tier retest reveals the exact failure mode ADR-0027's post-medium report-style probe predicted: `qwen3_6-35b-a3b-q4kxl-gguf` reliably completes mechanical code-modification tasks (F01–F03, F06–F08, F10) — often at fewer turns than AWQ — but does not emit a `FinishAction` on report-style deliverables. On F04, F05, and F09 the agent read the necessary files (or ran pytest) and then simply stopped without emitting the report the task required. Because report-style tasks make the deliverable **only** the finish-action payload, this drops those tasks to functional zero. The −10 rubric deduction is a secondary signal here; the primary is that the deliverable is absent.

AWQ delivered FinishAction on all 3 report-style tasks with substantially correct content (F04: correct test names + reasons but wrong pass count in summary; F05, F09: fully correct).

### Wall-time tiebreak (not applicable)

35b median wall-time (7.7s) is faster than AWQ (9.4s), but the tiebreak clause requires the top two cells to be within 3 quality points — they are 22.1 apart. Speed is informational only.

## Consequences

- **Production coder unchanged:** ADR-0027 verdict re-confirmed at Full tier. `select_role_coder()` continues to resolve to `qwen3-coder-30b-a3b-instruct-awq-4bit` on vLLM.
- **`select_model` MCP tool (deferred ADR):** The Full-tier data does NOT produce a multi-model split — no per-task cell mix warrants dynamic switching. Deferred ADR for `select_model` inclusion remains unratified and unbuilt.
- **35b remains a candidate** for future re-eval only if a superseding ADR authors a NEW task-set that specifically probes the report-style failure with corrective prompt engineering. This ADR does NOT authorize such an ADR; retiring 35b from candidate pool for the coder role is deferred to Phase 1.
- **Files preserved (never deleted):**
  - `bench/scoring/full-coder/probes/{awq,35b}.probe.json` (raw probe outputs, 203KB + 123KB)
  - `bench/scoring/full-coder/probes/{awq,35b}.meta.json` (harness metadata)
  - `bench/scoring/full-coder/probes/{awq,35b}_v2.txt` (compact extractions used for scoring)
  - `bench/scoring/full-coder/SCORING_20260811.md` (per-task scoring rationale)
- **Rubric + task-set integrity confirmed:** `bench/rubrics/full-scored.json` and `bench/tasks/coder-full-multi-turn.json` were `post_hoc_edit_locked` before scoring; no edit occurred. F05 amendment (2026-08-11 12:17 EDT) preceded first probe run and is documented in ADR-0028.

## Alternatives considered

1. **Flip to 35b anyway on wall-time speed** — Rejected. Speed is a tiebreak *only* within 3 quality points; the gap is 22.1. Also violates ADR-0028's locked criteria.
2. **Re-run 35b with an explicit "you must call finish" system prompt injection** — Rejected. Post-hoc prompt modification of a locked bench is exactly what `post_hoc_edit_locked` and "no post-hoc reinterpretation" prohibit. If we want to probe with a hardened finish-eliciting system prompt, that requires a superseding ADR + new locked task-set (deferred).
3. **Declare INTERMEDIATE and log per-task mix** — Rejected. INTERMEDIATE fires *only* when neither flip nor confirm criteria cleanly fire. Confirm fires on three independent clauses; verdict is not INTERMEDIATE.

## Lock-in phase

Phase 0.3 gate-3 closes with this ADR. Phase 0.4 (embedder Full-tier re-eval) is the next gate.

## References

- `adrs/ADR-0027-phase-0-3-gate-2-coder-verdict-confirm-awq.md` — gate-2 CONFIRM AWQ
- `adrs/ADR-0028-phase-0-3-gate-3-coder-full-tier-re-eval.md` — gate-3 opener, task-set + rubric + reversal criteria lock-in
- `bench/rubrics/full-scored.json` — locked scoring rubric
- `bench/tasks/coder-full-multi-turn.json` — locked task-set (F05 amended per ADR-0028)
- `bench/gold/coder-full-multi-turn/*.md` — locked gold rubrics per task
- `bench/scoring/full-coder/SCORING_20260811.md` — per-task scoring rationale
- `bench/scoring/full-coder/probes/*.probe.json` — raw probe artifacts (commit 7a03d49)
- `BUILD_LOG.md` 2026-08-11 12:46 EDT entry
