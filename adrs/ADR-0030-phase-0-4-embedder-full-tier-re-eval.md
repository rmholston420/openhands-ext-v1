# ADR-0030 — Phase 0.4 embedder Full-tier re-eval (three-way, pre-registered)

**Status:** Proposed (flips to Ratified on fixture lock-in: corpus manifest committed with pinned repo SHAs, 40 queries authored blind, rubric committed, qrels labeled by Perplexity-Max and hash-locked)

> **PROGRESS NOTE (2026-08-11 13:16 EDT):** Fixture lock-in step 3 (corpus manifest) COMPLETE. `bench/corpus/embedder-full-multi-block/MANIFEST.json` committed at pinned SHAs: openhands-ext-v1@5489fb19 (main), Kosmos@1f33519a on branch `stage-3-13-tektos-intention` (user's live working state, 45 commits ahead of Kosmos main; option S1 per user 2026-08-11 13:15 EDT), Rigpa-LMS@55b55539 (main). Totals: 969 code files (26 + 392 + 551), 139 docs files (42 + 97). Diagnostic correction filed in BUILD_LOG: earlier comparison output was misread — stage-3-13 is AHEAD of main by 45, not behind. Steps 4–6 remain before Ratification.

> **PROGRESS NOTE (2026-08-11 13:19 EDT):** Fixture lock-in step 4 (40 queries authored blind under B2 schema view + D1 20/20 split + QA2 cadence) COMPLETE. `bench/tasks/embedder-full-multi-block.queries.json` at 043ffc9. Full 66-candidate pool retained for post-hoc audit; culling was on coverage, not difficulty. Steps 5–6 remain.

> **PROGRESS NOTE (2026-08-11 13:23 EDT):** Fixture lock-in step 5 (rubric R2+G2) COMPLETE. `bench/rubrics/full-embedder-scored.json` at 59c4c9b. Composite weights sum-verified to 1.0; V3+W3 reversal predicates encoded as evaluable clauses; labeler instructions embedded verbatim; downsize has stricter single-metric loss guard (no composite-offset). `post_hoc_edit_locked=true`. Step 6 remains.

> **SCOPE-REDUCTION AMENDMENT (2026-08-11 14:00 EDT):** During step 6b execution on Colossus, the CPU-only embedder throughput (~10 tok/s prompt processing at Q8_0 on the 4B candidate) projected the full 12-cell run at ~50+ hours per candidate — not viable in-session. Per user selection (option S1), the matrix is reduced from `3 × 2 × 2 = 12 cells` to `3 × 2 × 1 = 6 cells` by **dropping the `code` block** and running only the `docs` block. Rationale:
> - The chunker axis (H1 vs H2 structure-aware) is the primary hypothesis test in this phase and is preserved.
> - The candidate axis (0.6B / 4B / 8B) is preserved.
> - The block axis (code vs docs) is dropped; docs-only is a smaller but honest reversal test given the CPU envelope.
> - The reversal criteria (§Reversal Criteria) are unchanged in their thresholds, but their scope is now labeled as `docs_block_only_composite`. Any 8B-flip or 0.6B-downsize verdict filed under this reduced scope must be flagged in ADR-0031 as "reversal test scope: docs-only" and cannot be interpreted as a code-corpus finding.
> - The 40-query set is unchanged; only the 20 docs queries are used. The 20 code queries remain in the queries file for a future re-run under a different compute envelope.
> - Pool size drops from `up to 20 × 40 × 12 = 9600` to `up to 20 × 20 × 6 = 2400` unique (query, chunk) pairs before dedup — well within a single Perplexity-Max labeling session's 150-300 label budget for the pruned-to-answered-queries subset.
>
> This is a scope-reduction amendment, not a decision-content change. Rubric weights, composite formula, chunk_id primary key, and reversal thresholds are unchanged. Post-hoc-edit-locked artifacts (queries file, rubric file, MANIFEST.json) are unchanged. If a future re-run under GPU or a longer CPU wall-clock envelope produces code-block results, they will be filed as a separate follow-up ADR under a new gate, not folded into ADR-0031.

> **DoD ORDERING AMENDMENT (2026-08-11 13:26 EDT):** The originally listed DoD ordering has steps 6 (qrels labeling) before 7 (runner extension) and 8 (running the 12 cells). This ordering is unexecutable — Perplexity-Max labeling requires the pooled union of top-20 chunks across all 12 cells, which cannot exist until the runner has been extended AND executed once in *pool-only* mode. The amended DoD ordering is:
>
> - **6a. Runner extension** — add `probe_embedder_full_multi_block()` to `bench/runner/probes.py` as a peer to existing probes (P1 per user 2026-08-11 13:26 EDT; no refactor of `probe_embedder_full()` inside this gate to preserve Phase 0.3 provenance boundary).
> - **6b. Pool-only runner execution** — run all 12 cells with retrieval-only mode; write pooled union of top-20 per query to `bench/gold/embedder-full-multi-block/pool.jsonl`. This IS execution of the 12 cells, but scoring is deferred until qrels are labeled.
> - **6c. Qrels labeling via Perplexity-Max (GL2 2–4 sessions)** — labelers grade the pool per the rubric's embedded instructions; unanswerable queries flagged. Locked file: `bench/gold/embedder-full-multi-block/qrels.jsonl` + `QRELS.locked.sha256`.
> - **6d. Scoring pass** — runner reads locked qrels, computes composite per cell, evaluates reversal criteria, emits verdict artifact. This is a re-run of scoring only, not retrieval — retrieval outputs from 6b are cached and reused (deterministic embeddings + fixed corpus + fixed queries).
> - **7. ADR-0031 verdict filed** — CONFIRM incumbent, or FLIP to 8B, or FLIP to 0.6B, or INTERMEDIATE (per-block split).
>
> Rationale for the reorder: labeling ordering was originally written assuming the runner would produce the pool as a side effect of scoring, without recognizing that scoring depends on the very qrels labeling is meant to produce. The 6a→6b→6c→6d→7 order eliminates this cycle. ADR-0030 remains Proposed; Ratification still coincides with the ADR-0031 verdict filing (step 7). No decision-level content of this ADR (rubric, candidates, primary key, reversal criteria) is changed by this amendment — only the ordering of the DoD steps that implement it.

**Lock-in phase:** Phase 0.4 gate-4 opener
**Supersedes:** —
**Extends:** ADR-0016 (medium-tier hybrid rubric), ADR-0017 (embedder production placement, amend #3: 4B-Q8 llama.cpp CPU), ADR-0022 (gold protocol), ADR-0028 (Full-tier ADR-opener template)
**Related:** ADR-0025 (planner CONFIRM 27B-Q6_K on llama.cpp GPU), ADR-0029 (coder CONFIRM AWQ on vLLM GPU) — these fix the VRAM budget that mandates the embedder CPU co-residency contract

## Context

Phase 0.3 closed with a stable coder + planner pair on the 32 GB VRAM budget:

- Coder: `qwen3-coder-30b-a3b-instruct-awq-4bit` on vLLM GPU (ADR-0029, gate-3)
- Planner: `qwen3_6-27b-q6k-gguf` on llama.cpp GPU (ADR-0025, gate-1)

The embedder, per ADR-0017 amendment #3, was placed on **llama.cpp CPU** specifically to preserve VRAM for those two GPU processes. That placement is a production-fidelity constraint, not a research convenience — moving the embedder to GPU would evict the coder or planner in Phase 1 runtime co-residency.

The current embedder (`qwen3-embedding-4B-Q8_0`, llama.cpp CPU) was selected at Medium-tier (Phase 0.2) with an inline ~40-chunk hand-authored task-set that:

1. **Does not stress-test scale** — real retrieval workloads span thousands of chunks, not forty
2. **Does not test chunking strategy** — the Medium set was per-doc-inline, so chunker-sensitivity is unmeasured
3. **Does not test multi-block generality** — Medium had one corpus flavor per arm; Phase 1 will index both code and governance docs together
4. **Was authored before the Full-tier score-band rubric was ratified** (ADR-0026, ADR-0028)

Phase 0.4 opens a **Full-tier three-way** re-eval to close all four gaps in a single pre-registered gate.

## Decision

Open Phase 0.4 gate-4 as a **three-way embedder Full-tier re-eval** with the pre-registered plan below. Filing status is **Proposed** at this commit; on fixture lock-in (corpus + queries + rubric + gold qrels committed and hashed), ADR-0030 flips to **Ratified** and `bench/tasks/embedder-full-multi-block.json` + rubric + qrels become `post_hoc_edit_locked=true`.

### Sub-decision 1 — Candidate pool (three-way)

**File:** `bench/candidates/embedder-full-pool.json` (committed this commit).

| Cell ID | Model | Runtime | Device | Weight (GiB) | Role designation |
|---|---|---|---|---:|---|
| `e04b_q8_cpu` | `qwen3-embedding-4B-Q8_0.gguf` | llama.cpp | CPU | 3.99 | **incumbent** |
| `e08b_q6k_cpu` | `qwen3-embedding-8B-Q6_K.gguf` | llama.cpp | CPU | 5.79 | challenger_upsize |
| `e006b_q8_cpu` | `qwen3-embedding-0.6B-Q8_0.gguf` | llama.cpp | CPU | 0.60 | challenger_downsize |

**All three on llama.cpp CPU** per the co-residency contract inherited from ADR-0017 amend #3. GPU sub-cells rejected (see Alternatives §1).

**8B-Q6_K verified** at `Qwen/Qwen3-Embedding-8B-GGUF/Qwen3-Embedding-8B-Q6_K.gguf` (5.79 GiB) via HF API 2026-08-11 13:04 EDT before locking. Q6_K chosen over Q8_0 (7.49 GiB) on quality-parity grounds; Q8_0 is a fallback if Q6_K exhibits pathological loss (unlikely for embedder weights).

### Sub-decision 2 — Task-set shape

**File:** `bench/tasks/embedder-full-multi-block.json` (committed this commit; queries deferred to fixture lock-in).

**Shape (original):** 3 candidates × 2 chunkers × 2 blocks = **12 cells**. Each cell runs 20 queries and returns top-20 chunks per query.

**Shape (SCOPE-REDUCED 2026-08-11 14:00 EDT):** 3 candidates × 2 chunkers × 1 block (docs) = **6 cells**. 20 docs queries × 20 top-k per cell. See SCOPE-REDUCTION AMENDMENT at top.

**Two retrieval blocks:**

- **code block** (`CC3`): corpus = `openhands-ext-v1` + `Kosmos` + `Rigpa-LMS` (Python source only; excludes `.venv/`, `node_modules/`, `__pycache__/`, `.pplx/`, minified assets). Expected 800–2500 source files.
- **docs block** (`DD2`): corpus = `openhands-ext-v1` governance (ADRs + BUILD_LOG + DEBUG_LOG + KNOWN_ISSUES + docs) + `Kosmos` governance (same + `Kosmos-Build-Spec-v25.md`, `Kosmos-Build-Sequence-v25.md`, `PORTING_LEDGER.md`). Expected 80–300 source files.

**Two chunking strategies** (both applied to both blocks):

- **H1** — fixed 512-token chunks with 64-token overlap, `cl100k_base` tokenizer
- **H2** — structure-aware: code = per-symbol (function/class/method-level via `ast.parse`); docs = per-heading (## and ### as boundaries). Falls back to H1 for symbols/sections >1024 tokens or where `ast.parse` fails.

### Sub-decision 3 — Rubric

**File:** `bench/rubrics/full-embedder-scored.json` (created at fixture lock-in; **not** in this commit).

**Metrics** (all four computed per cell over 20 queries):

| Metric | Weight in composite | Computed over |
|---|---:|---|
| nDCG@10 | 0.40 | graded relevance 0-3 |
| Recall@10 | 0.25 | relevance ≥ 2 |
| MRR@10 | 0.20 | primary-flagged only |
| Recall@1 | 0.15 | primary-flagged only |

**Composite** = 100 × (0.40·nDCG10 + 0.25·Recall10 + 0.20·MRR10 + 0.15·Recall1). Range 0–100.

**Cell macro** = mean composite across 20 queries within cell.
**(candidate, block) macro** = mean across the 2 chunker sub-cells.
**candidate overall macro** = mean across all 4 (chunker × block) sub-cells.

### Sub-decision 4 — Gold labeling protocol (G1 pooled)

- **Scorer:** Perplexity-Max (Claude Sonnet 4.6 via Perplexity Computer).
- **Pooling:** union of top-20 chunks across all 12 cells per query, deduplicated at `(repo, source_file_path, line_range)` key.
- **Grading:** 0 (irrelevant), 1 (marginal), 2 (relevant), 3 (exact).
- **Primary/secondary flag:** exactly one primary per query (the most-canonical `(file, line_range)` answering the query); zero-to-unbounded secondaries.
- **Primary key rule (P1, chunker-agnostic):** primary is at `(repo, source_file_path, line_range)` tuple. A retrieved chunk counts as MRR@1 hit if `chunk.line_span ∩ gold.line_range ≠ ∅`. Same qrel file for both H1 and H2 sub-cells within a block.
- **Locking:** qrels file hash committed to `bench/gold/embedder-full-multi-block/QRELS.locked.sha256` **before** first embedder inference on any candidate. Post-hoc relabeling prohibited.

Expected label budget: 40 queries × 15–60 unique candidates per pool = 600–2400 labels.

### Sub-decision 5 — Reversal criteria (pre-registered, V3+W3)

Locked in `bench/tasks/embedder-full-multi-block.json` `reversal_criteria` block. Verbatim mechanical rules:

**`confirm_incumbent_4b_q8_if`** (any one holds → CONFIRM 4B):
1. 4B overall macro ≥ (max challenger overall macro) − 3.0 (tiebreak band; incumbent retained on tie)
2. On the code block, no challenger passes the W3 strict gate
3. On the docs block, no challenger passes the W3 strict gate

**`flip_to_8b_q6k_if`** (all five must hold → FLIP to 8B):
1. 8B code block-macro ≥ 4B code block-macro + 3.0 (W1)
2. 8B docs block-macro ≥ 4B docs block-macro + 3.0 (W1)
3. On both blocks: no per-metric regression from 4B > 5.0 (W2)
4. On both blocks: no per-metric loss from 4B > 2.0 on any of {nDCG@10, Recall@10, MRR@10, Recall@1} (W3)
5. RAM peak of 8B-Q6_K ≤ 12 GiB (co-residency safety)

**`flip_to_0_6b_q8_if`** (all five must hold → FLIP to 0.6B):
1. 0.6B code block-macro ≥ 4B code block-macro + 3.0 (W1)
2. 0.6B docs block-macro ≥ 4B docs block-macro + 3.0 (W1)
3. On both blocks: no per-metric regression from 4B > 5.0 (W2)
4. On both blocks: no per-metric loss from 4B > 2.0 on any of {nDCG@10, Recall@10, MRR@10, Recall@1} (W3)
5. 0.6B frees ≥ 3.0 GiB RAM AND wall-time speedup ≥ 2× vs 4B (headroom/speed justification for downsize)

**INTERMEDIATE** (per-block split possible): confirm conditions fail on both blocks AND no challenger passes W3 on both blocks. A per-block split (e.g. 8B docs, 4B code) requires its own follow-up ADR — this ADR does not authorize a split flip on its own.

**Tiebreak:** wall-time median per query, applied ONLY within a 3-point composite band on the winning block(s). Speed cannot flip against incumbent (incumbent wins ties).

Boundary values default to preserving incumbent. Post-hoc reinterpretation prohibited (project instruction).

### Sub-decision 6 — Co-residency contract (harness enforcement)

Locked in `bench/tasks/embedder-full-multi-block.json` `co_residency_contract` block:

- All 3 candidates run llama.cpp CPU (`-ngl 0`).
- RAM peak per cell ≤ ~8 GiB (well within 128 GiB Colossus).
- **Runner MUST stop coder vLLM and planner llama.cpp GPU processes before each embedder cell** — not for VRAM (embedder is CPU-only) but to prevent CPU-core contention that would skew wall-time reporting.

### Sub-decision 7 — Harness contract

- Endpoint: OpenAI-compatible `/v1/embeddings` on llama.cpp.
- Batch size ≤ 16; deterministic seed 42.
- Index: **flat cosine similarity** (exact search, no ANN/FAISS at Full-tier — Full-tier measures embedder quality, not index topology).
- Top-k returned: 20.
- Runner enhancement required: `bench/runner/probes.py::probe_embedder_full_multi_block` (analog of `probe_coder`). Runner work is **not** in this commit and will land under a separate BUILD_LOG entry before gate-4 step 7.

## Rationale

- **Three-way** (not pairwise) because the incumbent placement is a compromise (CPU, moderate-quality); both an upsize and a downsize challenger are meaningful. A three-way with V3+W3 gates protects incumbent unless a challenger wins decisively on both blocks.
- **Two blocks** because Phase 1 will index both code and docs into the same embedder. A single-block gate could pick a winner that regresses catastrophically on the other block.
- **Two chunkers** because chunker-sensitivity is a genuine tuning knob at deploy time. Measuring it separately from embedder-quality lets the verdict ADR recommend both an embedder and a chunker.
- **20 queries per block** (not 10) because 40 total gives ≥2× the sample size of Medium and shrinks per-metric variance well below the 2.0-point W3 threshold.
- **P1 primary key rule** (line-range, chunker-agnostic) because using per-chunker primaries would require labeling twice and would blur chunker vs embedder attribution.
- **V3 + W3** because a challenger that wins overall macro by 3 but regresses catastrophically on one block or one metric would degrade production. W3 is strict but not paranoid: 2.0-point per-metric loss tolerance covers noise; 5.0-point is a hard regression bound.

## Consequences

- Corpus snapshot: three-repo pin (openhands-ext-v1 + Kosmos + Rigpa-LMS) plus two governance-doc pins requires a `bench/corpus/embedder-full-multi-block/MANIFEST.json` with SHA per repo. Manifest is fixture-lock-in step 3.
- Query authoring: 40 queries authored blind (no index-peeking) is fixture-lock-in step 4.
- Rubric commit: `bench/rubrics/full-embedder-scored.json` created at fixture-lock-in step 5.
- Gold labeling: Perplexity-Max labels ~600–2400 pooled (query, chunk) pairs at fixture-lock-in step 6. This is a materially larger labeling task than gate-3's 400-judgment coder gold. Session budget: 2–4 sessions.
- Runner extension: `probe_embedder_full_multi_block` in `bench/runner/probes.py` before step 7.
- Verdict ADR reservation: ADR-0031 reserved for the gate-4 verdict.
- 35b coder candidate retirement: **deferred to Phase 1** per user directive 2026-08-11 12:56 EDT; not addressed in this ADR.

## Alternatives considered

1. **GPU sub-cells (D2 or D3)** — Rejected. Coder vLLM + planner llama.cpp GPU together fill the 32 GB VRAM budget in production. Running embedder on GPU during eval would require evicting one of them, which changes measured wall-time and RAM in ways that do not reflect Phase 1 production co-residency. Any future GPU embedder placement is a separate ADR that would need to re-open the coder/planner co-residency budget first.
2. **Pairwise (incumbent vs single challenger)** — Rejected. The incumbent's placement is a compromise; both upsize and downsize deserve a shot in one gate rather than serial pairwise gates.
3. **10 queries per block (F1)** — Rejected. Full-tier composite variance on 10 queries is high enough that a 3-point block-macro delta could be noise; 20 queries roughly halves stderr.
4. **Per-chunker primaries (P2)** — Rejected. Labeling twice for a knob we want to isolate would blur attribution.
5. **Binary relevance (R1)** — Rejected. nDCG on binary is degenerate; graded 0-3 with primary flag is standard TREC-style.
6. **Skip 8B (Q4)** — Rejected. HF verification confirms `Qwen3-Embedding-8B-Q6_K.gguf` exists at 5.79 GiB (well within RAM budget); no reason to punt the challenger.
7. **W1 or W2 (weaker gates)** — Rejected. W1 (composite +3 per block) does not protect against per-metric regressions; W2 caps regression at 5 points but permits 5-point losses on individual metrics; W3 additionally caps single-metric losses at 2.0. W3 is the appropriate strictness level for a production embedder that will index all Phase 1 memory writes.

## Lock-in phase

Phase 0.4 gate-4 opens with this ADR (Proposed). Ratification requires fixture lock-in steps 3–6 in the Definition of Done. Verdict ADR-0031 reserved.

## References

- `bench/tasks/embedder-full-multi-block.json` — task-set + reversal criteria (committed this commit)
- `bench/candidates/embedder-full-pool.json` — three-way pool (committed this commit)
- `bench/rubrics/full-embedder-scored.json` — rubric (TBD at fixture lock-in)
- `bench/gold/embedder-full-multi-block/qrels.jsonl` — gold labels (TBD at fixture lock-in)
- `bench/corpus/embedder-full-multi-block/MANIFEST.json` — corpus snapshot manifest (TBD at fixture lock-in)
- `adrs/ADR-0016-medium-tier-scoring-rubric-hybrid.md` — hybrid rubric precedent
- `adrs/ADR-0017-production-role-selection-pre-medium.md` amend #3 — 4B-Q8 CPU placement
- `adrs/ADR-0028-phase-0-3-gate-3-coder-full-tier-re-eval.md` — Full-tier ADR-opener template
- `adrs/ADR-0029-phase-0-3-gate-3-coder-verdict-confirm-awq.md` — coder role locked
- `adrs/ADR-0025-planner-migration-probe-verdict-confirm-adr-0023.md` — planner role locked
- `BUILD_LOG.md` 2026-08-11 13:08 EDT entry
