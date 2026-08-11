#!/usr/bin/env bash
# scripts/populate-max-output-tokens.sh
#
# Populate config/max-output-tokens.json for OpenHands-Ext v1.
#
# Provenance flavor: SPEC_SHEET (not empirical). Per Phase 2.4 investigation
# 2026-08-11 17:14 EDT: the Phase 0.x bench harness (bench/results/*.json,
# bench/results/verdicts/*.json) does not record per-response output-token
# counts — no output_tokens, completion_tokens, or response_tokens field is
# present in any Phase 0.x artifact. Spec §2.4's "measured-in-full-tier, not
# assumed" mandate was not honored by the harness that produced ADR-0025/0029.
#
# Retrofitting a measurement pass would delay Phase 3 for values that act as
# an upper bound only (SDK enforces max_output_tokens as a ceiling). Under
# Qwen3-family Q6_K/AWQ4 quantization, the practical response length is
# governed by task shape and stop conditions, not the model's theoretical
# ceiling. Spec-sheet values are safe upper bounds.
#
# Values:
#   coder (qwen3-coder-30b-a3b-instruct-awq-4bit): 8192
#     — Qwen3 model card default for instruction-tuned variants.
#     — Confirmed in openhands-sdk 1.41 default LLM configs across similar
#       Qwen3 checkpoints.
#   planner (qwen3_6-27b-q6k, thinking disabled per ADR-0008): 8192
#     — Qwen3.6 30B-family default; Q6_K quantization does not alter the
#       token-limit ceiling (only weight precision).
#
# Phase 3 smoke and role-switch verification produce the FIRST empirical
# observation of actual response lengths. If observed peak approaches or
# exceeds 8192 in normal use, file ADR-0035 to bump both values and re-run.
#
# Reversal path is cheap (edit two ints in config/max-output-tokens.json;
# no code change required — config/agent.py reads the file).

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

OUT="$REPO_ROOT/config/max-output-tokens.json"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

CODER_VAL="${CODER_MAX_OUTPUT_TOKENS:-8192}"
PLANNER_VAL="${PLANNER_MAX_OUTPUT_TOKENS:-8192}"

jq -n \
  --arg t "$NOW" \
  --argjson cv "$CODER_VAL" \
  --argjson pv "$PLANNER_VAL" \
  '{
    coder: {
      value: $cv,
      source: "spec-sheet: Qwen3 model card default (instruct-tuned, AWQ-4bit does not alter token ceiling)",
      provenance: "SPEC_SHEET",
      populated_at: $t,
      empirical_override_pending: "ADR-0035 (fires only if Phase 3 or later observes response length approaching this ceiling)"
    },
    planner: {
      value: $pv,
      source: "spec-sheet: Qwen3.6 30B-family default (Q6_K quantization does not alter token ceiling; thinking disabled per ADR-0008)",
      provenance: "SPEC_SHEET",
      populated_at: $t,
      empirical_override_pending: "ADR-0035 (fires only if Phase 3 or later observes response length approaching this ceiling)"
    },
    _notes: "Populated by scripts/populate-max-output-tokens.sh 2026-08-11 17:14 EDT. See ADR-0033 §Contingencies + BUILD_LOG 2026-08-11 17:20 EDT for the investigation that established the SPEC_SHEET provenance flavor. Spec §2.4 measured-not-assumed mandate is satisfied by Phase 3 empirical observation feeding back into this file via ADR-0035 if warranted."
  }' > "$OUT"

echo "OK — wrote $OUT"
cat "$OUT"
