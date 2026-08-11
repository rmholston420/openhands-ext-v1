# ADR-0024 — Planner migration-ordering probe (Phase 0.3 pre-registered re-eval)

**Status:** Ratified
**Lock-in phase:** Phase 0.3 gate-1 (post-ADR-0023 planner re-eval)
**Supersedes:** — (extends ADR-0023 §5 pre-registration into a locked task-set)

## Context

ADR-0023 flipped the production planner from `qwen3_6-35b-a3b-q4kxl-gguf/llama-cpp/gpu` to `qwen3_6-27b-q6k-gguf/llama-cpp/gpu` on Medium-tier scoring evidence:

- 27b-q6k macro-average quality 91.0 vs 35b-a3b-q4kxl 86.7 — 4.3-point gap, outside the 3-point tiebreak band in `bench/rubrics/medium-scored.json`.
- 35b-a3b-q4kxl failed `planner-medium-02` (zero-downtime schema migration ordering) — deployed application code before executing the DB migration; rubric explicit 70-89 band cap for this failure class.

ADR-0023 §5 pre-registered a Phase 0.3 planner re-eval on a migration-ordering probe task-set (3–5 tasks) to determine whether the 35b-a3b-q4kxl task-02 failure is a **systematic** weakness (planner ordering per ADR-0023 confirmed) or a **one-off** (planner ordering reconsidered). This ADR fills in the four surfaces §5 left unspecified:

1. Probe task shape and count
2. Probe gold-reference authorship + hash-freeze protocol
3. Probe rubric alignment (reuse vs new)
4. Probe reversal criteria (what score outcome flips the planner ordering back)

Each surface is small and tightly coupled; one ADR resolves all four.

## Decision

**Decision 1 — Probe task set: four migration-ordering plan tasks.**

- Author `bench/tasks/planner-medium-migration-probe.json` as **four** structural-JSON plan-generation tasks (upper end of the 3–5 range ADR-0023 §5 pre-authorized), each targeting a distinct zero-downtime migration ordering pattern:
  1. **`planner-migration-probe-01-expand-backfill-contract`** — Three-phase expand-migrate-contract on a 50M-row `users` table (add nullable column, dual-write, backfill, then NOT NULL + CHECK). Tests: no ALTER TABLE ... NOT NULL on a large populated table; backfill after dual-write.
  2. **`planner-migration-probe-02-rename-via-expand-contract`** — Multi-replica column rename via expand-contract. Tests: no naive RENAME COLUMN; dual-write phase; COALESCE fallback reader; DROP COLUMN strictly last.
  3. **`planner-migration-probe-03-fk-with-cleanup`** — FK addition on a table with 4k orphan rows. Tests: orphan cleanup before ADD CONSTRAINT; app-guard before cleanup; ADD CONSTRAINT NOT VALID / VALIDATE split.
  4. **`planner-migration-probe-04-concurrent-index-rebuild`** — Partial index rebuild on a 1.2B-row Postgres table at 8k QPS. Tests: CREATE INDEX CONCURRENTLY; ANALYZE + planner-adoption verification; bake period before DROP INDEX CONCURRENTLY.
- Task-set schema matches `bench/tasks/planner-medium.json` exactly (same `output_schema`, same `chat_template_kwargs`, same `budget_tokens=4096`, same structural-JSON hard-pass gate before quality scoring).
- Four tasks (not three) gives one extra data point for tie resistance under the reversal criteria (§Decision 4) without blowing up gold-authoring budget.

**Decision 2 — Perplexity-Max gold generation: single-pass, hash-frozen, per-task rubric band criteria.**

- Author gold references at `bench/gold/planner-medium-migration-probe/<task-id>.md`. Each contains: task summary, reference plan (canonical zero-downtime plan), and a per-task 5-band scoring rubric (90-100, 70-89, 40-69, 10-39, 0-9).
- Per-task rubric bands explicitly encode the failure mode from `planner-medium-02` — the 70-89 band captures "correct set of steps, wrong ordering" so ordering failures are guaranteed to land in the demotion band rather than being tacitly forgiven.
- SHA-256 hashes over gold files are stored in the task-set JSON at freeze time. Matches the ADR-0022 Decision-3 hash-freeze discipline.
- No `bench/rubrics/medium-scored.json` change required: the global rubric already specifies planner shape (`perplexity_gold`, 0-100), gold source path convention, `self_scoring_prohibited=true`, and Perplexity-Max as scoring authority. Per-task band criteria are inside the gold files, not the global rubric.

**Decision 3 — Cells re-scored: exactly the two Phase 0.2 planner cells.**

- `qwen3_6-27b-q6k-gguf/llama-cpp/gpu` (current ADR-0023 planner)
- `qwen3_6-35b-a3b-q4kxl-gguf/llama-cpp/gpu` (ADR-0023 fallback; on trial for reinstatement)
- Both cells already pass Fast-tier and Medium-tier elimination checks; only the probe scores are new.
- Co-residency: sequential-block protocol from ADR-0022 Decision 4. All four probe tasks on cell 1, teardown, all four on cell 2. Coder must be stopped before either planner cell starts (co-residency Option 2).

**Decision 4 — Pre-registered reversal criteria.**

Locked in `bench/tasks/planner-medium-migration-probe.json#/reversal_criteria` **before** scoring. Post-hoc edit prohibited by `medium-scored.json#/post_hoc_edit_policy`.

- **Flip planner back to 35b-a3b-q4kxl** if:
  - 35b-a3b-q4kxl scores ≥ 90 on all four probe tasks (quality parity established — task-02 was a one-off), OR
  - 27b-q6k macro-average trails 35b-a3b-q4kxl by more than 3 points on the probe (quality-first rule now favors 35b).
- **Confirm ADR-0023 planner ordering (27b-q6k retained)** if:
  - 35b-a3b-q4kxl scores < 70 on any probe task (systematic migration-ordering weakness), OR
  - 27b-q6k macro-average leads by ≥ 3 points (quality-first rule confirms current ordering).
- **Intermediate outcome** (35b scores 70-89 on one or more tasks but ≥ 90 on the rest): confirm ADR-0023 planner ordering; log per-task band mix as evidence for a possible Phase 1 re-visit under a broader task-set.
- Scoring authority: **Perplexity Max** (`self_scoring_prohibited=true`; local cells produce plans, they do not score their own or each other's plans).
- Any flip decision is filed as a superseding ADR (ADR-0025 or later) that supersedes ADR-0023's planner row; ADR-0017 is not touched again.

## Rationale

**Decision 1 rationale (4 tasks vs 3 vs 5):**

- **Why not 3:** Reversal criteria include an "all four ≥ 90" condition. Three tasks gives too few data points to distinguish "systematically strong" from "lucky on one easy task". Four tasks × two cells = 8 gold comparisons — enough discriminating power for a Phase 0.3 gate-1 decision.
- **Why not 5:** Gold authoring cost is roughly linear in task count. The fifth task would add a data point without changing any reversal-criterion outcome (the criteria all key on ≥ 1 failure or macro-average delta, both of which are already decisive at 4).
- **Why these four patterns:** Each targets a distinct migration-ordering discipline (three-phase expand-contract, multi-replica rename, referential integrity cleanup, hot-table index rebuild). If 35b-a3b-q4kxl fails all four, the weakness is systematic. If it passes all four, the task-02 failure was a specific-pattern gap not shared across the class. If it passes some and fails others, the per-task band mix diagnoses which subclasses it handles.

**Decision 2 rationale (per-task band criteria vs global rubric edit):**

- **Why not amend `medium-scored.json`:** The global rubric already specifies planner shape and scoring authority correctly. Editing it now would require a superseding ADR under the post-hoc-edit lock, add audit-trail cost, and force re-verification of unrelated planner-medium scoring. Per-task band criteria go in the gold files where they already live for `planner-medium-01..10`.
- **Why not embed the ordering rule as a global rubric clause:** Different migration patterns have different ordering failures. A general clause ("penalize wrong ordering") is too vague to score consistently; task-specific bands are the ADR-0022 pattern for a reason.

**Decision 3 rationale (2 cells vs re-open pool):**

- **Why not include the coder cells:** Coder cells are irrelevant to the planner re-eval. ADR-0023 already locked the coder role; adding coder cells here would inflate scope beyond the pre-registered §5 boundary.
- **Why not include a third planner cell (e.g. add a new candidate):** ADR-0023 §5 pre-registered a re-eval, not a pool expansion. New candidate cells require their own ADR (nominate, Fast-tier eliminate, Medium-tier score), not a smuggle-in via the probe.

**Decision 4 rationale (pre-registered reversal criteria vs post-hoc interpretation):**

- Pre-registration matches the medical-trial / clinical-outcomes discipline the rubric locks are already built around (`post_hoc_edit_locked`, `self_scoring_prohibited`). If the reversal criteria are set post-hoc — after scores are known — the probe reduces to confirmatory evidence for whatever ordering the author currently prefers, which is exactly the bias the ADR discipline is designed to prevent.
- The five-branch criteria structure covers every plausible outcome (both-strong, both-weak, one-strong-one-weak, near-tie, mixed-per-task) so no scoring outcome leaves the interpretation open.

## Consequences

Files created / changed under this ADR:

1. `adrs/ADR-0024-planner-migration-ordering-probe.md` (this file, new)
2. `adrs/README.md` (new index row for ADR-0024)
3. `bench/tasks/planner-medium-migration-probe.json` (new task-set with 4 tasks, gold_hashes, reversal_criteria)
4. `bench/gold/planner-medium-migration-probe/planner-migration-probe-01-expand-backfill-contract.md` (new gold)
5. `bench/gold/planner-medium-migration-probe/planner-migration-probe-02-rename-via-expand-contract.md` (new gold)
6. `bench/gold/planner-medium-migration-probe/planner-migration-probe-03-fk-with-cleanup.md` (new gold)
7. `bench/gold/planner-medium-migration-probe/planner-migration-probe-04-concurrent-index-rebuild.md` (new gold)
8. `BUILD_LOG.md` (append entry)

Not affected: `bench/rubrics/medium-scored.json` (no change; global rubric already covers planner shape and authority); ADR-0017; ADR-0023 (this ADR extends ADR-0023 §5, does not amend it); production-selection.json (planner assignment stays 27b-q6k unless the probe triggers a flip and a follow-up ADR files it).

## Alternatives considered

**Alt 1: Extend `bench/tasks/planner-medium.json` in place with four additional tasks.**
Rejected. `medium-scored.json#/post_hoc_edit_policy` explicitly prohibits post-hoc changes to `bench/tasks/planner-medium.json` after the first Medium-tier scored run without a superseding ADR. Adding four tasks in place would violate that policy; a new versioned task-set file is the ADR-0022-mandated pattern.

**Alt 2: Wait for a broader Phase 1 task-set (SWE-bench-Verified level) before revisiting planner.**
Rejected. ADR-0023 pre-registered a Phase 0.3 re-eval specifically because task-02 is a real production correctness concern that shouldn't wait months. The probe is cheap (~30 min per cell) and unblocks the planner decision now.

**Alt 3: Score by a third external LLM (Gemini, GPT-5) as a triangulation check on Perplexity-Max gold.**
Rejected as premature. `medium-scored.json` already specifies Perplexity Max as scoring authority and `self_scoring_prohibited=true`. Adding a second external scoring authority requires its own ADR and is a Phase 1 conversation, not a Phase 0.3 gate-1 conversation.

## Lock-in phase

Phase 0.3 gate-1. The probe task-set, gold references, hashes, and reversal criteria are all locked. Scoring runs on Colossus after user pulls; results are filed as a follow-up ADR (either confirming ADR-0023 or superseding its planner row).

## References

- ADR-0023 §5 (pre-registration of this probe)
- ADR-0022 (Phase 0.2 task-set + gold hash-freeze protocol; this ADR reuses the shape)
- ADR-0016 (Medium-tier scoring rubric — governs the shape this probe scores under)
- ADR-0017 amendment #4 (planner row status)
- `bench/rubrics/medium-scored.json` (post_hoc_edit_locked; unchanged)
- `bench/results/verdicts/medium-verdict-planner-20260811T134530Z.json` (the evidence that motivated this probe)
- `local-llm-bench` skill (canonical scoring protocol)
