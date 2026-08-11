# ADR-0016 — Medium-tier scoring rubric: hybrid (embedder programmatic; planner/coder Perplexity-gold)

**Status:** Ratified
**Lock-in phase:** Phase 0.2 (Medium tier) — must land before first Medium-tier scored task runs.
**Supersedes:** — (extends the "future ADR" placeholder in `bench/rubrics/fast-elimination.json#/scoring.reason`)

## Context

Phase 0.2 is the first tier that produces **scored** cell rankings, not just elimination. Fast tier (Phase 0.1, ADR-0007) is elimination-only: cells either pass hard rubric checks or are dropped. `bench/rubrics/fast-elimination.json#/scoring` explicitly sets `enabled=false` and points forward to a "future ADR before first Medium-tier scored output" — this ADR fills that slot.

Three roles reach Medium tier with different pool sizes and different natural scoring surfaces:

- **Embedder-Medium** — retrieval task surface (embed corpus, embed queries, score by top-k retrieval quality). Ground-truth relevance labels exist by construction (qrels file authored alongside the task set).
- **Planner-Medium** — 2 cells locked (llama.cpp 27B Q6_K/gpu, 35B Q4_K_XL/gpu; thinker-2507-awq excluded per ADR-0015). Output is JSON plan objects; quality is a judgment on decomposition, dependency ordering, edge-case handling.
- **Coder-Medium** — 4-cell candidate pool including thinker-2507-awq (dual-role per ADR-0012). Output is tool-call sequences and file edits; quality is a judgment on diff precision, test coverage, tool-selection appropriateness.

Two candidate scoring shapes:

- **Shape A (Perplexity-gold rubric):** Cells that pass elimination get a Perplexity-Max-generated reference answer per task. Cell outputs (post `<think>`-strip) are scored 0-100 against the reference by Perplexity Max. Canonical protocol from `local-llm-bench` skill.
- **Shape B (programmatic rubric only):** Cells that pass elimination are scored on deterministic checks — token efficiency, wall time, structural richness metrics, recall@k for retrieval. No LLM-as-judge.

## Decision

**Hybrid rubric, by role:**

- **Embedder-Medium: Shape B (programmatic only).** Score using retrieval metrics (**recall@k, MRR, nDCG@10**) against a labeled qrels file that is authored and frozen alongside the embedder-medium task set. LLM-as-judge is prohibited for embedder scoring.

- **Planner-Medium: Shape A (elimination + Perplexity-gold rubric, 0-100).** After elimination-rule survivors are identified, generate a Perplexity-Max reference plan per task, dump each cell's stripped output, score 0-100 against reference per the `local-llm-bench` canonical protocol.

- **Coder-Medium: Shape A (elimination + Perplexity-gold rubric, 0-100).** Same protocol; reference is a Perplexity-Max-generated tool-call transcript + expected diff. Cell outputs scored 0-100 against reference.

**Tiebreak (applies uniformly across all three roles):** quality-first ranking; if two cells score within **3 points** on quality (per the `local-llm-bench` canonical tiebreak), faster wins on wall-time median across the task set.

**Rubric file format:** `bench/rubrics/medium-scored.json` — one file for the whole tier, authored at the same commit as this ADR, `post_hoc_edit_policy.allowed=false` per §0.0a bullet 3.

## Rationale

**Why Shape B for embedder:**
- Retrieval quality is a **solved measurement problem** — recall@k, MRR, and nDCG on a fixed qrels set are the industry-standard metrics (TREC, BEIR, MTEB). They are deterministic, reproducible offline, and produce a total ordering with meaningful margins.
- LLM-as-judge on embeddings adds latency, cost, and stochasticity while giving *no signal* that recall@k plus MRR does not already give. Perplexity Max reading "here are 10 retrieved chunks, rank them" is worse than the labeled qrels it would be reading against.
- Gold-standard scoring on embedders violates the `local-llm-bench` skill's own principle 1 ("quality first, speed second") because the "quality" signal is worse than the programmatic alternative.

**Why Shape A for planner and coder:**
- Both produce open-ended structured outputs where two schema-passing outputs can differ substantially in quality — a 4-step plan that handles the edge case is worth more than a 4-step plan that does not; a diff with test coverage is worth more than an equivalent diff without.
- Programmatic-only rubrics collapse these into countable metrics (step count, diff hunk count, test-touch count) that measure *effort proxies*, not correctness. The canonical `local-llm-bench` protocol exists precisely because judgment-heavy outputs need a judgment-capable scorer.
- Perplexity Max as gold-standard baseline is the user's saved preference (recorded in `local-llm-bench` skill) and produces defensible quality-vs-speed rankings that survive review.

**Why not Shape A for embedder + Shape B for planner/coder:**
- Wastes Perplexity-Max scoring budget on a role where deterministic ground truth exists.
- Deprives planner/coder — the two roles where judgment matters most — of the judgment-based signal they actually need.
- Splits the wrong way against the roles' evidence-shape.

**Why not full-programmatic hybrid (all three roles Shape B):**
- Cheaper and faster, but produces mechanical scores for planner/coder that cannot rank "correct-and-thorough" above "correct-and-minimal." The Fast tier already produces this signal; Medium tier's purpose is to *add* the judgment layer, not repeat elimination with more axes.

**Why not full-gold hybrid (all three roles Shape A):**
- Adds Perplexity-Max cost and latency to embedder scoring for no informational gain over recall@k+MRR+nDCG.
- Introduces judge-variance to a metric surface (retrieval) where the community has already solved the variance problem with labeled qrels.

## Consequences

**Files created at this ADR's commit:**
- `bench/rubrics/medium-scored.json` — canonical Medium-tier scoring rubric, authored + frozen simultaneously with this ADR, `post_hoc_edit_policy.allowed=false`.

**Files created at each per-role task-set authoring commit (later):**
- `bench/tasks/embedder-medium.json` — task set + inline qrels (or reference to `bench/tasks/embedder-medium-qrels.json` if size warrants split).
- `bench/tasks/planner-medium.json` — task set.
- `bench/tasks/coder-medium.json` — task set.
- `bench/gold/planner-medium/<task-id>.md` — Perplexity-Max reference plans, generated once per task set version and frozen.
- `bench/gold/coder-medium/<task-id>.md` — Perplexity-Max reference tool-call transcripts + expected diffs, generated once per task set version and frozen.

**Harness changes required (later, per-role):**
- Medium-tier harness gains a `--score` phase (post-elimination) that:
  - Embedder: runs recall@k / MRR / nDCG against qrels, writes numeric scores to result JSON.
  - Planner/Coder: dumps stripped outputs; the dump is scored **out-of-band** by Perplexity Max (per skill protocol: paste dump + gold, receive numeric scores per task); scores are then recorded via a `--record-scores <json>` invocation that appends to result JSON. Never allow a cell to score itself.

**Elimination phase unchanged:** Fast-tier-style hard checks continue to run before scoring. Cells that fail elimination never reach the scoring phase (no gold-standard budget spent on eliminated cells).

**Post-hoc edit prohibition** applies to `medium-scored.json`, all per-role task-set files, and all `bench/gold/**` reference files. Amendments require a superseding ADR.

**Downstream ADR triggers:**
- If Perplexity-Max scoring reveals a systematic quality bias against a runtime (e.g., all vLLM cells score higher than llama.cpp cells regardless of underlying model), file a bias-diagnosis ADR before ratifying tier verdicts.
- If any qrels file needs correction post-first-run, this ADR must be amended (post-hoc edit) or the run must be re-authored with a new qrels version and a new task-set file.

## Lock-in phase

Phase 0.2 (Medium tier). No Medium-tier scored task set may land before this ADR is committed and `bench/rubrics/medium-scored.json` exists at HEAD.

## References

- ADR-0007 — Fast-tier task authoring, sampling, elimination-rubric methodology
- ADR-0009 — Fast-tier planner uses guided decoding (may be revisited at Medium tier)
- ADR-0012 — Registry: 30B thinker is dual-role coder+planner
- ADR-0015 — thinker-2507-awq excluded from planner Medium pool (Confirmed)
- `bench/rubrics/fast-elimination.json#/scoring.reason` — explicit forward-reference filled by this ADR
- `local-llm-bench` skill — canonical Perplexity-gold scoring protocol; principle 1 (quality-first, speed-second); tiebreak (within 3 points → speed wins)
- Retrieval-metric references: TREC Deep Learning tracks, BEIR benchmark, MTEB benchmark — for embedder recall@k / MRR / nDCG conventions
