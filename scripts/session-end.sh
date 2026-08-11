#!/usr/bin/env bash
# scripts/session-end.sh
#
# Enforces ADR-0003 session-end discipline on Colossus:
#
#   - If the tree is clean and local == origin/main, no-op.
#   - If the tree has changes, prompts (or reads -m / $COMMIT_MSG) for a
#     commit message and commits with a body marker.
#   - Pushes to origin/main. The pre-push hook (no-diverged-remote.sh) will
#     block if the remote advanced.
#   - Verifies remote received the commit (SHA match).
#
# SMOKE-TEST TRUTH GATE (ADR-0003 amendment, filed 2026-08-11):
#
#   If EITHER of the two Phase -1 smoke-test JSONs
#     bench/results/phase-neg-1-smoke-llama-cpp-*.json
#     bench/results/phase-neg-1-smoke-vllm-*.json
#   is (a) missing entirely, or (b) present but does not have
#   `status == "pass"` in its most recent file, then a commit subject
#   containing the phrases "all green", "verification table green",
#   "green", or "phase -1 complete" is REJECTED. Use an honest subject like
#   "phase(-1) partial: llama.cpp built; vllm failed OOM" instead.
#
#   This gate exists because commit 535bc35 was marked "§-1 Verification
#   table all green" when both smoke tests had failed. Truth in commit
#   messages is now enforced, not merely encouraged.
#
# Usage:
#   bash scripts/session-end.sh                       # interactive
#   bash scripts/session-end.sh -m "commit message"   # non-interactive
#   COMMIT_MSG="..." bash scripts/session-end.sh      # env var form
#   ALLOW_GREEN_OVERRIDE=1 bash ...                   # bypass the gate;
#                                                     # requires human ack
#                                                     # of what failed

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

# --- smoke-test truth summary ---
smoke_status() {
  # $1 = component key ("llama-cpp" or "vllm")
  local pattern="bench/results/phase-neg-1-smoke-$1-*.json"
  local latest
  latest="$(ls -1t $pattern 2>/dev/null | head -1)"
  if [ -z "$latest" ]; then
    echo "missing"
    return
  fi
  local st
  st="$(jq -r '.status // "missing_field"' "$latest" 2>/dev/null)"
  echo "$st"
}

LLAMA_STATUS="$(smoke_status llama-cpp)"
VLLM_STATUS="$(smoke_status vllm)"

echo ""
echo "--- smoke-test truth ---"
printf '  llama.cpp smoke: %s\n' "$LLAMA_STATUS"
printf '  vllm smoke:      %s\n' "$VLLM_STATUS"

SMOKES_ALL_GREEN=0
if [ "$LLAMA_STATUS" = "pass" ] && [ "$VLLM_STATUS" = "pass" ]; then
  SMOKES_ALL_GREEN=1
fi

# --- gate: reject false "green" claims ---
if [ -n "$COMMIT_MSG_ARG" ] && [ "$SMOKES_ALL_GREEN" -ne 1 ] && [ "${ALLOW_GREEN_OVERRIDE:-0}" != "1" ]; then
  case "${COMMIT_MSG_ARG,,}" in
    *"all green"*|*"verification table green"*|*"phase -1 complete"*|*"phase(-1) complete"*|*"§-1"*green*|*"§-1"*"complete"*)
      echo "" >&2
      echo "FAIL: commit subject claims 'green' / 'complete' but the two Phase -1 smoke tests are:" >&2
      echo "   llama.cpp smoke: $LLAMA_STATUS" >&2
      echo "   vllm smoke:      $VLLM_STATUS" >&2
      echo "" >&2
      echo "Use an honest subject, or set ALLOW_GREEN_OVERRIDE=1 to bypass (not recommended)." >&2
      exit 1
      ;;
  esac
fi

# 1. Show what would be committed
if [ -n "$(git status --porcelain)" ]; then
  echo ""
  echo "--- changes to commit ---"
  git status --short
  echo ""

  if [ -z "$COMMIT_MSG_ARG" ]; then
    read -r -p "commit message (empty to abort): " COMMIT_MSG_ARG
    if [ -z "$COMMIT_MSG_ARG" ]; then
      echo "aborted — no commit message provided"
      exit 1
    fi
    # Re-check gate against interactively-entered message
    if [ "$SMOKES_ALL_GREEN" -ne 1 ] && [ "${ALLOW_GREEN_OVERRIDE:-0}" != "1" ]; then
      case "${COMMIT_MSG_ARG,,}" in
        *"all green"*|*"verification table green"*|*"phase -1 complete"*|*"phase(-1) complete"*|*"§-1"*green*|*"§-1"*"complete"*)
          echo "FAIL: gate — smokes are llama=$LLAMA_STATUS vllm=$VLLM_STATUS" >&2
          exit 1
          ;;
      esac
    fi
  fi

  git add -A
  git commit -m "$COMMIT_MSG_ARG

on-colossus
smoke.llama-cpp: $LLAMA_STATUS
smoke.vllm:      $VLLM_STATUS"
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
