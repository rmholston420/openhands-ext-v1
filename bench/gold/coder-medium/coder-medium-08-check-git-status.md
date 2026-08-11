# coder-medium-08-check-git-status

## Task summary
Report which files are currently modified in the git working tree (staged or unstaged). Do not modify anything. Do not commit.

## Expected tool-call transcript
1. `execute_bash("cd /workspace/repo && git status --short")` — get concise status output.

## Expected agent report format
The agent's final message should list the two modified files: `src/main.py` (modified) and `README.md` (modified), based on the fixture git state which has both files with unstaged modifications.

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | Single `execute_bash` with `git status`; correctly identifies both `src/main.py` and `README.md` as modified |
| 70-89 | Correct `git status` but only reports one of the two files, or includes untracked files as "modified" (minor confusion) |
| 40-69 | Uses `git diff` or `git ls-files -m` instead of `git status --short` — reaches correct answer via different path |
| 10-39 | Uses `read_file` on individual files trying to detect modification — wrong approach even if correct answer |
| 0-9 | No bash invocation, or reports wrong files, or attempts to `git add` / `git commit` (was explicitly forbidden) |

## Notes
Tests bash-tool selection for a read-only git query. Also tests instruction adherence — "do not commit" is a negative constraint that some agents may violate.
