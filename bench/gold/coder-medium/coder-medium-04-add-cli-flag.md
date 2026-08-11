# coder-medium-04-add-cli-flag

## Task summary
Add a new `--verbose` boolean CLI flag to an existing argparse-based script. Requires understanding argparse patterns and inserting the flag definition without disturbing existing flags.

## Expected tool-call transcript
1. `read_file("/workspace/repo/scripts/report.py")` — inspect current argparse setup.
2. `str_replace_editor` — insert `parser.add_argument("--verbose", action="store_true", help="Enable verbose output")` after the existing last `add_argument` call.

## Expected file state after diff (relevant section)
```python
parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True, help="Input file path")
parser.add_argument("--output", required=True, help="Output file path")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
args = parser.parse_args()
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Flag added via `str_replace_editor` after existing flags; uses `action="store_true"`; has help text; existing flags unchanged |
| 70-89 | Flag added but placed before existing flags or missing help text; existing flags preserved |
| 40-69 | Uses `write_file`; final state correct; loses partial-edit discipline |
| 10-39 | Flag added but uses `type=bool` (incorrect argparse pattern) or existing flag was altered |
| 0-9 | Flag not added, script broken, or wrong file |

## Notes
Tests understanding of argparse idioms — `action="store_true"` vs. the common `type=bool` mistake. Also tests insertion-point discipline in an existing block of similar statements.
