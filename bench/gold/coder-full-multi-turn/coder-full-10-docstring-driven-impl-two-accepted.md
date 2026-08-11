# Gold rubric — coder-full-10-docstring-driven-impl-two-accepted

**Task prompt (verbatim):**
> In /workspace/repo/src/algos.py, implement the function median_of_running_stream(values: list[int]) -> float | None per its docstring. Replace the `pass` body with a correct implementation. Do not change the signature or docstring.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Locked:** post_hoc_edit_locked per ADR-0028

## Correctness criteria

All 5 docstring examples MUST pass:
- `median_of_running_stream([])` → `None`
- `median_of_running_stream([3])` → `3.0`
- `median_of_running_stream([1, 2, 3])` → `2.0`
- `median_of_running_stream([1, 2, 3, 4])` → `2.5`
- `median_of_running_stream([1, 1, 2])` → `1.0` (duplicates counted individually — NOT deduped)

Signature and docstring MUST be byte-identical to fixture.

## Two accepted reference implementations

### (a) sorted-copy indexing

```python
def median_of_running_stream(values: list[int]) -> float | None:
    """<docstring unchanged>"""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2
```

### (b) statistics.median

```python
import statistics

def median_of_running_stream(values: list[int]) -> float | None:
    """<docstring unchanged>"""
    if not values:
        return None
    return float(statistics.median(values))
```

Both are exemplary.

## Scoring bands

### 90-100 — Exemplary
- One of the two reference implementations (or a functionally identical variant).
- All 5 examples produce correct outputs.
- Signature + docstring preserved.

### 75-89 — Correct with minor process flaws
- Correct impl but returns int for odd-length lists (e.g. `s[mid]` instead of `float(s[mid])`). Fails the `== 3.0` example only under strict type equality (Python `3 == 3.0` is True but `isinstance(3, float)` is False — smoke may still pass since `assert m([3]) == 3.0` succeeds; downgrade only if strict).
- Extra imports beyond `statistics`.

### 60-74 — Partially correct
- Fails 1 of 5 examples (e.g. edge case on single-element list returns None).

### 40-59 — Substantially incorrect
- Dedupes values (`set(values)`) → fails `median([1,1,2]) == 1.0` (would return 1.5).
- OR changes signature.
- OR returns int for even-length lists (e.g. `1` instead of `1.0`).

### 20-39 — Mostly failed
- Fails 3+ examples.
- OR only returns a running mean instead of median.

### 0-19 — Failed
- Function body still `pass`.
- OR raises on empty list.

## Deductions
- −5 hit max_iter=20
- −3 dispreferred tool

## Bonuses
- +2 minimum turn count
- +2 exact match to one of the two reference implementations
