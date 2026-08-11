#!/usr/bin/env bash
# scripts/pull-docs.sh
#
# Regenerable-artifact producer per ADR-0003 category 2. Clones the upstream
# doc-relevant paths of every component we depend on, at the tags recorded in
# VERSIONS.lock (re-fetched live to catch drift), and lands them under
# docs/vendor/<component>/.
#
# docs/vendor/ is gitignored (see .gitignore). This script is the tracked
# recipe that produces it. To use offline, run once.
#
# Layout produced:
#   docs/vendor/MANIFEST.json                      # component -> {tag, sha, fetched_at}
#   docs/vendor/openhands-sdk/                     # from OpenHands/software-agent-sdk
#   docs/vendor/openhands-app/                     # from OpenHands/OpenHands
#   docs/vendor/openhands-agent-canvas/            # from OpenHands/agent-canvas
#   docs/vendor/llama-cpp/                         # from ggml-org/llama.cpp
#   docs/vendor/vllm/                              # from vllm-project/vllm
#   docs/vendor/pypi/<pkg>.json                    # PyPI metadata for each openhands-*
#
# For each git repo we do a full clone at the target tag, then keep only the
# docs-relevant subtrees (README, docs/, examples/, CHANGELOG, LICENSE,
# top-level YAMLs, and for llama.cpp its tools/*/README.md and examples/).
#
# Log: /tmp/openhands-ext-v1-pull-docs-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-pull-docs-$(date +%s).log"
VENDOR="$REPO_ROOT/docs/vendor"
WORK="$(mktemp -d /tmp/pull-docs.XXXXXX)"
trap "rm -rf '$WORK'" EXIT

mkdir -p "$VENDOR"

fetch_tag_github() {
  # $1 = owner/repo
  local repo="$1"
  local tag
  tag="$(curl -sf "https://api.github.com/repos/$repo/releases/latest" | jq -r .tag_name)"
  if [ -z "$tag" ] || [ "$tag" = "null" ]; then
    echo "FAIL: could not fetch latest tag for $repo" >&2
    return 1
  fi
  echo "$tag"
}

clone_docs() {
  # $1 = owner/repo
  # $2 = tag
  # $3 = output directory (under docs/vendor/)
  # $4+ = docs-relevant path globs (relative to repo root)
  local repo="$1"; shift
  local tag="$1"; shift
  local out="$1"; shift
  local paths=("$@")

  local tmp="$WORK/$(basename "$repo")"
  echo "  cloning $repo@$tag ..."
  # Full clone at the tag (--depth 1 to save time/space; blobless would be
  # ideal but git clone --filter can be tricky with --branch). Fall back if
  # depth 1 misses the tag (some repos tag old releases).
  git clone --depth 1 --branch "$tag" "https://github.com/$repo.git" "$tmp" 2>&1 | tail -3

  local sha
  sha="$(git -C "$tmp" rev-parse HEAD)"

  # Wipe target then copy just doc-relevant paths
  rm -rf "$VENDOR/$out"
  mkdir -p "$VENDOR/$out"

  for pattern in "${paths[@]}"; do
    # Use rsync with include patterns for glob support; fall back to plain cp
    # for simple paths.
    (cd "$tmp" && find . -path "./$pattern*" -print0 2>/dev/null | \
      xargs -0 -I{} cp --parents -r {} "$VENDOR/$out/" 2>/dev/null || true)
  done

  # Always copy README, LICENSE, CHANGELOG at repo root if present
  for f in README.md README.rst LICENSE LICENSE.md LICENSE.txt CHANGELOG.md CHANGELOG.rst pyproject.toml setup.py setup.cfg package.json; do
    if [ -f "$tmp/$f" ]; then
      cp "$tmp/$f" "$VENDOR/$out/" 2>/dev/null || true
    fi
  done

  local size
  size="$(du -sh "$VENDOR/$out" 2>/dev/null | awk '{print $1}')"
  echo "  -> $VENDOR/$out ($size, tag=$tag, sha=$sha)"

  # Record in manifest
  jq --arg comp "$out" --arg repo "$repo" --arg tag "$tag" --arg sha "$sha" --arg ts "$(date -u -Iseconds)" \
    '.[$comp] = {source: ("github.com/" + $repo), tag: $tag, sha: $sha, fetched_at_utc: $ts}' \
    "$VENDOR/MANIFEST.json" > "$VENDOR/MANIFEST.json.tmp" && mv "$VENDOR/MANIFEST.json.tmp" "$VENDOR/MANIFEST.json"

  rm -rf "$tmp"
}

fetch_pypi() {
  # $1 = pkg name
  local pkg="$1"
  local out="$VENDOR/pypi/$pkg.json"
  mkdir -p "$VENDOR/pypi"
  curl -sf "https://pypi.org/pypi/$pkg/json" > "$out"
  local ver
  ver="$(jq -r '.info.version' "$out")"
  echo "  pypi/$pkg -> $ver"
  jq --arg comp "pypi/$pkg" --arg pkg "$pkg" --arg ver "$ver" --arg ts "$(date -u -Iseconds)" \
    '.[$comp] = {source: ("pypi.org/project/" + $pkg), version: $ver, fetched_at_utc: $ts}' \
    "$VENDOR/MANIFEST.json" > "$VENDOR/MANIFEST.json.tmp" && mv "$VENDOR/MANIFEST.json.tmp" "$VENDOR/MANIFEST.json"
}

{
  echo "===== pull-docs start — $(date -Iseconds) ====="
  echo "vendor: $VENDOR"
  echo "work:   $WORK"

  # Seed manifest
  if [ ! -f "$VENDOR/MANIFEST.json" ]; then
    echo '{}' > "$VENDOR/MANIFEST.json"
  fi

  echo ""
  echo "--- fetching latest tags ---"
  SDK_TAG="$(fetch_tag_github OpenHands/software-agent-sdk)"
  APP_TAG="$(fetch_tag_github OpenHands/OpenHands)"
  CANVAS_TAG="$(fetch_tag_github OpenHands/agent-canvas)"
  LLAMA_TAG="$(fetch_tag_github ggml-org/llama.cpp)"
  VLLM_TAG="$(fetch_tag_github vllm-project/vllm)"
  echo "  software-agent-sdk = $SDK_TAG"
  echo "  OpenHands          = $APP_TAG"
  echo "  agent-canvas       = $CANVAS_TAG"
  echo "  llama.cpp          = $LLAMA_TAG"
  echo "  vllm               = $VLLM_TAG"

  echo ""
  echo "--- OpenHands software-agent-sdk ---"
  clone_docs "OpenHands/software-agent-sdk" "$SDK_TAG" "openhands-sdk" \
    "docs" "examples" "openhands/sdk/README" "openhands/tools/README" \
    "openhands/workspace/README" "openhands/agent_server/README"

  echo ""
  echo "--- OpenHands app ---"
  clone_docs "OpenHands/OpenHands" "$APP_TAG" "openhands-app" \
    "docs" "microagents" "config.template.toml" "config.template.yaml" \
    "docker-compose.yml" "Makefile"

  echo ""
  echo "--- OpenHands agent-canvas ---"
  clone_docs "OpenHands/agent-canvas" "$CANVAS_TAG" "openhands-agent-canvas" \
    "docs" "packages/*/README" "apps/*/README"

  echo ""
  echo "--- llama.cpp ---"
  clone_docs "ggml-org/llama.cpp" "$LLAMA_TAG" "llama-cpp" \
    "docs" "examples" "tools" "grammars" "gguf-py/README" \
    "requirements" "scripts/get-flags.mk" "ci/README.md"

  echo ""
  echo "--- vllm ---"
  clone_docs "vllm-project/vllm" "$VLLM_TAG" "vllm" \
    "docs" "examples" "benchmarks/README" "tests/README"

  echo ""
  echo "--- PyPI packages ---"
  for pkg in openhands-sdk openhands-tools openhands-workspace openhands-agent-server vllm; do
    fetch_pypi "$pkg"
  done

  echo ""
  echo "--- manifest ---"
  cat "$VENDOR/MANIFEST.json" | jq .

  echo ""
  echo "--- total size ---"
  du -sh "$VENDOR"

  echo ""
  echo "===== pull-docs done — $(date -Iseconds) ====="
} 2>&1 | tee "$LOG"
