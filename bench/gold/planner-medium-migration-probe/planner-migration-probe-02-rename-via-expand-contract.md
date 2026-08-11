# planner-migration-probe-02-rename-via-expand-contract

## Task summary
Plan a zero-downtime rename of the `email` column on the `accounts` table to `primary_email`, across a service with multiple deployed replicas that read and write the column concurrently. No column drops or renames allowed as a single atomic step — must use expand-contract.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Author migration A: ADD COLUMN primary_email VARCHAR(255) NULL (initially unpopulated); do not touch existing email column.", "deps": []},
    {"id": "s2", "desc": "Deploy migration A; verify all replicas continue to read/write email as before (primary_email is invisible to app code).", "deps": ["s1"]},
    {"id": "s3", "desc": "Deploy application version R1 that DUAL-WRITES: every INSERT and UPDATE writes the same value to both email and primary_email; readers continue to read email only.", "deps": ["s2"]},
    {"id": "s4", "desc": "Run backfill job to populate primary_email = email for all rows where primary_email IS NULL; batch and retry-safe; verify row count matches.", "deps": ["s3"]},
    {"id": "s5", "desc": "Deploy application version R2 that reads from primary_email (with COALESCE(primary_email, email) fallback for safety); continues to dual-write.", "deps": ["s4"]},
    {"id": "s6", "desc": "After R2 is fully rolled out to all replicas and stable (bake period ~24h), deploy application version R3 that reads and writes ONLY primary_email; email column becomes ignored by application.", "deps": ["s5"]},
    {"id": "s7", "desc": "Author migration B: DROP COLUMN email (safe now that no live code path reads or writes it).", "deps": ["s6"]},
    {"id": "s8", "desc": "Deploy migration B; add pytest coverage that verifies INSERT/UPDATE/SELECT paths use primary_email exclusively and email column is gone.", "deps": ["s7"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 7-9 steps sequencing: ADD new column → deploy → dual-write app → backfill → read-from-new-with-fallback → drop old references → DROP COLUMN migration → deploy + tests. **Dual-write precedes backfill**; **fallback reader (COALESCE or equivalent) precedes drop-old-writes**; **DROP COLUMN happens ONLY after all replicas stop reading email**. |
| 70-89 | Correct expand-contract structure but skips the fallback-reader intermediate step (goes directly from dual-write to reads-primary-email-only without COALESCE safety net) OR drops the old column before verifying all replicas have rolled to the new reader. |
| 40-69 | Uses expand-contract shape but combines rename into one migration (ALTER TABLE ... RENAME COLUMN) which breaks in-flight replicas, or omits the dual-write phase entirely. |
| 10-39 | 4+ steps but misses the multi-replica coordination (assumes single deploy is atomic across replicas) or omits the backfill. |
| 0-9 | <4 steps or invalid JSON schema. Also 0-9: plan uses a single ALTER TABLE ... RENAME COLUMN as its central step (fatal for zero-downtime multi-replica). |

## Notes
Tests understanding of expand-contract rename discipline in a multi-replica environment. Key discriminators: (1) does the plan avoid the naive RENAME COLUMN? (2) does it dual-write before backfilling? (3) does it introduce a fallback reader (COALESCE) as a safety layer between dual-write and drop-old-column? (4) does DROP COLUMN happen strictly last, only after every replica has rolled to primary_email-exclusive code? This is a stricter test than probe 01 because the discipline is entirely at the application-deploy layer, not at the DB migration layer.
