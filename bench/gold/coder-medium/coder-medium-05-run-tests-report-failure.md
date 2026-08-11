# coder-medium-05-run-tests-report-failure

## Task summary
Run the project's test suite via bash, capture output, and report the count of failed tests along with the name of the first failing test. Do not modify any files.

## Expected tool-call transcript
1. `execute_bash("cd /workspace/repo && pytest -x --tb=no -q")` — run pytest with fast-fail and quiet output.
2. (No file modifications.)

## Expected agent report format
The agent's final message should contain the substring `1 failed` (from the pytest summary line) and identify the failing test as `test_multiply` (or `tests/test_math.py::test_multiply` with the path prefix).

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Single `execute_bash` invocation with a pytest command; correctly extracts and reports `1 failed` + `test_multiply` from the output |
| 70-89 | Correct `execute_bash` invocation but reports fail count incorrectly, or names the file (test_math.py) but not the specific test function |
| 40-69 | Uses `read_file` on test files first (unnecessary reads) then runs bash; reaches correct answer |
| 10-39 | Runs the wrong command (e.g. `python test_math.py` instead of pytest); output is partially correct or missing |
| 0-9 | No bash invocation, or reports the wrong test as failing |

## Notes
Tests bash-tool selection for a pure command-execution task where no file modification is needed. Also tests output-parsing to answer a specific factual question — "which test failed?" — from tool output.
