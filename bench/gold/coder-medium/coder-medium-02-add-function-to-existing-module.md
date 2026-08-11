# coder-medium-02-add-function-to-existing-module

## Task summary
Add a new function to an existing Python module without breaking the existing public surface. Requires reading the file, choosing an insertion point that keeps imports at top and public API grouped, and adding the new function with a docstring.

## Expected tool-call transcript
1. `read_file("/workspace/repo/src/utils/text.py")` — inspect current module structure.
2. `str_replace_editor` — insert new function `slugify(text: str) -> str` after the existing `normalize()` function; new function must include a one-line docstring.

## Expected file state after diff
```python
/workspace/repo/src/utils/text.py:
"""Text utilities."""


def normalize(s: str) -> str:
    """Strip and lowercase."""
    return s.strip().lower()


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    return "-".join(text.strip().lower().split())
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Uses `read_file` then `str_replace_editor` to insert; function has docstring; existing `normalize` unchanged; insertion after `normalize` (or logically grouped); implementation strips/lowers/replaces whitespace |
| 70-89 | Function added but placed at top of file (before existing functions) or missing docstring; existing surface preserved |
| 40-69 | Uses `write_file` (rewrites whole module); final state correct; loses partial-edit discipline |
| 10-39 | Function added but existing `normalize` was altered or import block was disturbed |
| 0-9 | Module broken (syntax error), function missing, or wrong file |

## Notes
Tests planning within a small refactor: choosing insertion point, keeping existing code untouched, preferring surgical edit over full rewrite. Slugify implementation details are not scored beyond "produces a URL-safe slug" — variations like using `re.sub` for non-alphanumerics are equally acceptable.
