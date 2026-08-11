#!/usr/bin/env bash
# scripts/install-hooks.sh
#
# Installs the openhands-ext-v1 git hooks into .git/hooks/.
# Idempotent — safe to re-run on every session start.
#
# Currently installs:
#   - pre-commit: hooks/pre-commit/no-localworkspace.sh (ADR-0002)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

HOOK_SRC="hooks/pre-commit/no-localworkspace.sh"
HOOK_DEST=".git/hooks/pre-commit"

if [ ! -f "$HOOK_SRC" ]; then
  echo "ERROR: $HOOK_SRC not found" >&2
  exit 1
fi

mkdir -p .git/hooks

# If a pre-commit hook already exists and is different from ours, back it up.
if [ -f "$HOOK_DEST" ] && ! cmp -s "$HOOK_SRC" "$HOOK_DEST"; then
  echo "existing pre-commit hook differs — backing up to $HOOK_DEST.backup.$(date +%s)"
  cp "$HOOK_DEST" "$HOOK_DEST.backup.$(date +%s)"
fi

cp "$HOOK_SRC" "$HOOK_DEST"
chmod +x "$HOOK_DEST"

echo "installed pre-commit hook -> $HOOK_DEST"
echo "verifying by running the hook once against the working tree..."
"$HOOK_DEST" && echo "hook self-check passed."
