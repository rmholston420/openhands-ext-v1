# planner-medium-02-migrate-database

## Task summary
Plan a zero-downtime schema migration to add a `deleted_at` timestamp column to an existing `orders` table, with the application reading soft-delete state from it.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Author an alembic migration that adds the deleted_at column (nullable timestamp with default NULL) to the orders table.", "deps": []},
    {"id": "s2", "desc": "Deploy the migration to production, verifying no application read/write breakage (nullable column is backward-compatible).", "deps": ["s1"]},
    {"id": "s3", "desc": "Update the Order SQLAlchemy model to include the deleted_at column.", "deps": ["s2"]},
    {"id": "s4", "desc": "Update all order-fetching query paths to filter WHERE deleted_at IS NULL by default; add an include_deleted=True parameter for admin/audit paths.", "deps": ["s3"]},
    {"id": "s5", "desc": "Replace hard DELETE calls with UPDATE orders SET deleted_at = NOW() in the order-deletion service methods.", "deps": ["s4"]},
    {"id": "s6", "desc": "Add pytest coverage for soft-delete behavior: deleted orders excluded from default queries, included when include_deleted=True, deleted_at populated on delete call.", "deps": ["s5"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-7 steps sequencing: migration → deploy → model update → query update → delete-path change → tests. DAG dependencies correct (deploy before code changes; query filter before soft-delete rewrite). |
| 70-89 | Correct steps but sequences deploy-migration after the model change (breaks zero-downtime) OR misses the "add include_deleted" flag consideration. |
| 40-69 | Covers migration + model + delete rewrite but combines deploy with migration authorship (loses the deployment gate). |
| 10-39 | 3+ steps but misses either the query-filter update or the delete-path rewrite (leaves the system in inconsistent state). |
| 0-9 | <3 steps or invalid schema. |

## Notes
Tests planner's understanding of zero-downtime schema migration ordering. Key discriminator: does the plan deploy the migration before changing application code that reads/writes the new column? Models that get the ordering wrong reveal shallow understanding of migration mechanics.
