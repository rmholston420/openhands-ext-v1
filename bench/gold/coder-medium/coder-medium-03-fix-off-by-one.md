# coder-medium-03-fix-off-by-one

## Task summary
Diagnose and fix an off-by-one bug in a bounded loop. Requires reading the file, identifying the loop bound is wrong, and using `str_replace_editor` to correct it.

## Expected tool-call transcript
1. `read_file("/workspace/repo/src/pagination.py")` — inspect current logic.
2. `str_replace_editor` — replace `range(len(items) - 1)` with `range(len(items))` in the `page_items` function.

## Expected file state after diff
```python
/workspace/repo/src/pagination.py:
"""Pagination helper."""


def page_items(items: list, page_size: int) -> list[list]:
    """Chunk items into pages of size page_size."""
    pages = []
    for i in range(0, len(items), page_size):
        pages.append(items[i:i + page_size])
    return pages
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Uses `read_file` then `str_replace_editor`; final `range()` call matches expected exactly; loop structure preserved; no bash |
| 70-89 | Bug fixed but implementation rewritten (e.g. list comprehension) — behavior correct but exceeds task scope |
| 40-69 | Uses `write_file` for full rewrite; final state correct |
| 10-39 | Off-by-one fixed but a new bug introduced (e.g. `page_size + 1`) or unrelated code touched |
| 0-9 | Bug not fixed, file unchanged, or file corrupted |

## Notes
Tests localized bug fixing — the fix is a single-token change in a range expression. Rewrites or list-comprehension refactors solve the problem but signal weaker minimal-edit discipline.
