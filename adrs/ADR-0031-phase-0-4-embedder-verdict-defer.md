# ADR-0031 — Phase 0.4 gate-4 embedder verdict: DEFER (accept 4-query calibration, retain 4B-Q8 incumbent)

**Status:** Ratified
**Lock-in phase:** Phase 0.4 gate-4
**Supersedes:** —
**Amends:** ADR-0030 (fixture proposal)

## Context

ADR-0030 defined a Phase 0.4 embedder re-eval as a 3-way Qwen comparison (0.6B-Q8, 4B-Q8 incumbent, 8B-Q6_K) plus nomic-embed-code as an informational cross-family sanity check. The DoD required labeling all 3324 pool rows across 40 queries and computing macro nDCG@10 / Recall@10 / MRR@10 / Recall@1 per cell to trigger V3+W3 reversal criteria.

Labeling all 3324 rows would consume 2-4 Perplexity-Max sessions (per rubric G2 budget). To validate the labeling driver + rubric before committing that budget, a 4-query calibration slice was labeled (q-c01 real slice from s01 + q-d29 + q-c40 + q-d18, plus q-c09 + q-c32 as unanswerable-at-pinned-SHA verifications). Combined qrels locked at SHA256 `f7137c7bebbf9b10da14091488c185921f4cda2e071880c838eefff4aaca48f8` (437 rows across 4 answerable queries).

An offline scorer (`bench/scoring/embedder-full-multi-block-calibration/score_offline.py`) reads step-6b per-cell top-20 output + the locked qrels and computes rubric metrics without re-running any embedder.

## Calibration results (N=4 queries, 2 code + 2 docs)

Composite = `100 * (0.40*nDCG@10 + 0.25*R@10 + 0.20*MRR@10 + 0.15*R@1)`.

| cell | role | nDCG@10 | R@10 | MRR@10 | R@1 | composite |
|---|---|---|---|---|---|---|
| e006b_q8_cpu | 0.6B Q8 downsize | 0.126 | 0.051 | 0.494 | 0.017 | **16.41** |
| e04b_q8_cpu | 4B Q8 incumbent | 0.254 | 0.142 | 0.750 | 0.028 | **29.11** |
| e08b_q6k_cpu | 8B Q6_K upsize | 0.321 | 0.206 | 0.685 | 0.023 | **32.04** |
| enomicc_q6k_gpu | nomic informational | 0.283 | 0.126 | 0.702 | 0.028 | **28.94** |

Observations (facts, not reversal-criteria interpretation):
- 8B leads on 3 of 4 metrics; 4B leads MRR.
- 0.6B has one all-zero sub-cell (H1 docs).
- nomic sits between 4B and 8B on composite.
- Recall@1 is near-zero across all cells at this pool depth × chunker split.

## Decision

**DEFER the ADR-0030 verdict. Retain 4B-Q8 as production embedder incumbent.**

Specifically:
1. **Do not file a V3+W3 verdict** (confirm / flip / intermediate) at this labeling depth. The rubric requires 20 queries/block for stable macro; N=4 is calibration signal only and cannot cross the reversal thresholds defensibly.
2. **Retain 4B-Q8 (e04b_q8_cpu)** as the production embedder pending future re-eval. No swap.
3. **Do not ratify ADR-0030's fixture.** ADR-0030 remains Proposed. The pool artifact, rubric, and locked calibration qrels persist as-is; future full-labeling work resumes from this state without redoing step 6b.
4. **ADR-0030b (co-residency viability)** — decoupled. Post-verdict co-residency testing is now conditional on a future full re-eval that produces a defensible quality winner. ADR-0030b status stays Proposed; no execution required at this time.
5. **Corpus SHAs at calibration lock:** openhands-ext-v1 `a9d5bd6`, Kosmos `1f33519a`, Rigpa-LMS `55b55539`. Recorded in the locked qrels header.
6. **No post-hoc rubric changes.** `post_hoc_edit_locked=true` remains per ADR-0016 + ADR-0022. If future full re-eval finds a rubric weakness (e.g. Recall@1 near-zero across all candidates suggests low discriminative value at 15% weight), that requires a spec-amendment ADR before re-scoring.

## Rationale

- **N=4 is below the rubric's stability threshold.** ADR-0030 sub-decision 5 (V3+W3) requires 20 queries/block. Filing a verdict at N=4 would violate the pre-registered protocol.
- **Retention beats speculative swap.** 8B leads calibration composite by ~3 points over 4B, but that margin is well inside the noise band for N=4 and does not clear any reversal predicate. Swapping the incumbent on unratified signal is worse than deferring.
- **Sunk cost is preserved, not wasted.** Step 6b's 16-cell pool run (~38 minutes GPU cold) is durable: the per-cell top-20 files persist on Colossus and can be re-scored offline against any future qrels expansion without re-running embeddings.
- **Rubric + gold lock is unbroken.** Deferral is a schedule change, not a rubric change. No post-hoc edits triggered.
- **Alternatives considered:**
  - **Expand labeling to full 20 queries/block now.** Rejected: would consume 2-4 additional Perplexity-Max sessions with no time-sensitive driver. Better to fold into a batched future re-eval.
  - **Flip to 8B-Q6_K on the 32.04 vs 29.11 calibration margin.** Rejected: violates pre-registered N=20/block requirement, and would be a post-hoc reversal-criteria interpretation (explicitly prohibited by ADR-0016 + ADR-0022 lock).
  - **Flip to 0.6B-Q8 to save VRAM.** Rejected: 0.6B has an all-zero sub-cell (H1 docs). Even at N=4 the downsize predicate fails on the "no metric loses ≥15 points vs incumbent" clause.

## Consequences

- Production embedder unchanged (4B-Q8, `qwen3-embedding-4B-Q8_0.gguf`, llama.cpp GPU cold).
- ADR-0030 remains Proposed. If a future re-eval is initiated, it resumes from the locked calibration qrels + persisted step-6b pool; no re-embedding needed. Additional queries just expand the qrels file (append + re-lock SHA).
- ADR-0030b remains Proposed. Co-residency testing deferred to future post-verdict.
- No PORTING_LEDGER change (no port added/removed).
- No SESSION_HANDOFF blocker — DoD stop-condition met for calibration slice; full-slice DoD deferred.
- The offline scorer (`bench/scoring/embedder-full-multi-block-calibration/score_offline.py`) is now the durable path for step-6d scoring: rubric metrics computable from persisted step-6b output + any locked qrels file, no embedder re-launch.

## Lock-in phase

Phase 0.4 gate-4. Verdict-defer decision ratified on this file's commit.

## References

- `adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md` — fixture (still Proposed)
- `adrs/ADR-0030b-embedder-co-residency-viability.md` — co-residency methodology (still Proposed, deferred)
- `adrs/ADR-0016-medium-tier-scoring-rubric-hybrid.md` — post-hoc edit lock
- `adrs/ADR-0022-phase-0-2-coder-planner-medium-task-and-gold-protocol.md` — post-hoc reversal-criteria prohibition
- `bench/gold/embedder-full-multi-block/qrels.jsonl` — locked calibration set (SHA256 f7137c7bebbf9b10da14091488c185921f4cda2e071880c838eefff4aaca48f8)
- `bench/scoring/embedder-full-multi-block-calibration/scored_4query_calibration_20260811.md` — full results table
- `bench/scoring/embedder-full-multi-block-calibration/score_offline.py` — offline scorer
- `BUILD_LOG.md` — 2026-08-11 15:50 EDT (step 6b), 16:07 EDT (q-c01), 16:30 EDT (calibration expansion), 16:36 EDT (step 6d scoring)
