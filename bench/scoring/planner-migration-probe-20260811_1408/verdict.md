# Planner migration-ordering probe verdict — 2026-08-11 14:08 UTC

**Scoring authority:** Perplexity Max (Claude Sonnet 4.6 via Perplexity Computer).
**Rubric:** `bench/gold/planner-medium-migration-probe/*.md` per-task bands (0-100).
**Reversal criteria:** pre-registered in `bench/tasks/planner-medium-migration-probe.json#/reversal_criteria`.
**ADR:** locked in ADR-0025.

## Per-task scores

| Task | 27b-q6k | 35b-a3b-q4kxl |
|---|---:|---:|
| probe-01 expand-migrate-contract | 92 | 85 |
| probe-02 rename via expand-contract | 90 | 91 |
| probe-03 FK with cleanup | 92 | 78 |
| probe-04 concurrent index rebuild | 93 | 92 |
| **Macro-avg** | **91.75** | **86.50** |

## Wall-time (documentation only, non-binding)

| Task | 27b wall | 35b wall |
|---|---:|---:|
| probe-01 | 9.62 s | 2.19 s |
| probe-02 | 9.98 s | 2.31 s |
| probe-03 | 7.23 s | 1.48 s |
| probe-04 | 8.33 s | 2.07 s |
| Total | 35.16 s | 8.05 s |

35b is 4.4× faster wall on this task class. Speed rule applies only within 3-pt quality tiebreak; quality gap 5.25 pts is outside band.

## Reversal-criteria application

- Flip to 35b (all ≥90): FAIL — 85, 91, 78, 92
- Flip to 35b (macro-avg >+3): FAIL — -5.25
- Confirm ADR-0023 (35b <70 any): not triggered — min 78
- **Confirm ADR-0023 (27b leads ≥+3): FIRED — +5.25**
- Intermediate: N/A

## Decision

**CONFIRM ADR-0023.** Production planner remains `qwen3_6-27b-q6k-gguf` (llama.cpp, GPU, :8082). No routing changes. 35b-a3b-q4kxl remains a valid fallback (all scores ≥78) but is not the production cell.

## Per-task rationale

### probe-01 expand-migrate-contract

- **27b-q6k (92):** 9 steps; nullable ADD (s1) → dual-write deploy (s2-s3) → backfill AFTER dual-write (s4) → verify (s5) → CHECK constraint alone (s6) → NOT NULL alone (s7) → remove dual-write (s8) → tests (s9). Follows gold canonical structure exactly. All 90-100 discriminators explicit.
- **35b-a3b (85):** 8 steps; correct dual-write-before-backfill and NOT-NULL-after-backfill sequencing, but combined CHECK+NOTNULL into a single migration (s6). Not the 40-69 failure mode (which is ADD+ALTER combined), but does lose points on gold canonical structure.

### probe-02 rename via expand-contract

- **27b-q6k (90):** 10 steps; ADD nullable column (s1-s2) → R1 dual-write (s3) → R2 COALESCE fallback (s4) → backfill (s5) → verify (s6) → R3 remove dual-write (s7) → DROP COLUMN migration (s8-s9) → tests (s10). No naive RENAME. Sequences COALESCE reader before backfill (unusual — gold has backfill then COALESCE); defensible because COALESCE bridges the gap during backfill.
- **35b-a3b (91):** 9 steps; ADD column + R1 dual-write (s1-s2) → backfill (s3) → COALESCE code (s4) → R2 deploy (s5) → tests (s6) → bake (s7) → R3 primary-only (s8) → DROP COLUMN (s9). Follows gold canonical order (dual-write → backfill → COALESCE-reader → drop-old). Slightly cleaner than 27b's variant.

### probe-03 FK with cleanup

- **27b-q6k (92):** 7 steps; identify orphans (s1) → app-guard (s2) → cleanup policy (s3) → verify zero orphans (s4) → ADD CONSTRAINT NOT VALID (s5) → VALIDATE CONSTRAINT (s6) → tests (s7). Cleanup precedes constraint. NOT VALID/VALIDATE split explicit. App-guard deployed. Verify step present.
- **35b-a3b (78):** 6 steps; identify (s1) → app-guard (s2) → cleanup (s3) → ADD CONSTRAINT NOT VALID (s4) → VALIDATE (s5) → tests (s6). **Omits orphan-count verification step between cleanup and constraint** — same failure class as planner-medium-02 (skipped intermediate verification). Rubric 40-69 band explicitly names "omits the orphan-query verification step" but 35b still has NOT VALID split and app-guard which are 70-89 anchors. Best fit upper 70-89.

### probe-04 concurrent index rebuild

- **27b-q6k (93):** 8 steps; EXPLAIN baseline (s1) → CREATE INDEX CONCURRENTLY (s2) → monitor + REINDEX CONCURRENTLY recovery contingency (s3) → ANALYZE (s4) → verify planner adoption (s5) → 24h bake (s6) → DROP INDEX CONCURRENTLY (s7) → runbook (s8). All 90-100 discriminators explicit including recovery contingency.
- **35b-a3b (92):** 8 steps; EXPLAIN ANALYZE baseline (s1) → CREATE INDEX CONCURRENTLY (s2) → monitor pg_stat_progress + abort/manual recovery (s3) → ANALYZE (s4) → verify (s5) → 24h bake (s6) → DROP INDEX CONCURRENTLY (s7) → runbook (s8). Essentially tied with 27b; both meet all 90-100 discriminators.

## Notes on 35b's failure mode

Probe-03 reproduced the exact skipped-verification failure class from planner-medium-02. This is a stable model behavior on migration ordering, not a task-specific anomaly. Consistent with the Phase 0.2 signal that motivated ADR-0023.
