# planner-migration-probe-04-concurrent-index-rebuild

## Task summary
Plan a zero-downtime index change on a hot production table (`events`, ~1.2 billion rows, 8,000 QPS read/write). The existing index `idx_events_created_at` is a plain btree; you need to replace it with a partial index `WHERE processed_at IS NULL` to accelerate the unprocessed-events queue query. The old index cannot be dropped until all query planners have adopted the new one. Postgres backend.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Confirm the current query pattern for the unprocessed-events queue with EXPLAIN ANALYZE against production (or a recent snapshot) and record baseline latency and rows-scanned metrics.", "deps": []},
    {"id": "s2", "desc": "Author migration A: CREATE INDEX CONCURRENTLY idx_events_created_at_unprocessed ON events (created_at) WHERE processed_at IS NULL; run OUTSIDE any transaction (Postgres requirement for CONCURRENTLY).", "deps": ["s1"]},
    {"id": "s3", "desc": "Deploy migration A during off-peak window; monitor pg_stat_progress_create_index and confirm the new index reaches valid state (indisvalid = true, indisready = true) — expect long duration on 1.2B rows.", "deps": ["s2"]},
    {"id": "s4", "desc": "If CONCURRENTLY build fails partway (leaves invalid index), run DROP INDEX CONCURRENTLY idx_events_created_at_unprocessed and retry from s2; do NOT proceed with an invalid index.", "deps": ["s3"]},
    {"id": "s5", "desc": "Run ANALYZE events to refresh planner statistics; verify new index is chosen with EXPLAIN on the queue query.", "deps": ["s3"]},
    {"id": "s6", "desc": "Deploy application-code query hint or planner-cost tuning (if the planner does not naturally prefer the partial index) — verify via pg_stat_user_indexes that idx_scan on the new index climbs and idx_scan on the old one plateaus.", "deps": ["s5"]},
    {"id": "s7", "desc": "Bake period (24-72h): monitor that no query regressions appear and that the new index is serving the target workload; confirm old index scan count is flat or decreasing.", "deps": ["s6"]},
    {"id": "s8", "desc": "Author migration B: DROP INDEX CONCURRENTLY idx_events_created_at; deploy during off-peak window.", "deps": ["s7"]},
    {"id": "s9", "desc": "Add operational-runbook entry documenting the index change, the CONCURRENTLY discipline, and rollback procedure (recreate old index CONCURRENTLY if the new one turns out to underperform).", "deps": ["s8"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 7-9 steps sequencing: baseline → CREATE INDEX CONCURRENTLY → invalid-recovery contingency → ANALYZE → planner-adoption verification → bake period → DROP INDEX CONCURRENTLY → runbook. **CREATE INDEX CONCURRENTLY explicit** (not plain CREATE INDEX). **DROP INDEX CONCURRENTLY explicit**. **Bake period between new-index-live and old-index-drop is called out** — model recognizes that dropping the old index prematurely can regress queries that the planner did not migrate to the new index. **ANALYZE step present** so planner statistics reflect the new index. |
| 70-89 | Uses CONCURRENTLY correctly on both create and drop but skips the bake period (drops the old index immediately after creating the new one, risking planner-regression window) OR omits the ANALYZE step. |
| 40-69 | Uses CREATE INDEX CONCURRENTLY but plain DROP INDEX (takes an exclusive lock on a hot 1.2B-row table's index — brief but blocks writes), OR omits the invalid-index recovery contingency. |
| 10-39 | 4+ steps but uses a plain CREATE INDEX (takes an ACCESS EXCLUSIVE lock, blocks all writes for hours on a 1.2B-row table) — fatal for zero-downtime. |
| 0-9 | <4 steps or invalid JSON schema. Also 0-9: plan tries to DROP INDEX before CREATE INDEX (leaves a window with no supporting index on a hot query) or drops-and-recreates inside a single transaction. |

## Notes
Tests understanding of index-rollout ordering on a hot table. Key discriminators: (1) CREATE INDEX CONCURRENTLY vs plain CREATE INDEX — the difference between zero-downtime and a multi-hour outage on a 1.2B-row table? (2) does the plan bake the new index before dropping the old one, so query planners have time to adopt it? (3) does it distinguish between "index built" (indisready) and "index usable by queries" (indisvalid + ANALYZE)? (4) does it include a rollback path for a failed CONCURRENTLY build? Unlike probes 01-03, the ordering here is not about DB vs application code — it's about parallel-index existence and planner adoption within the DB layer.
