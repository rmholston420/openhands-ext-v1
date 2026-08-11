# planner-medium-06-add-rate-limiting

## Task summary
Plan the addition of per-user rate limiting (100 requests/minute) to an existing FastAPI application, using Redis for state, with graceful 429 responses.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Add slowapi (or fastapi-limiter) to project dependencies, initialize with the Redis connection at application startup.", "deps": []},
    {"id": "s2", "desc": "Define a key function that identifies the caller: request.state.user_id if authenticated, otherwise request.client.host.", "deps": []},
    {"id": "s3", "desc": "Configure the rate-limit rule: 100 requests per 60 seconds, using the key function from s2.", "deps": ["s1", "s2"]},
    {"id": "s4", "desc": "Attach the rate limiter as FastAPI middleware or decorator, ensuring it fires before endpoint handlers.", "deps": ["s3"]},
    {"id": "s5", "desc": "Add an exception handler for RateLimitExceeded that returns HTTP 429 with a Retry-After header and a JSON error body.", "deps": ["s4"]},
    {"id": "s6", "desc": "Add pytest coverage: verify 100 requests succeed in a 60s window, verify the 101st returns 429, verify Retry-After header is present, verify separate users have independent limits.", "deps": ["s5"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-7 steps: library setup → key function → rule config → middleware attach → 429 handler → tests. Key function handles both auth and unauth cases. Tests verify per-user independence. |
| 70-89 | All steps present but key function uses only IP address (not per-user for authenticated requests — a design weakness). |
| 40-69 | Rate limit + 429 present but missing the Retry-After header (violates HTTP spec convention). |
| 10-39 | Rate limit mentioned but no clear key strategy — would apply globally not per-user. |
| 0-9 | <3 steps or invalid schema. |

## Notes
Tests planner's understanding of rate-limiting patterns. Key discriminator: does the plan handle the auth vs. unauth key-function distinction? Missing this creates either an over-permissive limit (all traffic sharing one bucket) or a bypass path (authenticated users have no limit).
