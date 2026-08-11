# planner-migration-probe-03-fk-with-cleanup

## Task summary
Plan a zero-downtime rollout that adds a foreign-key constraint from `orders.customer_id` → `customers.id`. Historical data contains ~4,000 orphan rows in `orders` whose `customer_id` does not correspond to any live `customers.id` (deleted customers, legacy imports). The FK must be added with ON DELETE RESTRICT.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Query the orphan set: SELECT o.id, o.customer_id FROM orders o LEFT JOIN customers c ON c.id = o.customer_id WHERE c.id IS NULL; save the CSV for audit.", "deps": []},
    {"id": "s2", "desc": "Author a data-cleanup script that resolves each orphan by one of three policies: (a) reassign to a designated 'archived-customer' sentinel row, (b) NULL out customer_id if the schema permits, or (c) hard-delete the orphan order — decide per business rule and document.", "deps": ["s1"]},
    {"id": "s3", "desc": "Deploy an application-code guard that rejects any new INSERT/UPDATE into orders where customer_id does not exist in customers (belt-and-suspenders check ahead of the DB constraint).", "deps": ["s2"]},
    {"id": "s4", "desc": "Run the cleanup script against production; re-run the orphan query and verify count is zero before proceeding.", "deps": ["s3"]},
    {"id": "s5", "desc": "Author migration A: ALTER TABLE orders ADD CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT NOT VALID (Postgres) or online-DDL equivalent — avoids full-table validation lock.", "deps": ["s4"]},
    {"id": "s6", "desc": "Deploy migration A; the constraint is enforced on new INSERT/UPDATE but existing rows are not re-validated yet.", "deps": ["s5"]},
    {"id": "s7", "desc": "Run ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_customer as a separate low-priority step — takes a share lock, not exclusive, so reads/writes continue.", "deps": ["s6"]},
    {"id": "s8", "desc": "Add pytest coverage: (a) INSERT with invalid customer_id is rejected, (b) DELETE of a customer with orders is blocked by RESTRICT, (c) valid inserts succeed.", "deps": ["s7"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 7-9 steps sequencing: identify orphans → author cleanup policy → deploy app-guard → run cleanup → verify → ADD CONSTRAINT NOT VALID → deploy → VALIDATE CONSTRAINT → tests. **Cleanup precedes constraint addition**; **NOT VALID split from VALIDATE** to avoid full-table exclusive lock on a large table; **app-guard deployed before cleanup** to prevent new orphans landing during cleanup. |
| 70-89 | Correct sequence overall but one of: (a) uses a single ADD CONSTRAINT without the NOT VALID / VALIDATE split (works but takes a longer lock), or (b) skips the app-guard step (small race window during cleanup where new orphans could land). |
| 40-69 | Runs cleanup and adds FK in correct relative order but combines cleanup with constraint addition into one migration (violates zero-downtime if the FK add fails partway through), OR omits the orphan-query verification step. |
| 10-39 | 4+ steps but tries to ADD CONSTRAINT before cleanup (constraint add fails immediately on orphan rows), OR relies on ON DELETE CASCADE without discussing the data-loss implication. |
| 0-9 | <4 steps or invalid JSON schema. Also 0-9: plan proposes to ADD CONSTRAINT as step 1 (fatal — will error on orphan rows). |

## Notes
Tests understanding that referential-integrity backfill and constraint addition are separate concerns that must be sequenced with a cleanup-first discipline. Key discriminators: (1) does the plan identify and cleanse orphans BEFORE adding the constraint? (2) does it deploy an application-layer guard so new orphans don't land during the cleanup window? (3) does it use the NOT VALID / VALIDATE split (or equivalent online-DDL feature) to avoid a full-table exclusive lock? (4) does it distinguish RESTRICT vs CASCADE semantics? A model that puts ADD CONSTRAINT first will fail immediately on the first orphan — this is the migration-ordering failure class the probe targets.
