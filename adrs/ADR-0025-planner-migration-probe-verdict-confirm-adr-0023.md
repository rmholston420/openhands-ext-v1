# ADR-0025 — Planner migration-ordering probe verdict: CONFIRM ADR-0023 (27b-q6k retained)

**Status:** Ratified
**Lock-in phase:** Phase 0.3 gate-1
**Supersedes:** —
**Extends:** ADR-0023, ADR-0024

## Context

ADR-0023 flipped the planner role from `qwen3_6-35b-a3b-q4kxl-gguf` to `qwen3_6-27b-q6k-gguf` on quality-first grounds (91.0 vs 86.7 macro-avg on planner-medium.json, 4.3-pt gap outside the 3-pt tiebreak band). Because the underlying signal was largely driven by task planner-medium-02 (migration ordering), ADR-0023 §5 pre-registered a 4-task migration-ordering probe with pre-registered reversal criteria — filed as ADR-0024.

The probe ran on 2026-08-11 at 10:07-10:08 EDT (results `smoke-medium-planner-*-20260811T1407*Z*.json`). Both cells produced schema-valid structured JSON, `verdict=pass` at the R1/R2 level on all 4 tasks. This ADR records the Perplexity-Max scoring against the 4 gold references, applies the pre-registered reversal criteria, and locks the planner routing decision.

## Decision

The planner role assignment established in ADR-0023 is **CONFIRMED**. `qwen3_6-27b-q6k-gguf` (llama.cpp, GPU, port :8082) remains the production planner cell. No routing changes.

### Sub-decision 1 — Per-task scores (Perplexity Max, gold-bounded)

Scoring authority: Perplexity Max (Claude Sonnet 4.6 via Perplexity Computer). Self-scoring prohibited per rubric. Bands per gold rubric in `bench/gold/planner-medium-migration-probe/`.

| Task | 27b-q6k | 35b-a3b-q4kxl | Notes |
|---|---:|---:|---|
| probe-01 expand-migrate-contract | 92 | 85 | 35b combined CHECK+NOTNULL into one migration; 27b kept them split per gold structure. Neither triggered the 40-69 or 70-89 failure modes. |
| probe-02 rename via expand-contract | 90 | 91 | Both correct expand-contract with COALESCE fallback. 27b sequences COALESCE reader before backfill (unusual but defensible — COALESCE bridges the gap). 35b sequences dual-write→backfill→COALESCE per gold canonical order. |
| probe-03 FK with cleanup | 92 | 78 | 35b omitted the orphan-count verification step between cleanup and constraint add — same failure class as planner-medium-02 (skipped intermediate verification). 27b included verify step explicitly. |
| probe-04 concurrent index rebuild | 93 | 92 | Both correct: CREATE INDEX CONCURRENTLY, ANALYZE, bake period, DROP INDEX CONCURRENTLY, recovery contingency. Essentially tied. |
| **Macro-avg** | **91.75** | **86.50** | 27b leads by 5.25 pts. |

### Sub-decision 2 — Application of pre-registered reversal criteria

Reversal criteria as locked in `bench/tasks/planner-medium-migration-probe.json#/reversal_criteria` before scoring (post-hoc interpretation prohibited):

| Rule | Threshold | 35b Actual | Fired? |
|---|---|---|---|
| Flip to 35b: scores ≥90 on ALL 4 tasks | all ≥90 | 85, 91, 78, 92 | ❌ (85 <90, 78 <90) |
| Flip to 35b: macro-avg beats 27b by >3 pts | 35b − 27b > 3 | -5.25 | ❌ |
| Confirm ADR-0023: 35b <70 on ANY task | any <70 | min 78 | ❌ |
| **Confirm ADR-0023: 27b leads by ≥3 pts** | 27b − 35b ≥ 3 | **+5.25** | ✅ **FIRED** |
| Intermediate branch | otherwise | N/A | N/A |

**Decision path:** rule 4 fired unambiguously; no other rule contradicts. Confirm ADR-0023.

### Sub-decision 3 — Wall-time reality check (documentation only, non-binding)

Speed data (probe wall_seconds per task, from `.probe.json` files):

| Task | 27b wall | 35b wall | Gap |
|---|---:|---:|---:|
| probe-01 | 9.62 s | 2.19 s | 4.4× |
| probe-02 | 9.98 s | 2.31 s | 4.3× |
| probe-03 | 7.23 s | 1.48 s | 4.9× |
| probe-04 | 8.33 s | 2.07 s | 4.0× |
| Total | 35.16 s | 8.05 s | 4.4× |

Speed gap widened vs Phase 0.2 planner-medium (16.6 s per candidate). 35b is 4.4× faster wall on this task class. Speed rule applies only within the 3-pt quality tiebreak band; quality gap (5.25 pts) is outside band, so speed does not overturn.

### Sub-decision 4 — Router config unchanged; no cascading amendments

- `bench/candidates/planner-medium-pool.json` — no change
- Production router (per ADR-0023) planner → `qwen3_6-27b-q6k-gguf` — no change
- Fallback cell for planner remains `qwen3_6-35b-a3b-q4kxl-gguf` (not eliminated; still viable at 86.5, above the 70-pt disqualification threshold on all tasks)
- ADR-0017 (Amended-4) row for planner remains superseded by ADR-0023
- No spec (`docs/specs/*`) edit required; ADR-0023 already recorded the flip in §17 ADR summary

## Rationale

**Why confirm and not flip.** The pre-registered reversal criteria were designed exactly to avoid post-hoc bias in the direction of a preferred outcome. Rule 4 (`27b leads by ≥3 pts`) fired with a 5.25-pt margin. Under the ADR-0022 post-hoc-edit lock, the decision must follow the fired rule; overriding it would require an ADR amendment that pre-dates scoring, which does not exist.

**Why the migration-ordering weakness in 35b persists.** Probe-03 reproduced the exact skipped-verification failure class from planner-medium-02. This is a stable model behavior on this task class, not a task-specific anomaly. 27b's discipline on multi-phase migrations (verify count, split NOT VALID / VALIDATE, three-phase expand-migrate-contract) is consistently ~5-7 pts above 35b across the probe. Confirms the Phase 0.2 signal.

**Why 35b is not disqualified.** All 4 probe scores are ≥78 (well above the 70-pt disqualification band). 35b remains a valid fallback cell for planner and a strong candidate for other roles (recall it scored 80.9 on coder-medium, close to coder-30B-instruct-awq's 78.9 quality). No pool changes.

**Why the wall-time gap does not override.** 35b is 4.4× faster. Under the medium-scored rubric, speed tiebreaks only within 3 pts of quality. 5.25 pts is outside the band. If a future workload class emerges where 35b's speed advantage is critical AND its quality gap on that class is ≤3 pts, a workload-specific router entry could be added — but not on migration-planning traffic.

## Consequences

- **Files to update in this fan-out:**
  - `adrs/ADR-0025-planner-migration-probe-verdict-confirm-adr-0023.md` (this file)
  - `adrs/README.md` (index row added)
  - `BUILD_LOG.md` (append entry)
  - `SESSION_HANDOFF.md` (overwrite — probe complete, next Phase 0.3 action)
  - `bench/scoring/planner-migration-probe-20260811_1408/` (new — verdict + per-task rationale)
- **No changes to:**
  - `bench/candidates/planner-medium-pool.json`
  - `bench/tasks/planner-medium-migration-probe.json` (post_hoc_edit_locked)
  - `bench/gold/planner-medium-migration-probe/` (post_hoc_edit_locked)
  - `bench/rubrics/medium-scored.json` (no rubric change)
  - `Kosmos-Build-Spec-v25.md` §17 (ADR-0023 row already reflects planner = 27b-q6k)
  - `docs/specs/integration-execution-plan-v16.md` (no spec surface affected)
- **Probe artifacts retained (raw evidence for auditability):**
  - `bench/results/smoke-medium-planner-qwen3_6-27b-q6k-gguf-llama-cpp-gpu-20260811T140708Z.json` + `.probe.json`
  - `bench/results/smoke-medium-planner-qwen3_6-35b-a3b-q4kxl-gguf-llama-cpp-gpu-20260811T140749Z.json` + `.probe.json`

## Lock-in phase

Phase 0.3 gate-1. This ADR closes the ADR-0023 §5 pre-registration and locks the planner cell for the Phase 0.3 production router.

## References

- ADR-0016 (medium-tier scoring rubric)
- ADR-0022 (Phase 0.2 task-set and gold protocol; post_hoc_edit_locked pattern)
- ADR-0023 (Phase 0.3 planner flip — this ADR confirms)
- ADR-0024 (probe task-set + gold + pre-registered reversal criteria — this ADR resolves)
- `bench/tasks/planner-medium-migration-probe.json` (probe spec)
- `bench/gold/planner-medium-migration-probe/` (gold references, hash-frozen)
- `bench/results/smoke-medium-planner-*20260811T1407*Z*.json` (raw probe outputs)
