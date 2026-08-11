# ADR-0023 — Phase 0.3 router-selection: post-Medium production role update

**Status:** Ratified
**Lock-in phase:** Phase 0.3 gate-1
**Supersedes:** — (amends ADR-0017 §Decision · planner row)

## Context

Phase 0.2 Medium-tier scoring is complete. Two verdicts locked on 2026-08-11:

- **Coder verdict** — `bench/results/verdicts/medium-verdict-coder-20260811T134530Z.json`
  - 3 cells scored under `capture_scope: single_turn_first_tool_call` (ceiling 85 applied).
  - Quality macro-avg: 35B-a3b-q4kxl **80.9**, coder-30B-instruct-awq **78.9**, 27B-q6k **76.4**.
  - Delta between rank-1 and rank-2 = 2.0 points — **within the 3-point tiebreak band** locked in `bench/rubrics/medium-scored.json`. Tiebreak activates → wall-time decides.
  - Wall-time (total 10 tasks): coder-30B-instruct-awq **3.3s**, 35B-a3b-q4kxl **6.2s**, 27B-q6k **16.6s**.

- **Planner verdict** — `bench/results/verdicts/medium-verdict-planner-20260811T134530Z.json`
  - 2 cells scored (full-plan capture; no ceiling).
  - Quality macro-avg: 27B-q6k **91.0**, 35B-a3b-q4kxl **86.7**.
  - Delta = 4.3 points — **outside the 3-point tiebreak band**. Rubric rule: quality-first wins outright; wall-time does not override.
  - 35B-a3b-q4kxl fails planner-medium-02 (zero-downtime DB migration ordering: deploys application code before executing DB migration) — rubric explicit 70-89 cap for this class of failure.

The current production selection is ADR-0017 (pre-Medium): coder = qwen3-coder-30B-instruct-awq/vllm, planner = **qwen3_6-35b-a3b-q4kxl-gguf/llama-cpp**. Post-Medium evidence changes the planner pick but confirms the coder pick.

Additional bench-harness observation captured in the coder verdict: the current harness records only the **first** tool call per task (single-turn). Coder scores evaluate tool selection + arguments + planning content in `assistant.content`, not final file state. Multi-turn correctness across edit + verify is unverifiable at present depth. This is an open item for a future harness upgrade, not a blocker on Phase 0.3.

## Decision

### 1. Coder role — **UNCHANGED from ADR-0017**

| Role | Model | Runtime | Device |
|---|---|---|---|
| **coder** | `qwen3-coder-30b-a3b-instruct-awq-4bit` | vLLM | GPU (port 8100) |

Rationale:
- Rank-1 (35B-a3b-q4kxl) and rank-2 (coder-30B-instruct-awq) are **within the 3-point tiebreak band** — rubric activates wall-time secondary sort. Coder-30B-instruct-awq wins the tiebreak (3.3s vs 6.2s, 47% faster).
- Coder-30B-instruct-awq is purpose-built for tool use (Qwen model-card guidance; ADR-0011 mandates the `qwen3_coder` tool-call parser for it) — the property most likely to matter beyond first-tool-call benchmarks.
- ADR-0017 wiring is done (systemd unit, port 8100, parser flags, health checks); no infrastructure churn.

### 2. Planner role — **CHANGED from ADR-0017**

| Role | Model | Runtime | Device |
|---|---|---|---|
| **planner** | `qwen3_6-27b-q6k-gguf` | llama.cpp | GPU |

Rationale:
- Quality gap of 4.3 points is **outside the 3-point tiebreak band** — rubric rule: quality-first wins outright. Wall-time (80.8s vs 16.6s total) does not override under the locked rubric.
- 35B-a3b-q4kxl fails a real correctness pattern on task 02 (deploys application code that references `deleted_at` column BEFORE executing the migration that adds the column). This is a production-hazardous plan output, not a stylistic difference.
- Planner is invoked once per episode (not once per tool call). Median wall-time 8.1s/task on 27B-q6k is acceptable for episode-scale planning.
- Both cells share the same runtime (llama.cpp/GPU) so infrastructure change is minimal (model file swap + serve-planner.sh update).

### 3. Embedder role — **UNCHANGED from ADR-0017 (amendment #3)**

| Role | Model | Runtime | Device |
|---|---|---|---|
| **embedder** | `qwen3-embedding-4b-q8-gguf` | llama.cpp | CPU (port 8090, ctx 4096, `-ngl 0`) |

Rationale: locked by embedder verdict (`bench/results/verdicts/medium-verdict-embedder-20260811T100541Z.json`, rank-1) and ADR-0017 amendment #3. No new data.

### 4. Pool cleanups for Phase 0.3

- **Drop** `qwen3_6-27b-q6k-gguf/llama-cpp/gpu` from the **coder** candidate pool. Dominated on both axes in Medium-tier coder scoring (quality 76.4 vs rank-1 80.9; wall 16.6s vs 3.3s). Retained in the **planner** pool (rank-1 there).
- **Retain** `qwen3-coder-30b-a3b-instruct-awq-4bit/vllm/gpu` and `qwen3_6-35b-a3b-q4kxl-gguf/llama-cpp/gpu` in the coder pool as fallback candidates pending Phase 0.3 multi-turn re-eval.
- **Retain** `qwen3_6-35b-a3b-q4kxl-gguf/llama-cpp/gpu` in the planner pool as the latency-sensitive fallback (86.7 quality is production-viable for tasks that don't touch DB migrations).

### 5. Phase 0.3 planner re-eval — migration-ordering probe

Add a pre-registered migration-ordering probe to the Phase 0.3 planner task set:
- 3–5 new tasks that require correct sequencing of schema migration vs application deploy.
- Purpose: verify whether the 35B-a3b-q4kxl task-02 failure is systematic (should stay demoted) or a one-off (may be reconsidered).
- Task authoring gated by the same locked-authoring discipline (ADR-0022).

## Consequences

Files that change under this ADR:

1. `bench/candidates/coder-medium-pool.json` — remove `qwen3_6-27b-q6k-gguf/llama-cpp/gpu` cell.
2. `bench/candidates/production-selection.json` — planner row updated to `qwen3_6-27b-q6k-gguf/llama-cpp/gpu` (from `qwen3_6-35b-a3b-q4kxl-gguf`); coder and embedder unchanged.
3. `scripts/serve-planner.sh` — model path updated to the 27B-q6k GGUF.
4. `scripts/check-production-endpoints.sh` — no change (endpoints unchanged, only model path).
5. `docs/specs/integration-execution-plan-v16.md` — planner row footnote updated to point at ADR-0023.
6. `adrs/README.md` — new row for ADR-0023; ADR-0017 status line updated to "Ratified v25 · Amended ×3 · Planner row superseded by ADR-0023".
7. `Kosmos-Build-Spec-v25.md` §17 — planner row updated; ADR reference changed from ADR-0017 to ADR-0023 for planner.
8. `PORTING_LEDGER.md` — no change (both cells already listed).
9. `BUILD_LOG.md` — new append entry timestamped 2026-08-11 09:49 EDT.

Not affected: coder wiring, embedder wiring, MCP registry (ADR-0019), any port assignments.

## Alternatives considered

**Alt 1: Keep planner = 35B-a3b-q4kxl despite the rubric.**
Rejected: violates the post_hoc_edit_locked scoring rule from ADR-0022. Amending the ADR every time the data conflicts with the previous decision defeats the point of locking the rubric before scoring. If the rubric is wrong, that requires a separate ADR authoring cycle, not silent noncompliance.

**Alt 2: Wait for Phase 0.3 multi-turn coder re-eval before deciding planner.**
Rejected: planner and coder verdicts are independent (different roles, different cells for planner). Delay costs nothing but adds nothing.

**Alt 3: Adopt a router that picks per-task by heuristic (e.g. 27B-q6k for migrations, 35B-a3b-q4kxl for everything else).**
Rejected as premature. No routing infrastructure exists at Phase 0.3 gate-1. The ADR-0017 "Option 2 — single large model at a time" co-residency policy still holds. Cross-task routing is a Phase 0.3 gate-2 or Phase 1 question at the earliest.

## Lock-in phase

Phase 0.3 gate-1. Router-selection frozen for the duration of Phase 0.3 unless the pre-registered migration-ordering probe (§5) reverses the planner ordering.

## References

- `bench/results/verdicts/medium-verdict-coder-20260811T134530Z.json`
- `bench/results/verdicts/medium-verdict-planner-20260811T134530Z.json`
- `bench/results/verdicts/medium-verdict-embedder-20260811T100541Z.json`
- `bench/rubrics/medium-scored.json` (post_hoc_edit_locked scoring rules)
- ADR-0017 (pre-Medium production role selection; planner row amended by this ADR)
- ADR-0022 (Phase 0.2 task-set + gold-reference lock)
- ADR-0016 (Medium-tier scoring rubric)
- ADR-0011 (coder tool-call parser `qwen3_coder`)
- ADR-0015 (planner thinker-2507-awq elimination)
