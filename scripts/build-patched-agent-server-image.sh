#!/usr/bin/env bash
# scripts/build-patched-agent-server-image.sh
#
# Build the ADR-0035 overlay agent-server image that applies the ADR-0034
# openhands-sdk patch inside the DockerWorkspace container. Idempotent:
# reuses an existing tag when the patch hash is unchanged.
#
# Output: prints the resolved image tag on stdout (last line), so callers can
# capture it with `IMAGE=$(scripts/build-patched-agent-server-image.sh)`.
#
# Log: /tmp/openhands-ext-v1-build-patched-agent-server-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-build-patched-agent-server-$(date +%s).log"
PATCH_FILE="$REPO_ROOT/patches/openhands-sdk-llm-discriminated-union.patch"
VENDOR_TREE="$REPO_ROOT/vendor/openhands-sdk/openhands-sdk"
DOCKERFILE="$REPO_ROOT/docker/agent-server-patched/Dockerfile"

BASE_IMAGE="${BASE_IMAGE:-ghcr.io/openhands/agent-server:latest-python}"
IMAGE_REPO="${IMAGE_REPO:-openhands-ext-v1/agent-server-patched}"

# Log to file; mirror status lines to stderr so stdout stays clean for the tag.
exec 3>>"$LOG"
log() { echo "$@" | tee -a "$LOG" >&2; }

if [ ! -f "$PATCH_FILE" ]; then
  log "FAIL: patch file missing at $PATCH_FILE"
  exit 1
fi

# Content-addressed tag: 12-char hash of the patch file. Any change to the
# patch produces a new tag, so stale caches cannot silently serve unpatched
# behavior.
PATCH_HASH="$(sha256sum "$PATCH_FILE" | awk '{print substr($1,1,12)}')"
TAG="${IMAGE_REPO}:${PATCH_HASH}"

log "=== build-patched-agent-server-image — $(date -Iseconds) ==="
log "BASE_IMAGE=$BASE_IMAGE"
log "TAG=$TAG"
log "PATCH_FILE=$PATCH_FILE"
log "VENDOR_TREE=$VENDOR_TREE"
log "LOG=$LOG"

# Idempotence: skip build when the tag already exists locally.
if docker image inspect "$TAG" >/dev/null 2>&1; then
  log "--- tag already present locally; skipping build ---"
  echo "$TAG"
  exit 0
fi

# Ensure vendor tree is present and fresh. `vendor/` is category-2 regenerable
# (ADR-0003) and gitignored; regenerate via the tracked vendor script.
if [ ! -d "$VENDOR_TREE" ]; then
  log "--- vendor tree missing; running scripts/vendor-openhands-sdk.sh ---"
  bash "$REPO_ROOT/scripts/vendor-openhands-sdk.sh" >>"$LOG" 2>&1
fi

if [ ! -d "$VENDOR_TREE" ]; then
  log "FAIL: vendor tree still missing at $VENDOR_TREE after vendor script"
  exit 1
fi

# Pre-pull the base image so `docker build` doesn't race with the network on
# first run. Silent no-op if already local.
log "--- docker pull $BASE_IMAGE ---"
docker pull "$BASE_IMAGE" >>"$LOG" 2>&1 || {
  log "WARN: docker pull failed; falling back to local base image if present"
}

log "--- docker build $TAG ---"
docker build \
  --file "$DOCKERFILE" \
  --build-arg "BASE_IMAGE=$BASE_IMAGE" \
  --tag "$TAG" \
  "$REPO_ROOT" >>"$LOG" 2>&1

log "--- build complete; tag=$TAG ---"
echo "$TAG"
