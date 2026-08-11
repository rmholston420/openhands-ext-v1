#!/usr/bin/env bash
# hooks/pre-push/no-diverged-remote.sh
#
# Enforces ADR-0003's hard sync discipline: rejects a push if origin has
# advanced beyond the local branch's known upstream tip. Forces an explicit
# `git pull --rebase` (or manual reconciliation) rather than allowing silent
# fast-forward-then-force divergence between Colossus and the Perplexity
# authoring surface.
#
# This hook is called by `git push` with the remote name and URL as arguments
# and the (local_ref local_sha remote_ref remote_sha) tuples on stdin.
#
# Exit codes:
#   0 — remote has not advanced; push may proceed
#   1 — remote has commits we don't have; push blocked

set -euo pipefail

REMOTE_NAME="${1:-origin}"

# Only enforce for main. Other refs (tags, feature branches if we ever have any)
# fall through.
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
if [ "$BRANCH" != "main" ]; then
  exit 0
fi

# Fetch the remote tip without merging.
git fetch --quiet "$REMOTE_NAME" main 2>/dev/null || {
  echo "pre-push: warning — could not fetch $REMOTE_NAME/main (offline?). Allowing push." >&2
  exit 0
}

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "$REMOTE_NAME/main" 2>/dev/null || echo '')"

if [ -z "$REMOTE_SHA" ]; then
  # No remote branch yet — first push. Allow.
  exit 0
fi

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  # No local commits ahead. `git push` will be a no-op; allow.
  exit 0
fi

# Is REMOTE_SHA an ancestor of LOCAL_SHA? If yes, fast-forward push is safe.
if git merge-base --is-ancestor "$REMOTE_SHA" "$LOCAL_SHA"; then
  exit 0
fi

echo "========================================================================"
echo "PRE-PUSH FAILURE — remote $REMOTE_NAME/main has advanced (ADR-0003)"
echo "Local HEAD:  $LOCAL_SHA"
echo "Remote HEAD: $REMOTE_SHA"
echo "------------------------------------------------------------------------"
echo "The remote has commits your local branch does not. Reconcile before"
echo "pushing to prevent divergence between Colossus and Perplexity author state:"
echo ""
echo "    git pull --rebase origin main"
echo ""
echo "Review any conflicts, then re-run your push."
echo "========================================================================"
echo "To bypass (NOT RECOMMENDED), re-run with: git push --no-verify"
exit 1
