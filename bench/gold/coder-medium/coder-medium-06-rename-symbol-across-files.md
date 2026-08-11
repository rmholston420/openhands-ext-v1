# coder-medium-06-rename-symbol-across-files

## Task summary
Rename a function `compute_total` to `calculate_total` across two files — its definition in `math_ops.py` and its call site in `main.py`. Requires reading both files and editing both.

## Expected tool-call transcript
1. `read_file("/workspace/repo/src/math_ops.py")` — inspect definition site.
2. `read_file("/workspace/repo/src/main.py")` — inspect call site.
3. `str_replace_editor` on `math_ops.py` — rename definition `def compute_total(` → `def calculate_total(`.
4. `str_replace_editor` on `main.py` — rename call `compute_total(` → `calculate_total(`.

## Expected file state after diff

`math_ops.py`:
```python
def calculate_total(items: list[int]) -> int:
    return sum(items)
```

`main.py`:
```python
from math_ops import calculate_total

print(calculate_total([1, 2, 3]))
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Both files read and edited via `str_replace_editor`; both call and definition renamed; import statement in main.py also updated; no bash |
| 70-89 | Rename complete but only 3 tool calls (skipped one read) or minor extras (unnecessary re-reads); final state correct |
| 40-69 | Uses `execute_bash sed -i` for cross-file rename; final state correct but non-surgical |
| 10-39 | Only one file renamed (call OR definition, not both) — broken code |
| 0-9 | Neither file modified, or rename introduces syntax errors |

## Notes
Tests multi-file coordination. The import statement in `main.py` is a subtle detail — models that miss it will leave main.py broken.
