# planner-medium-03-refactor-callback-to-async

## Task summary
Plan the refactor of a callback-based file-processing pipeline into an async/await implementation using asyncio, preserving all existing call sites and public API.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Inventory all public functions in the pipeline module and their current callback signatures.", "deps": []},
    {"id": "s2", "desc": "Author async versions of each pipeline function with the naming convention <name>_async (e.g. process_file → process_file_async), matching the original signatures minus callbacks.", "deps": ["s1"]},
    {"id": "s3", "desc": "Refactor internal pipeline logic to use await for I/O (file reads via aiofiles, network via aiohttp or the project's async client).", "deps": ["s2"]},
    {"id": "s4", "desc": "Keep the original callback-based functions as thin wrappers that call the async versions via asyncio.run + a shim that invokes the callback with the result.", "deps": ["s3"]},
    {"id": "s5", "desc": "Add pytest-asyncio tests for the new async surface, plus regression tests confirming original callback paths still return correct results.", "deps": ["s4"]},
    {"id": "s6", "desc": "Mark the callback-based wrapper functions with a DeprecationWarning pointing at the async surface.", "deps": ["s4"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-7 steps sequencing: inventory → async surface → async internals → wrapper preservation → tests. Explicit backward-compat commitment (wrappers OR feature flag). DAG valid. |
| 70-89 | Correct sequencing but skips inventory step OR misses the DeprecationWarning/migration-path step (still preserves BC via wrappers). |
| 40-69 | Refactor plan valid but drops backward compatibility (removes callback functions instead of wrapping them). |
| 10-39 | Async conversion mentioned but no plan for existing call sites; would break them. |
| 0-9 | <3 steps or invalid schema. |

## Notes
Tests planner's handling of an invariant-preserving refactor. Key discriminator: is backward compatibility explicitly preserved? Models that just "rewrite as async" without addressing existing callers lose points.
