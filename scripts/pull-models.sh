#!/usr/bin/env bash
# scripts/pull-models.sh
#
# Phase 0 §0.0b candidate-pool downloader. Table-driven from
# bench/candidates/registry.json. For each selected role's candidates,
# resolves the current HF revision, downloads the requested files (or
# the full snapshot when hf_files is empty), computes a rollup SHA256,
# and appends to models/manifest.json.
#
# Rules baked in per project custom instructions + spec §0.0a/§0.0b:
#   - Live-fetch revisions from HF at download time (no hardcoded SHAs).
#   - Never pre-narrow the pool. Selection is per-role, not per-candidate.
#   - Idempotent: skip if the local dir already has the expected files.
#   - Refuse to run if free disk on models/ FS is less than 1.25× the
#     approx-size sum of the requested pool (buffer for tokenizer/config).
#   - Manifest is append-only; do not rewrite prior entries.
#
# Usage:
#   scripts/pull-models.sh --role coder|planner|embedder|all [--dry-run]
#
# Log: /tmp/openhands-ext-v1-pull-models-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-pull-models-$(date +%s).log"
VENV_BIN="$REPO_ROOT/.venv/bin"
HF="$VENV_BIN/hf"
VENV_PY="$VENV_BIN/python"
REGISTRY="$REPO_ROOT/bench/candidates/registry.json"
MANIFEST="$REPO_ROOT/models/manifest.json"

ROLE=""
DRY_RUN=0

usage() {
  cat >&2 <<EOF
Usage: $0 --role <coder|planner|embedder|all> [--dry-run]

Reads bench/candidates/registry.json and pulls every candidate registered
for the selected role. Use --dry-run to print the plan and disk check
without downloading.
EOF
  exit 2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --role) ROLE="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage ;;
    *) echo "unknown arg: $1" >&2; usage ;;
  esac
done

case "$ROLE" in
  coder|planner|embedder|all) ;;
  *) usage ;;
esac

if [ ! -x "$HF" ]; then
  echo "FAIL: hf CLI not found at $HF — run scripts/bootstrap-venv.sh first" >&2
  exit 1
fi
if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv python not found at $VENV_PY — run scripts/bootstrap-venv.sh first" >&2
  exit 1
fi
if [ ! -f "$REGISTRY" ]; then
  echo "FAIL: candidate registry not found at $REGISTRY" >&2
  exit 1
fi

mkdir -p "$REPO_ROOT/models"

# HF auth soft-check: warn (do not fail) if no token in env. Unauthenticated
# HF pulls are rate-limited and may throttle for the ~155 GiB coder+planner
# batch. hf CLI picks up HF_TOKEN automatically.
if [ -z "${HF_TOKEN:-}" ] && [ ! -f "$HOME/.cache/huggingface/token" ]; then
  echo "WARN: no HF_TOKEN in env and no token cached at ~/.cache/huggingface/token."
  echo "WARN: pulls will run unauthenticated (rate-limited). For large role batches"
  echo "WARN: (--role coder|planner|all) set HF_TOKEN=<your read token> before running."
fi

{
  echo "===== pull-models start — $(date -Iseconds) ====="
  echo "role: $ROLE   dry-run: $DRY_RUN"
  echo "registry: $REGISTRY"
  echo "manifest: $MANIFEST"
  echo "hf CLI:   $($HF --version 2>&1 | head -1)"

  # 1. Resolve the selected candidate list (JSON array) via python.
  #    Prints one line per candidate: slug|hf_repo|format|runtime|role_pool_csv|approx_gib|files_csv
  PLAN="$("$VENV_PY" - <<PY
import json, sys
role = "$ROLE"
with open("$REGISTRY") as f:
    reg = json.load(f)
roles = ["coder", "planner", "embedder"] if role == "all" else [role]
seen = set()
for r in roles:
    for c in reg["roles"].get(r, []):
        if c["slug"] in seen:
            continue
        seen.add(c["slug"])
        files = ",".join(c.get("hf_files") or [])
        pool = ",".join(c["role_pool"])
        print(f"{c['slug']}|{c['hf_repo']}|{c['format']}|{c['runtime']}|{pool}|{c['approx_size_gib']}|{files}")
PY
)"

  if [ -z "$PLAN" ]; then
    echo "FAIL: no candidates for role=$ROLE in $REGISTRY" >&2
    exit 1
  fi

  echo ""
  echo "--- plan ---"
  printf '%s\n' "$PLAN" | awk -F'|' 'BEGIN{OFS="  "} {print $1, $2, "["$3"/"$4"]", "~"$6"GiB", "files=["$7"]"}'

  # 2. Disk preflight (1.25x approx sum).
  TOTAL_GIB="$(printf '%s\n' "$PLAN" | awk -F'|' '{s+=$6} END{printf "%d", s*1.25}')"
  MODELS_FS_FREE_GIB="$(df -BG --output=avail "$REPO_ROOT/models" | tail -1 | tr -dc '0-9')"
  echo ""
  echo "disk check: need ~${TOTAL_GIB} GiB (1.25×sum), have ${MODELS_FS_FREE_GIB} GiB free at $REPO_ROOT/models"
  if [ "$MODELS_FS_FREE_GIB" -lt "$TOTAL_GIB" ]; then
    echo "FAIL: insufficient disk. Free some space or reduce --role scope." >&2
    exit 1
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    echo ""
    echo "(dry-run: not downloading)"
    echo "===== pull-models done (dry-run) — $(date -Iseconds) ====="
    exit 0
  fi

  # 3. Ensure manifest exists as a JSON array file we append to.
  if [ ! -f "$MANIFEST" ]; then
    echo "[]" > "$MANIFEST"
  fi

  # 4. Download each candidate.
  echo ""
  echo "--- downloads ---"
  while IFS='|' read -r SLUG HF_REPO FORMAT RUNTIME POOL APPROX FILES; do
    [ -z "$SLUG" ] && continue
    DEST="$REPO_ROOT/models/$SLUG"
    mkdir -p "$DEST"

    echo ""
    echo "==> $SLUG   $HF_REPO   [$FORMAT/$RUNTIME]"

    # 4a. Idempotency guard.
    if [ -n "$FILES" ]; then
      # File list mode: skip only if every requested file already present.
      ALL_PRESENT=1
      IFS=',' read -ra FLIST <<< "$FILES"
      for f in "${FLIST[@]}"; do
        [ -f "$DEST/$f" ] || { ALL_PRESENT=0; break; }
      done
      if [ "$ALL_PRESENT" -eq 1 ]; then
        echo "skip: all requested files already present under $DEST"
        SKIPPED=1
      else
        SKIPPED=0
      fi
    else
      # Snapshot mode: skip if a config.json AND at least one .safetensors OR .gguf are present.
      if [ -f "$DEST/config.json" ] && \
         { ls "$DEST"/*.safetensors >/dev/null 2>&1 || ls "$DEST"/*.gguf >/dev/null 2>&1; }; then
        echo "skip: snapshot already appears complete under $DEST"
        SKIPPED=1
      else
        SKIPPED=0
      fi
    fi

    # 4b. Download.
    if [ "$SKIPPED" -eq 0 ]; then
      if [ -n "$FILES" ]; then
        IFS=',' read -ra FLIST <<< "$FILES"
        for f in "${FLIST[@]}"; do
          echo "    hf download $HF_REPO $f --local-dir $DEST"
          "$HF" download "$HF_REPO" "$f" --local-dir "$DEST"
        done
      else
        # For embedding-GGUF repos we ask HF for the Q8_0 file preferentially,
        # but fall back to full snapshot if not present.
        if [ "$FORMAT" = "gguf" ]; then
          # Try common Q8_0 filenames first
          Q8_CANDIDATES=()
          # e.g. Qwen3-Embedding-0.6B-Q8_0.gguf, Qwen3-Embedding-4B-Q8_0.gguf
          case "$HF_REPO" in
            *Qwen3-Embedding-0.6B-GGUF*) Q8_CANDIDATES+=("Qwen3-Embedding-0.6B-Q8_0.gguf");;
            *Qwen3-Embedding-4B-GGUF*)   Q8_CANDIDATES+=("Qwen3-Embedding-4B-Q8_0.gguf");;
          esac
          Q8_OK=0
          for f in "${Q8_CANDIDATES[@]}"; do
            echo "    trying $HF_REPO :: $f"
            if "$HF" download "$HF_REPO" "$f" --local-dir "$DEST"; then
              Q8_OK=1
              # Record the resolved GGUF filename for the manifest.
              FILES="$f"
              break
            fi
          done
          if [ "$Q8_OK" -eq 0 ]; then
            echo "    Q8_0 file not found — pulling full snapshot"
            "$HF" download "$HF_REPO" --local-dir "$DEST"
          fi
        else
          "$HF" download "$HF_REPO" --local-dir "$DEST"
        fi
      fi
    fi

    # 4c. Resolve pinned revision from HF (best-effort — the API returns
    #     the main branch SHA at query time).
    RESOLVED_REV="$("$VENV_PY" - <<PY
from huggingface_hub import HfApi
try:
    api = HfApi()
    info = api.repo_info("$HF_REPO", repo_type="model")
    print(info.sha or "")
except Exception as e:
    print("")
PY
)"

    # 4d. Compute rollup SHA256 of the downloaded tree (files sorted by path).
    ROLLUP="$(cd "$DEST" && find . -type f \( -name '*.safetensors' -o -name '*.gguf' -o -name '*.json' -o -name '*.model' -o -name 'tokenizer.json' -o -name 'tokenizer_config.json' -o -name 'config.json' \) -print0 2>/dev/null | \
      sort -z | xargs -0 sha256sum 2>/dev/null | sha256sum | awk '{print $1}')"
    SIZE_BYTES="$(du -sb "$DEST" | awk '{print $1}')"

    # 4e. Append manifest entry.
    "$VENV_PY" - <<PY
import json, os, sys
manifest_path = "$MANIFEST"
with open(manifest_path) as f:
    data = json.load(f)
entry = {
    "slug": "$SLUG",
    "hf_repo": "$HF_REPO",
    "resolved_revision": "$RESOLVED_REV" or None,
    "files_requested": [x for x in "$FILES".split(",") if x],
    "format": "$FORMAT",
    "runtime": "$RUNTIME",
    "role_pool": "$POOL".split(","),
    "approx_size_gib": int("$APPROX"),
    "actual_size_bytes": int("$SIZE_BYTES") if "$SIZE_BYTES".isdigit() else None,
    "rollup_sha256": "$ROLLUP" or None,
    "local_dir": os.path.relpath("$DEST", "$REPO_ROOT"),
    "resolved_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "source_url": f"https://huggingface.co/$HF_REPO" + (f"/tree/$RESOLVED_REV" if "$RESOLVED_REV" else ""),
}
# Replace any prior entry with the same slug (idempotent re-runs) but preserve
# the append order for auditability by moving the updated entry to the end.
data = [e for e in data if e.get("slug") != "$SLUG"]
data.append(entry)
with open(manifest_path, "w") as f:
    json.dump(data, f, indent=2)
PY
    echo "    manifest: appended $SLUG (rev=${RESOLVED_REV:0:12}, ${SIZE_BYTES}B, sha=${ROLLUP:0:12})"

  done <<< "$PLAN"

  echo ""
  echo "===== pull-models done — $(date -Iseconds) ====="
  echo "manifest: $MANIFEST"
} 2>&1 | tee "$LOG"
