# ADR-0022 — Phase 0.2 coder + planner Medium-tier task-set, gold-reference, and co-residency protocol

**Status:** Ratified (2026-08-11 08:57 EDT)
**Lock-in phase:** Phase 0.2 (Medium tier) — coder + planner
**Supersedes:** — (extends ADR-0016 which specified rubric shape but deferred task-set + gold-authoring specifics)

## Context

Phase 0.2 (Medium tier) is the first tier that produces **scored** cell rankings. Embedder-Medium already ran (verdict `bench/results/verdicts/medium-verdict-embedder-20260811T100541Z.json`) because embedder scoring is programmatic (recall@k/MRR/nDCG@10 per ADR-0016) and required no gold authorship.

Coder-Medium and planner-Medium remain blocked. ADR-0016 fixed the rubric shape ("Shape A: Perplexity-Max gold, 0-100 scoring") but left four downstream surfaces unspecified:

1. Coder-medium task shape and count
2. Planner-medium task shape and count
3. Perplexity-Max gold-reference generation protocol
4. VRAM co-residency + cell-swap protocol during scored runs

Each of these can be decided independently, but they are tightly coupled: the task shape determines the gold-reference protocol, which determines run-time, which determines the co-residency strategy. Filing four separate ADRs inflates the audit trail without improving review. This ADR resolves all four as one decision unit.

Pool state at time of authoring:
- **Coder-medium pool:** 4 cells (`bench/candidates/coder-medium-pool.json`, ADR-0014-locked, no eliminations Fast→Medium)
- **Planner-medium pool:** 2 cells (`bench/candidates/planner-medium-pool.json`, ADR-0015-locked, thinker-2507-awq eliminated)
- **Embedder-medium:** DONE, verdict locked, 4B bf16 vLLM/gpu winner at nDCG@10 = 0.5505

## Decision

**Decision 1 — Coder-medium task set: extended synthetic, 10 tasks.**

- Author `bench/tasks/coder-medium.json` as 10 tool-call tasks against a mocked OpenHands tool surface (`str_replace_editor`, `execute_bash`, `read_file`, `write_file`, and any additional tools required for the specific tasks).
- Task shape: task-id + prompt + expected tool-call transcript (from Perplexity-Max gold) + expected file-content-after-diff.
- Gold references live at `bench/gold/coder-medium/<task-id>.md`, hashed in the task-set JSON.
- SHA-256 hashes over gold-reference files stored in `bench/tasks/coder-medium.json#/gold_hashes` at task-set-freeze time.

**Decision 2 — Planner-medium task set: 10 multi-step plan tasks.**

- Author `bench/tasks/planner-medium.json` as 10 structural-JSON plan-generation tasks (agent-work breakdown, dependency ordering, risk analysis).
- Task shape: task-id + prompt + expected plan schema.
- Gold references live at `bench/gold/planner-medium/<task-id>.md`, hashed in the task-set JSON at freeze time.
- Structural-JSON conformance is a hard-pass gate before quality scoring (matches Fast-tier planner survivor gate).

**Decision 3 — Perplexity-Max gold generation: single-pass, hash-frozen.**

- Each gold reference is a single Perplexity-Max pass, authored once, saved to disk, hashed, and frozen. No re-generation.
- Rubric `bench/rubrics/medium-scored.json` `post_hoc_edit_policy.allowed=False` already enforces freeze after first scored run; this ADR extends that discipline to gold-reference files.
- If a gold is later found wrong, the correct remedy is a task-set version bump (v2 filename) authored by a superseding ADR — never in-place gold edit.
- Matches `local-llm-bench` skill's canonical protocol and the saved user preference "Perplexity Max as gold-standard baseline."

**Decision 4 — VRAM co-residency: sequential role blocks.**

- Run order: **all coder cells → single large-model teardown → all planner cells**. One coder-cell block, one planner-cell block, one swap between.
- Embedder is CPU-resident throughout (per ADR-0017 amendment #3) — no VRAM contention.
- Within each block, cell order is fixed to the pool JSON `cells[]` order (no randomization, no interleave).
- Swap uses `scripts/stop-large-model.sh` + `scripts/serve-coder.sh` / `scripts/serve-planner.sh` (already committed).
- One-shot swap keeps total Medium runtime at ~2.5 hr instead of ~4.5 hr for per-task interleave, without adding cell-order confounds that exceed rubric resolution (3-point quality threshold from ADR-0016 tiebreak).

## Rationale

**Decision 1 rationale (synthetic vs. SWE-bench-Lite vs. real repro):**

- **Why not SWE-bench-Lite:** Phase 0.3 already runs SWE-bench-Verified. Duplicating that surface at Medium wastes gold-authorship budget and pushes Medium runtime toward Full-tier territory (~6-8 hr instead of ~2.5 hr).
- **Why not real OpenHands repro:** Not reproducible without a frozen repo snapshot; violates the "task set frozen pre-run" principle from ADR-0016.
- **Why 10 tasks:** Enough for meaningful nDCG-analog quality differentiation across 4 cells (40 gold comparisons); few enough to author gold references in one sitting; runtime ~2 hr per Medium run at ~3 min/task average.
- **Why synthetic:** Medium tier's purpose per ADR-0016 is discriminating shortlist among Fast-tier survivors, not final ranking. Synthetic gives more discriminating signal per unit runtime; final ranking happens at Phase 0.3.

**Decision 2 rationale (plan-generation vs. extended-fast-set vs. real-planning-traces):**

- **Why not extended-fast-set:** Fast tier already eliminated on structural-JSON conformance. Extending it with more of the same signal is redundant.
- **Why not real-planning-traces:** Same non-reproducibility problem as coder Option B.
- **Why 10 tasks:** 2-cell pool × 10 tasks = 20 gold comparisons. Small pool means gold authorship burden is small (10 gold plans total). ~10 tasks × 2 cells × 60s per task ≈ 20-30 min per Medium planner run.

**Decision 3 rationale (single-pass vs. 3-sample consensus vs. user-reviewed):**

- **Why not 3-sample consensus:** 3× Perplexity-Max scoring budget without proportionally increasing discriminating power at Medium tier. Multi-sample adds value at Full tier (Phase 0.3) where 3+ repeats are already the standard per spec §0.3.
- **Why not user-reviewed:** Adds an out-of-band block on user review time; freeze policy + version-bump-via-ADR already provides audit trail for gold-quality issues.
- **Why hash-freeze:** `local-llm-bench` skill's canonical protocol explicitly specifies "gold answer saved to disk" and freeze. Hash extends this to detect accidental in-place edits.

**Decision 4 rationale (sequential blocks vs. per-task interleave vs. randomized within blocks):**

- **Why not per-task interleave:** ~40 swaps × ~2-3 min per swap = ~2 hr of pure overhead. Buys precision below the 3-point quality-tiebreak threshold from ADR-0016.
- **Why not randomized-within-blocks:** Adds randomization-state bookkeeping (RNG seed capture) for no discriminating benefit at Medium tier. Thermal drift within a block is dominated by cell-level GPU warmup which affects the first cell of each block regardless of order.
- **Why sequential:** Matches ADR-0017 Option 2 co-residency policy verbatim. Also minimizes total wall time, keeping Medium runtime executable in one session.

## Alternatives considered

- **Alt 1 — Author 4 separate ADRs (0022 through 0025).** Rejected: the four surfaces are tightly coupled and reviewed together. Four ADRs adds four filings to the audit trail without adding review value, and creates the risk of two of them getting out of sync during amendments.
- **Alt 2 — Use SWE-bench-Lite for coder-medium (Option C from menu).** Rejected: as above, duplicates Phase 0.3 work.
- **Alt 3 — 3-sample gold consensus (Option B from menu).** Rejected: Medium tier's discriminating purpose does not benefit from the added scoring budget.
- **Alt 4 — Per-task cell interleave (Option B from menu).** Rejected: overhead exceeds rubric resolution.
- **Alt 5 — Defer coder-medium + planner-medium and skip straight to Phase 0.3.** Rejected: spec §0.2 explicitly requires scored Medium-tier shortlisting before Full tier. Phase 0.4 escalation rule allows skipping Medium only when Fast produced an unambiguous large-margin winner — neither coder nor planner Fast-tier produced that (coder-fast pool has 4 admitted cells, planner-fast pool has 2). Skip is not applicable.

## Consequences

### Files / infrastructure to author this session

1. **`bench/tasks/coder-medium.json`** — 10 tool-call tasks + expected transcripts + gold-hash table.
2. **`bench/tasks/planner-medium.json`** — 10 plan-generation tasks + expected schema + gold-hash table.
3. **`bench/gold/coder-medium/<task-id>.md`** × 10 — Perplexity-Max gold tool-call transcripts + expected diffs.
4. **`bench/gold/planner-medium/<task-id>.md`** × 10 — Perplexity-Max gold plans.
5. **`bench/gold/README.md`** — freeze-policy note referencing this ADR and ADR-0016.

### Runtime state

- Total Medium runtime estimate: coder block ~2 hr + swap ~3 min + planner block ~25 min = **~2.5 hr per full Medium coder+planner run.**
- Sandbox reaper (already committed at `03a1279`) handles container cleanup across the swap.
- FlashInfer sampler stays disabled per prior workaround (env `VLLM_USE_FLASHINFER_SAMPLER=0`).

### ADR / spec / logs

- Rubric `bench/rubrics/medium-scored.json` — no edit required; this ADR references its already-frozen `post_hoc_edit_policy` and extends it to gold references.
- ADR index `adrs/README.md` — new row for ADR-0022.
- `BUILD_LOG.md` — entry appended.

### Not affected

- ADR-0016 (rubric shape) — untouched; this ADR extends it, not amends it.
- Embedder-medium verdict — locked, unaffected.
- ADR-0017 role-selection amendments — unaffected; this ADR reuses the existing swap scripts.

## Lock-in phase

Phase 0.2 (Medium tier). This ADR locks in the coder+planner Medium-tier protocol going into task-set + gold authoring. Any change to the task-set shape, task count, gold protocol, or co-residency policy after this ADR is committed requires a superseding ADR.

## References

- `docs/specs/integration-execution-plan-v16.md` §0.2 (Medium tier definition)
- `adrs/ADR-0014-coder-fast-pool-reinstate-r2-warning-survivors.md` (coder-medium pool composition)
- `adrs/ADR-0015-planner-medium-thinker-budget-probe.md` (planner-medium pool composition)
- `adrs/ADR-0016-medium-tier-scoring-rubric-hybrid.md` (rubric shape; this ADR extends)
- `adrs/ADR-0017-production-role-selection-pre-medium.md` (co-residency Option 2 policy)
- `bench/candidates/coder-medium-pool.json` (4 cells)
- `bench/candidates/planner-medium-pool.json` (2 cells)
- `bench/rubrics/medium-scored.json` (frozen rubric)
- `local-llm-bench` skill (canonical Perplexity-gold protocol; saved user preference)
