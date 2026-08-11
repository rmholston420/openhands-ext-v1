# coder-medium-10-implement-from-docstring

## Task summary
Implement a function that has a complete docstring specifying its behavior but currently only contains `pass`. The docstring says the function must return the second-largest unique value in a list, or None if fewer than 2 unique values exist.

## Expected tool-call transcript
1. `read_file("/workspace/repo/src/algos.py")` — inspect the docstring.
2. `str_replace_editor` — replace `pass` with an implementation matching the spec.

## Expected file state after diff
```python
def second_largest_unique(values: list[int]) -> int | None:
    """Return the second-largest unique value in values.

    Args:
        values: A list of integers.

    Returns:
        The second-largest unique value, or None if fewer than
        two unique values exist.
    """
    unique = sorted(set(values), reverse=True)
    if len(unique) < 2:
        return None
    return unique[1]
```

## Expected behavior (test cases)
- `second_largest_unique([1, 2, 3, 4, 5])` → `4`
- `second_largest_unique([5, 5, 5])` → `None`
- `second_largest_unique([])` → `None`
- `second_largest_unique([3, 1, 4, 1, 5, 9, 2, 6])` → `6`
- `second_largest_unique([7])` → `None`

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Function implemented correctly; all 5 test cases pass when evaluated; docstring preserved; uses `str_replace_editor` |
| 70-89 | Implementation returns wrong value on the all-duplicates case (returns the single unique value instead of None) OR uses two-pass sorting with same result |
| 40-69 | Implementation returns wrong value on the empty-list case, OR the len<2 branch is missing (would raise IndexError) |
| 10-39 | Implementation returns the second element by position instead of second-largest unique (fundamental misread of spec) |
| 0-9 | `pass` unchanged, syntax error introduced, or docstring destroyed |

## Notes
Tests spec-reading and correct implementation of edge cases (empty, all-duplicates, single-element). The `set()` + sort approach is the canonical one; a two-pass max-then-max-excluding is equally acceptable. Failure mode to watch: models that miss the "unique" constraint and return the second-largest with duplicates counted.
