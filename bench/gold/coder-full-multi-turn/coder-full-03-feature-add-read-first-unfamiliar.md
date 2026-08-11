# Gold rubric — coder-full-03-feature-add-read-first-unfamiliar

**Task prompt (verbatim):**
> In /workspace/repo/src/cache/lru.py, the class LRUCache has get() and put() methods and existing tests under tests/test_lru.py. Add a new method `peek(key)` that returns the value associated with key if present, or None if absent, WITHOUT updating recency (unlike get()). Do not modify any existing method's behavior. After your edits, `python -m pytest tests/ -q` must exit 0.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Locked:** post_hoc_edit_locked per ADR-0028

## Correctness criteria

- `peek(key)` MUST NOT call `self._data.move_to_end(key)`.
- `peek(key)` MUST return `None` for missing keys (not raise KeyError).
- Existing `get` and `put` methods MUST be byte-identical (or semantically identical if reformatted).
- All three tests in `test_lru.py` MUST pass: `test_get_put_basic`, `test_peek_does_not_update_recency`, `test_peek_missing_key`.

## Reference implementation

```python
def peek(self, key):
    if key not in self._data:
        return None
    return self._data[key]
```

Also acceptable: `return self._data.get(key)`.

## Scoring bands

### 90-100 — Exemplary
- All 3 tests pass.
- `peek` correctly avoids `move_to_end`. `get`/`put` unchanged.
- Turn count near minimum (read → edit → smoke).

### 75-89 — Correct with minor process flaws
- Tests pass. Extra reads or one extra smoke run.
- `peek` implementation is verbose but correct.

### 60-74 — Partially correct
- `peek` calls `move_to_end` (breaks `test_peek_does_not_update_recency`) but returns correct values for existing keys.
- OR `peek` raises KeyError on missing key (breaks `test_peek_missing_key`).

### 40-59 — Substantially incorrect
- `get` or `put` modified in behavior.
- OR tests modified.

### 20-39 — Mostly failed
- Multiple existing tests broken.

### 0-19 — Failed
- `peek` not added; no edits.

## Deductions
- −5 hit max_iter=20
- −3 dispreferred tool
- −5 (band cap) modifying tests or existing methods

## Bonuses
- +2 minimum turn count
- +2 perfect preservation of `get`/`put` bytes
