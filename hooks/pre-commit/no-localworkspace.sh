#!/usr/bin/env bash
# hooks/pre-commit/no-localworkspace.sh
#
# Enforces spec §Phase 1's zero-`LocalWorkspace` policy per ADR-0002.
# Fails the commit if any tracked file outside the allow-list mentions LocalWorkspace.
#
# Allow-list (paths where "LocalWorkspace" is legitimately quoted, not a code reference):
#   - docs/specs/**            (the v16 spec itself quotes the term)
#   - docs/donor-inventory.md
#   - docs/verification/**     (verification checklists quote spec Phase 1 verbatim)
#   - docs/BENCHMARK_UNPAUSE_GATES.md   (references the ADR-0002 policy by name)
#   - adrs/**                  (ADRs describe the decision, must quote the term)
#   - PORTING_LEDGER.md
#   - BUILD_LOG.md
#   - DEBUG_LOG.md
#   - KNOWN_ISSUES.md
#   - SESSION_HANDOFF.md
#   - hooks/pre-commit/no-localworkspace.sh   (this file)
#   - scripts/install-hooks.sh                (references the hook)
#   - **/test_*/**, **/tests/**, **/*.test.*, **/*_test.py   (test/example code)
#
# Behavior: exits 0 if no violations; exits 1 with the offending paths otherwise.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Only inspect files that would be committed (staged in index) or all tracked files
# when run manually. Default: staged files if any, else full tree.
if git diff --cached --name-only --diff-filter=ACMRT | grep -q .; then
  MODE="staged"
  FILES="$(git diff --cached --name-only --diff-filter=ACMRT)"
else
  MODE="full-tree"
  FILES="$(git ls-files)"
fi

# Allow-list regex — a file matching this is exempt.
ALLOW_RE='^(docs/specs/|docs/donor-inventory\.md$|docs/verification/|docs/BENCHMARK_UNPAUSE_GATES\.md$|adrs/|PORTING_LEDGER\.md$|BUILD_LOG\.md$|DEBUG_LOG\.md$|KNOWN_ISSUES\.md$|SESSION_HANDOFF\.md$|hooks/pre-commit/no-localworkspace\.sh$|hooks/pre-commit/dispatch\.sh$|hooks/pre-commit/size-guard\.sh$|hooks/pre-push/no-diverged-remote\.sh$|scripts/install-hooks\.sh$|scripts/session-start\.sh$|scripts/session-end\.sh$|.*/tests?/|.*\.test\.[a-z]+$|.*_test\.py$|.*/test_.*)'

VIOLATIONS=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ ! -f "$f" ] && continue
  if [[ "$f" =~ $ALLOW_RE ]]; then
    continue
  fi
  if grep -Iln 'LocalWorkspace' "$f" >/dev/null 2>&1; then
    hits="$(grep -In 'LocalWorkspace' "$f")"
    VIOLATIONS+="${f}:"$'\n'"${hits}"$'\n'
  fi
done <<< "$FILES"

if [ -n "$VIOLATIONS" ]; then
  echo "========================================================================"
  echo "PRE-COMMIT FAILURE — LocalWorkspace reference detected (mode: $MODE)"
  echo "See ADR-0002-localworkspace-guard-pre-commit.md and spec §Phase 1."
  echo "The following files mention LocalWorkspace outside the allow-list:"
  echo "------------------------------------------------------------------------"
  printf '%s\n' "$VIOLATIONS"
  echo "========================================================================"
  echo "To bypass this check (NOT RECOMMENDED), re-run with: git commit --no-verify"
  exit 1
fi

exit 0
