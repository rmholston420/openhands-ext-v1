#!/usr/bin/env bash
# scripts/session-end.sh
#
# Enforces ADR-0003 session-end discipline on Colossus:
#   - If the tree is clean and local == origin/main, no-op (already synced).
#   - If the tree has changes, prompts for a commit message and commits.
#   - Pushes to origin/main. The pre-push hook (no-diverged-remote.sh) will
#     block if the remote advanced.
#   - Verifies remote received the commit (SHA match).
#
# Usage:
#   bash scripts/session-end.sh                       # interactive commit message
#   bash scripts/session-end.sh -m "commit message"   # non-interactive
#   COMMIT_MSG="..." bash scripts/session-end.sh      # env var form

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

echo "===================================================================="
echo "openhands-ext-v1 session end — $(date -Iseconds)"
echo "===================================================================="

COMMIT_MSG_ARG=""
if [ "${1:-}" = "-m" ] && [ -n "${2:-}" ]; then
  COMMIT_MSG_ARG="$2"
elif [ -n "${COMMIT_MSG:-}" ]; then
  COMMIT_MSG_ARG="$COMMIT_MSG"
fi

# 1. Show what would be committed
if [ -n "$(git status --porcelain)" ]; then
  echo "--- changes to commit ---"
  git status --short
  echo ""

  if [ -z "$COMMIT_MSG_ARG" ]; then
    read -r -p "commit message (empty to abort): " COMMIT_MSG_ARG
    if [ -z "$COMMIT_MSG_ARG" ]; then
      echo "aborted — no commit message provided"
      exit 1
    fi
  fi

  git add -A
  git commit -m "$COMMIT_MSG_ARG

on-colossus"
  echo "[ok] committed: $(git rev-parse HEAD)"
else
  echo "[ok] working tree clean — nothing to commit"
fi

# 2. Fetch and check divergence before push
git fetch --quiet origin main
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse origin/main)"

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  echo "[ok] local HEAD == origin/main — nothing to push"
  exit 0
fi

if ! git merge-base --is-ancestor "$REMOTE_SHA" "$LOCAL_SHA"; then
  echo ""
  echo "FAIL — origin/main has advanced. Rebase before pushing:"
  echo "    git pull --rebase origin main"
  exit 1
fi

# 3. Push
echo ""
echo "--- pushing to origin/main ---"
git push origin main

# 4. Verify
git fetch --quiet origin main
PUSHED_SHA="$(git rev-parse origin/main)"
if [ "$LOCAL_SHA" = "$PUSHED_SHA" ]; then
  echo "[ok] pushed — origin/main == $PUSHED_SHA"
else
  echo "FAIL — push completed but remote SHA mismatch (local=$LOCAL_SHA, remote=$PUSHED_SHA)"
  exit 1
fi

echo ""
echo "===================================================================="
echo "session end complete."
echo "===================================================================="
