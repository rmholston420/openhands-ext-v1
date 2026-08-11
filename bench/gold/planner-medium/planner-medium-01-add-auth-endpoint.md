# planner-medium-01-add-auth-endpoint

## Task summary
Plan the addition of a `/auth/login` FastAPI endpoint that accepts `{username, password}`, validates against a Postgres users table, and returns a JWT on success.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Define Pydantic request/response models: LoginRequest with username+password, LoginResponse with access_token+token_type.", "deps": []},
    {"id": "s2", "desc": "Add a Users SQLAlchemy model with id, username (unique index), password_hash columns, if not already defined.", "deps": []},
    {"id": "s3", "desc": "Implement a helper verify_password(plain, hashed) using bcrypt (or the project's existing hash library).", "deps": []},
    {"id": "s4", "desc": "Implement create_access_token(sub, expires_delta) returning a signed JWT using the project's secret key.", "deps": []},
    {"id": "s5", "desc": "Implement POST /auth/login endpoint: look up user by username, verify_password, on success create_access_token and return LoginResponse; on failure return 401.", "deps": ["s1", "s2", "s3", "s4"]},
    {"id": "s6", "desc": "Add pytest cases: successful login returns 200 with a token, wrong password returns 401, missing user returns 401, malformed payload returns 422.", "deps": ["s5"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-7 steps covering: request/response models, user model, password verification, token creation, endpoint, tests. DAG valid. Deps sequenced correctly (endpoint depends on helpers). |
| 70-89 | Covers the endpoint + tests but misses either password verification or JWT creation as an explicit step. DAG still valid. |
| 40-69 | Covers endpoint but no test step, OR bundles too much into one step (e.g. "implement endpoint" without breaking out helpers). DAG valid. |
| 10-39 | 3+ steps but missing at least two of: models, hashing, JWT, endpoint, tests. |
| 0-9 | <3 steps, invalid JSON, cycles in DAG, or missing required schema fields. |

## Notes
Tests planner's ability to decompose an endpoint-with-auth task into ordered dependencies. Key discriminator: does the plan sequence dependencies correctly (models before endpoint, endpoint before tests)?
