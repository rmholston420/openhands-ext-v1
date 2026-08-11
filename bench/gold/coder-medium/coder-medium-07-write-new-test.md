# coder-medium-07-write-new-test

## Task summary
Read an existing utility function and write a new pytest test file that exercises three cases: empty input, single element, and multiple elements.

## Expected tool-call transcript
1. `read_file("/workspace/repo/src/stats.py")` — inspect the function under test.
2. `write_file("/workspace/repo/tests/test_stats.py", ...)` — create new test file with three test functions.

## Expected file state after diff (test file)
```python
/workspace/repo/tests/test_stats.py:
from stats import mean


def test_mean_empty():
    assert mean([]) == 0


def test_mean_single():
    assert mean([42]) == 42


def test_mean_multiple():
    assert mean([1, 2, 3, 4]) == 2.5
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Uses `read_file` then `write_file`; test file contains exactly 3 tests covering empty/single/multiple; imports `mean` from `stats`; each test uses `assert` |
| 70-89 | 3 tests present but assertion values wrong for one case, or import path uses `src.stats` (may or may not work depending on PYTHONPATH — acceptable variation) |
| 40-69 | Only 2 tests written, OR uses `str_replace_editor` on a nonexistent file (should be write_file for new files) |
| 10-39 | Test file created but tests reference wrong function name or introduce syntax errors |
| 0-9 | No test file written, or file contains no `def test_` functions |

## Notes
Tests write_file selection for new files (str_replace_editor is for existing files). Also tests test-authoring quality — three specific cases were requested; models that write only one or two lose points.
