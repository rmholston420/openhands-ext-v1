# planner-migration-probe-01-expand-backfill-contract

## Task summary
Plan a zero-downtime rollout that adds a non-nullable `country_code` VARCHAR(2) column to a large existing `users` table (~50M rows). New signups must populate it; existing rows must be backfilled from an external geolocation service; the column must ultimately be NOT NULL with a CHECK on ISO-3166 alpha-2 codes.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Author migration A: ADD COLUMN country_code VARCHAR(2) NULL (nullable, no default) — backward-compatible additive change.", "deps": []},
    {"id": "s2", "desc": "Deploy migration A to production; verify existing application continues to read/write users table unchanged.", "deps": ["s1"]},
    {"id": "s3", "desc": "Deploy application version that DUAL-WRITES: on new signup, populate country_code from geolocation service alongside existing writes; readers ignore the column.", "deps": ["s2"]},
    {"id": "s4", "desc": "Run backfill job in batches of 10k rows updating country_code for pre-existing users via the geolocation service; job is idempotent and retriable; log rows that fail lookup for manual review.", "deps": ["s3"]},
    {"id": "s5", "desc": "Verify backfill completion with SELECT COUNT(*) FROM users WHERE country_code IS NULL; resolve any residual NULLs (default to XX-unknown sentinel or targeted lookup) before proceeding.", "deps": ["s4"]},
    {"id": "s6", "desc": "Author migration B: ALTER COLUMN country_code SET NOT NULL and ADD CHECK constraint (country_code ~ '^[A-Z]{2}$').", "deps": ["s5"]},
    {"id": "s7", "desc": "Deploy migration B; monitor for constraint violations from any in-flight writes that predate s3.", "deps": ["s6"]},
    {"id": "s8", "desc": "Add pytest coverage for country_code population on new signup, geolocation-service failure fallback, and CHECK constraint rejection of malformed codes.", "deps": ["s7"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 7-9 steps sequencing: nullable ADD → deploy → dual-write app → backfill → verify → NOT NULL/CHECK migration → deploy → tests. DAG dependencies correct. **Backfill runs AFTER dual-write is live** so no new rows land NULL. **NOT NULL/CHECK is deployed AFTER backfill completes**. |
| 70-89 | Correct three-phase (expand-migrate-contract) structure but one of: (a) applies NOT NULL before backfill completes (breaks in-flight signups), or (b) starts backfill before dual-write is deployed (leaves race window where new signups land NULL). |
| 40-69 | Has migration + backfill + application change but combines the two migrations into one (breaks zero-downtime; ALTER TABLE ... NOT NULL on a large populated table takes a long exclusive lock). |
| 10-39 | 4+ steps but omits either the dual-write phase (backfill races with new signups) or the final CHECK constraint. |
| 0-9 | <4 steps or invalid JSON schema. |

## Notes
Tests classic three-phase expand-migrate-contract discipline. Key discriminators: (1) does the model recognize that a single ALTER TABLE ADD COLUMN NOT NULL DEFAULT on a 50M-row table is not zero-downtime? (2) does dual-write precede backfill? (3) is NOT NULL deferred until after backfill completes? Failure to sequence these correctly is the exact class of error 35b-a3b-q4kxl produced on planner-medium-02 and is what this probe re-tests systematically.
