#!/usr/bin/env bash
# scripts/install-hooks.sh
#
# Installs the openhands-ext-v1 git hooks into .git/hooks/.
# Idempotent — safe to re-run on every session start.
#
# Installs:
#   - pre-commit: hooks/pre-commit/dispatch.sh
#       which chains:
#         - hooks/pre-commit/size-guard.sh          (ADR-0003)
#         - hooks/pre-commit/no-localworkspace.sh   (ADR-0002)
#   - pre-push:   hooks/pre-push/no-diverged-remote.sh   (ADR-0003)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

install_hook() {
  local src="$1"
  local dest="$2"

  if [ ! -f "$src" ]; then
    echo "ERROR: source $src not found" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$dest")"

  if [ -f "$dest" ] && ! cmp -s "$src" "$dest"; then
    local backup="$dest.backup.$(date +%s)"
    echo "existing $(basename "$dest") differs — backing up to $backup"
    cp "$dest" "$backup"
  fi

  cp "$src" "$dest"
  chmod +x "$dest"
  echo "installed $(basename "$dest") -> $dest"
}

# Ensure source hooks are executable in the working tree too.
chmod +x hooks/pre-commit/*.sh hooks/pre-push/*.sh 2>/dev/null || true

install_hook "hooks/pre-commit/dispatch.sh"       ".git/hooks/pre-commit"
install_hook "hooks/pre-push/no-diverged-remote.sh" ".git/hooks/pre-push"

echo ""
echo "verifying pre-commit dispatcher against the working tree..."
if bash hooks/pre-commit/dispatch.sh; then
  echo "pre-commit dispatch self-check passed."
else
  echo "pre-commit dispatch self-check FAILED — investigate before committing." >&2
  exit 1
fi

echo ""
echo "hooks installed. Sync discipline (ADR-0003) is active."
