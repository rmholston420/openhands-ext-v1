# coder-medium-01-json-config-flip

## Task summary
Toggle a boolean field inside a nested JSON config while preserving the surrounding structure and indentation.

## Expected tool-call transcript
1. `read_file("/workspace/repo/config/app.json")` — inspect current contents before deciding how to edit.
2. `str_replace_editor` — targeted single-line replacement: `"debug": false` → `"debug": true`.

## Expected file state after diff
```
/workspace/repo/config/app.json:
{
  "app": {
    "name": "medium-01",
    "version": "1.0.0",
    "debug": true
  },
  "database": {
    "url": "sqlite:///data.db",
    "pool_size": 5
  }
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Uses `str_replace_editor` on the `"debug"` line only; final file equals expected byte-for-byte; no bash invocation |
| 70-89 | Correct final file state but tool choice is `write_file` (rewrites the whole file instead of surgical edit) |
| 40-69 | Uses `execute_bash sed` or similar — brittle to whitespace; final state correct on this fixture but non-robust |
| 10-39 | File modified but structure damaged (indentation/trailing-comma/other keys touched) |
| 0-9 | File unmodified, corrupted, or wrong file targeted |

## Notes
Tests tool-selection discipline on a task where the naive path (bash sed) works but is dispreferred. This is the exact anti-pattern that ADR-0011/0014 rescored.
