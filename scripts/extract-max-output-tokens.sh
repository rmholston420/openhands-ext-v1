#!/usr/bin/env bash
# scripts/extract-max-output-tokens.sh
#
# Extract measured max_output_tokens from Phase 0.3 bench JSON and write to
# config/max-output-tokens.json (provenance-tracked).
#
# Per ADR-0033 + spec §2.4: max_output_tokens must be measured, not assumed.
# Reads:
#   Coder   — ~/.forge-oh/bench_coder_full_multi_turn/*_run/*awq*.json (ADR-0029)
#   Planner — ~/.forge-oh/bench_planner_medium_migration_probe/*_run/*27b*.json
#              (ADR-0025)
#
# Definition: max_output_tokens := max(output_tokens) observed across all
# scored bench cells for the winning model. This is the empirical ceiling
# the model hit under Phase 0.3 conditions, not a theoretical spec-sheet
# claim.
#
# Output shape:
# {
#   "coder": {
#     "value": <int>,
#     "source": "<path-to-source-json>",
#     "measured_at": "<ISO-8601 UTC of this script run>"
#   },
#   "planner": {...}
# }

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

OUT="$REPO_ROOT/config/max-output-tokens.json"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

CODER_BENCH_ROOT="${CODER_BENCH_ROOT:-$HOME/.forge-oh/bench_coder_full_multi_turn}"
PLANNER_BENCH_ROOT="${PLANNER_BENCH_ROOT:-$HOME/.forge-oh/bench_planner_medium_migration_probe}"

if ! command -v jq >/dev/null 2>&1; then
  echo "FAIL: jq is required" >&2
  exit 1
fi

extract_max() {
  local root="$1"; local pattern="$2"; local role="$3"
  if [ ! -d "$root" ]; then
    echo "FAIL[$role]: bench root not found: $root" >&2
    exit 1
  fi
  # Find latest _run/ dir with matching model files
  local run_dir
  run_dir="$(find "$root" -maxdepth 1 -type d -name "*_run" | sort | tail -1)"
  if [ -z "$run_dir" ]; then
    echo "FAIL[$role]: no *_run directory under $root" >&2
    exit 1
  fi
  # shellcheck disable=SC2086
  local files
  files="$(find "$run_dir" -maxdepth 1 -type f -name "*.json" | grep -Ei "$pattern" || true)"
  if [ -z "$files" ]; then
    echo "FAIL[$role]: no bench files matching /$pattern/ under $run_dir" >&2
    exit 1
  fi
  # Compute max(output_tokens) across all matching files' results[]
  local max_tokens=0
  local source_file=""
  while IFS= read -r f; do
    local m
    m="$(jq '[.results[]?.output_tokens // 0] | max // 0' "$f" 2>/dev/null || echo 0)"
    if [ "$m" -gt "$max_tokens" ]; then
      max_tokens="$m"
      source_file="$f"
    fi
  done <<< "$files"
  if [ "$max_tokens" -le 0 ]; then
    echo "FAIL[$role]: no output_tokens found in any of: $files" >&2
    exit 1
  fi
  # Emit JSON fragment
  jq -n \
    --argjson v "$max_tokens" \
    --arg src "$source_file" \
    --arg t "$NOW" \
    '{value: $v, source: $src, measured_at: $t}'
}

CODER_FRAG="$(extract_max "$CODER_BENCH_ROOT" "awq|coder-30b" "coder")"
PLANNER_FRAG="$(extract_max "$PLANNER_BENCH_ROOT" "27b|q6k|q6_k" "planner")"

jq -n \
  --argjson coder "$CODER_FRAG" \
  --argjson planner "$PLANNER_FRAG" \
  '{coder: $coder, planner: $planner}' > "$OUT"

echo "OK — wrote $OUT"
cat "$OUT"
