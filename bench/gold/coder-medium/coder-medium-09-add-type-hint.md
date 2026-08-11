# coder-medium-09-add-type-hint

## Task summary
Add a return type hint `-> dict[str, int]` to an existing function that lacks one. The function body must not be modified. The function currently returns a dict mapping strings to counts.

## Expected tool-call transcript
1. `read_file("/workspace/repo/src/counter.py")` — inspect current signature.
2. `str_replace_editor` — modify signature `def count_words(text: str):` → `def count_words(text: str) -> dict[str, int]:`.

## Expected file state after diff (relevant lines)
```python
def count_words(text: str) -> dict[str, int]:
    counts = {}
    for word in text.split():
        counts[word] = counts.get(word, 0) + 1
    return counts
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Uses `str_replace_editor` on the signature line only; return type is `dict[str, int]`; function body byte-identical |
| 70-89 | Return type added but uses older syntax `Dict[str, int]` (requires `from typing import Dict` import that agent may or may not add) — acceptable minor variation |
| 40-69 | Uses `write_file` to rewrite the module; final state correct on signature |
| 10-39 | Type hint added but body was reformatted or a docstring inserted (out of scope) |
| 0-9 | Signature unchanged, or type hint incorrect (e.g. `-> dict` without parameters) |

## Notes
Tests minimal-edit discipline on a one-line change. The `dict[str, int]` (lowercase, PEP 585) vs `Dict[str, int]` (typing module) distinction is a modern-Python signal — both are acceptable, but the modern form scores slightly higher.
