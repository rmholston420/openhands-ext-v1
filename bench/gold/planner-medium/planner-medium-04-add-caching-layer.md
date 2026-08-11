# planner-medium-04-add-caching-layer

## Task summary
Plan the addition of a Redis-based caching layer in front of an existing PostgreSQL-backed `get_user_by_id(id)` function, with TTL-based invalidation and explicit cache-invalidate calls on user updates.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Add a Redis client dependency (redis-py) and initialize a connection pool at application startup, configured via environment variables.", "deps": []},
    {"id": "s2", "desc": "Define a cache-key convention like user:{id} and a default TTL constant (e.g. 300 seconds).", "deps": []},
    {"id": "s3", "desc": "Wrap get_user_by_id: check Redis first via GET user:{id}; on miss, query Postgres, SET the result with TTL, return; on hit, return the cached value.", "deps": ["s1", "s2"]},
    {"id": "s4", "desc": "Add explicit cache invalidation in update_user and delete_user paths: DEL user:{id} after the DB write completes.", "deps": ["s3"]},
    {"id": "s5", "desc": "Add serialization handling: use JSON serialization for user records; handle deserialization errors by treating them as cache misses.", "deps": ["s3"]},
    {"id": "s6", "desc": "Add pytest coverage: cache hit path, cache miss populates cache, update invalidates cache, corrupted cache entry falls through to DB.", "deps": ["s4", "s5"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-7 steps covering: Redis client setup, cache-key + TTL, read-through wrapper, explicit invalidation on update/delete, serialization, tests. DAG shows invalidation depends on wrapper. |
| 70-89 | Cache layer + tests covered but misses explicit invalidation on update/delete (relies on TTL only — a real correctness bug). |
| 40-69 | Correct read-through but no serialization handling (fails on non-string types) OR no test coverage. |
| 10-39 | Cache mentioned but no clear invalidation strategy AND no TTL specified. |
| 0-9 | <3 steps or plan describes putting the cache after the DB write instead of before. |

## Notes
Tests planner's understanding of cache-invalidation patterns (a classic source of correctness bugs). Key discriminator: does the plan explicitly invalidate the cache on update, or does it rely only on TTL (which creates stale-read windows)?
