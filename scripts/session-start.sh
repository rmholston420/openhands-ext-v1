#!/usr/bin/env bash
# scripts/session-start.sh
#
# Enforces ADR-0003 session-start discipline on Colossus:
#   - Fetches origin/main.
#   - Refuses to proceed if the working tree is dirty.
#   - Refuses to proceed if origin/main has diverged from local.
#   - Fast-forwards (or reports mismatch) so local HEAD = origin/main.
#   - Re-installs hooks (idempotent — protects against forgotten install).
#   - Prints SESSION_HANDOFF.md and the tail of BUILD_LOG.md so context is
#     visible before any work starts.
#
# Never modifies files outside .git/hooks or logs to stdout. Safe to re-run.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

echo "===================================================================="
echo "openhands-ext-v1 session start — $(date -Iseconds)"
echo "repo:  $REPO_ROOT"
echo "branch: $(git rev-parse --abbrev-ref HEAD)"
echo "===================================================================="

# 1. Dirty tree check
if [ -n "$(git status --porcelain)" ]; then
  echo ""
  echo "FAIL — working tree is dirty. Commit or stash before session start."
  echo ""
  git status --short
  exit 1
fi
echo "[ok] working tree clean"

# 2. Fetch and divergence check
git fetch --quiet origin main
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse origin/main)"

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  echo "[ok] local HEAD == origin/main ($LOCAL_SHA)"
elif git merge-base --is-ancestor "$LOCAL_SHA" "$REMOTE_SHA"; then
  echo "[info] origin/main is ahead — fast-forwarding"
  git merge --ff-only origin/main
  echo "[ok] fast-forwarded to $(git rev-parse HEAD)"
elif git merge-base --is-ancestor "$REMOTE_SHA" "$LOCAL_SHA"; then
  echo "[info] local is ahead of origin/main — remember to push at session end"
else
  echo ""
  echo "FAIL — local and remote have diverged. Reconcile manually:"
  echo "    git log --oneline --graph --all -20"
  echo "    git pull --rebase origin main"
  exit 1
fi

# 3. Re-install hooks (idempotent)
if [ -x "scripts/install-hooks.sh" ]; then
  echo ""
  echo "--- installing hooks ---"
  bash scripts/install-hooks.sh
fi

# 4. Print SESSION_HANDOFF.md
echo ""
echo "--- SESSION_HANDOFF.md ---"
if [ -f SESSION_HANDOFF.md ]; then
  cat SESSION_HANDOFF.md
else
  echo "(SESSION_HANDOFF.md not present)"
fi

# 5. Tail last N BUILD_LOG entries
N=5
echo ""
echo "--- BUILD_LOG.md (last $N entries) ---"
if [ -f BUILD_LOG.md ]; then
  awk -v n="$N" '/^## /{c++; if(c>0) entries[c]=""} c>0 {entries[c]=entries[c] $0 "\n"} END{start=(c>n?c-n+1:1); for(i=start;i<=c;i++) printf "%s", entries[i]}' BUILD_LOG.md
else
  echo "(BUILD_LOG.md not present)"
fi

echo ""
echo "===================================================================="
echo "session ready. Run scripts/session-end.sh when you finish."
echo "===================================================================="
