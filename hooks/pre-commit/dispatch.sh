#!/usr/bin/env bash
# hooks/pre-commit/dispatch.sh
#
# Runs all pre-commit checks in sequence. Each check exits non-zero on
# violation; the dispatcher fails on the first failure and reports which
# check failed.
#
# Add new checks by appending them to the CHECKS array. Order matters: cheapest
# checks first so common failures fail fast.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Checks in execution order.
CHECKS=(
  "hooks/pre-commit/size-guard.sh"
  "hooks/pre-commit/no-localworkspace.sh"
)

for check in "${CHECKS[@]}"; do
  if [ ! -x "$check" ] && [ ! -f "$check" ]; then
    echo "pre-commit dispatch: missing check $check" >&2
    exit 1
  fi
  if ! bash "$check"; then
    echo "pre-commit dispatch: check failed — $check" >&2
    exit 1
  fi
done

exit 0
