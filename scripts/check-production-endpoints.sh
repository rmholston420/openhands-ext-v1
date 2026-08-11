#!/usr/bin/env bash
# scripts/check-production-endpoints.sh
#
# Health-check the three production role endpoints declared in
# bench/candidates/production-selection.json (ADR-0017). For each role:
#   1. GET /v1/models  — confirm served_model_name matches ADR-0017.
#   2. Role-appropriate canary request:
#        coder    -> POST /v1/chat/completions with one tool-call harness question
#        planner  -> POST /v1/chat/completions with one short planning prompt
#        embedder -> POST /v1/embeddings with two short strings
#   3. Report per-role: status, latency_ms, output_tokens (chat) or vector_dim (embed).
#
# Usage:
#   scripts/check-production-endpoints.sh              # all three roles
#   scripts/check-production-endpoints.sh coder
#   scripts/check-production-endpoints.sh planner
#   scripts/check-production-endpoints.sh embedder
#
# Exit codes:
#   0 = all requested roles PASS
#   1 = one or more roles FAIL (details printed to stderr)
#   2 = misconfiguration (missing selection file, jq missing, etc.)
#
# Read-only. Never mutates config, never starts/stops servers.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

SELECTION_FILE="$REPO_ROOT/bench/candidates/production-selection.json"

if [ ! -f "$SELECTION_FILE" ]; then
  echo "FAIL: $SELECTION_FILE not found (ADR-0017 selection missing)" >&2
  exit 2
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "FAIL: jq not installed" >&2
  exit 2
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "FAIL: curl not installed" >&2
  exit 2
fi

_pretty_ok()   { printf "  \033[32mPASS\033[0m  %s\n" "$*"; }
_pretty_warn() { printf "  \033[33mWARN\033[0m  %s\n" "$*"; }
_pretty_fail() { printf "  \033[31mFAIL\033[0m  %s\n" "$*"; }

# Global exit tracker.
FAIL_COUNT=0

# ---- helpers ----

# _time_ms_curl <curl args...>  -> prints "http_code|body_bytes|elapsed_ms|body_temp_file"
_time_curl() {
  local tmp
  tmp="$(mktemp)"
  local start end elapsed_ms
  start="$(date +%s%N)"
  local http
  # -m 60 hard cap so a hung server can't wedge the check
  http="$(curl -sS -o "$tmp" -w '%{http_code}' -m 60 "$@" || echo 000)"
  end="$(date +%s%N)"
  elapsed_ms=$(( (end - start) / 1000000 ))
  local bytes
  bytes="$(wc -c < "$tmp")"
  printf "%s|%s|%s|%s" "$http" "$bytes" "$elapsed_ms" "$tmp"
}

# _check_models_endpoint <endpoint> <expected_name>
_check_models() {
  local endpoint="$1" expected="$2"
  local out http bytes ms body
  out="$(_time_curl -X GET "$endpoint/models")"
  IFS='|' read -r http bytes ms body <<<"$out"
  if [ "$http" != "200" ]; then
    _pretty_fail "/v1/models http=$http (${ms} ms)"
    if [ "$bytes" -gt 0 ] && [ "$bytes" -lt 500 ]; then
      sed 's/^/         /' "$body" >&2
    fi
    rm -f "$body"
    return 1
  fi
  local names
  names="$(jq -r '.data[].id // empty' "$body" 2>/dev/null | paste -sd, - || true)"
  rm -f "$body"
  if [ -z "$names" ]; then
    _pretty_fail "/v1/models returned no model ids (${ms} ms)"
    return 1
  fi
  if [[ ",$names," != *",$expected,"* ]]; then
    _pretty_warn "/v1/models registered [$names]; ADR-0017 expected [$expected] (${ms} ms)"
    return 2
  fi
  _pretty_ok "/v1/models registered [$expected] (${ms} ms)"
  return 0
}

# _check_chat <endpoint> <served_name> <role_label>
# Sends one small chat completion; reports latency and output token count.
_check_chat() {
  local endpoint="$1" served="$2" role="$3"
  local prompt
  case "$role" in
    coder)
      prompt='Reply with exactly one line: OK COLOSSUS CODER'
      ;;
    planner)
      prompt='Reply with exactly one line: OK COLOSSUS PLANNER'
      ;;
    *)
      prompt='Reply with exactly one line: OK'
      ;;
  esac
  local payload
  payload="$(jq -n --arg m "$served" --arg p "$prompt" '{
    model: $m,
    messages: [{role:"user", content:$p}],
    max_tokens: 32,
    temperature: 0.0
  }')"
  local out http bytes ms body
  out="$(_time_curl -X POST "$endpoint/chat/completions" \
    -H "Content-Type: application/json" \
    -d "$payload")"
  IFS='|' read -r http bytes ms body <<<"$out"
  if [ "$http" != "200" ]; then
    _pretty_fail "/v1/chat/completions http=$http (${ms} ms)"
    if [ "$bytes" -gt 0 ] && [ "$bytes" -lt 800 ]; then
      sed 's/^/         /' "$body" >&2
    fi
    rm -f "$body"
    return 1
  fi
  local content out_tokens
  content="$(jq -r '.choices[0].message.content // ""' "$body" 2>/dev/null | head -c 200)"
  out_tokens="$(jq -r '.usage.completion_tokens // "?"' "$body" 2>/dev/null)"
  rm -f "$body"
  if [ -z "$content" ]; then
    _pretty_fail "/v1/chat/completions returned empty content (${ms} ms)"
    return 1
  fi
  _pretty_ok "chat: ${ms} ms, out_tokens=${out_tokens}, reply=\"${content}\""
  return 0
}

# _check_embed <endpoint> <served_name>
# Sends two short strings; reports latency and vector dim.
_check_embed() {
  local endpoint="$1" served="$2"
  local payload
  payload="$(jq -n --arg m "$served" '{
    model: $m,
    input: ["Colossus RTX 5090 sanity check.", "OpenHands-Ext production embedder role."]
  }')"
  local out http bytes ms body
  out="$(_time_curl -X POST "$endpoint/embeddings" \
    -H "Content-Type: application/json" \
    -d "$payload")"
  IFS='|' read -r http bytes ms body <<<"$out"
  if [ "$http" != "200" ]; then
    _pretty_fail "/v1/embeddings http=$http (${ms} ms)"
    if [ "$bytes" -gt 0 ] && [ "$bytes" -lt 800 ]; then
      sed 's/^/         /' "$body" >&2
    fi
    rm -f "$body"
    return 1
  fi
  local count dim
  count="$(jq -r '.data | length' "$body" 2>/dev/null)"
  dim="$(jq -r '.data[0].embedding | length' "$body" 2>/dev/null)"
  rm -f "$body"
  if [ "$count" != "2" ]; then
    _pretty_fail "/v1/embeddings returned ${count} vectors (expected 2) (${ms} ms)"
    return 1
  fi
  if [ -z "$dim" ] || [ "$dim" = "null" ] || [ "$dim" -lt 32 ] 2>/dev/null; then
    _pretty_fail "/v1/embeddings vector dim=${dim} (implausibly small) (${ms} ms)"
    return 1
  fi
  _pretty_ok "embed: ${ms} ms, vectors=2, dim=${dim}"
  return 0
}

# _check_role <role_key>
_check_role() {
  local role="$1"
  local endpoint served label
  endpoint="$(jq -r --arg r "$role" '.roles[$r].endpoint // empty' "$SELECTION_FILE")"
  served="$(jq -r --arg r "$role" '.roles[$r].served_model_name // empty' "$SELECTION_FILE")"
  if [ -z "$endpoint" ] || [ -z "$served" ]; then
    _pretty_fail "role='$role' not present in $SELECTION_FILE"
    return 1
  fi
  echo ""
  echo "== role=$role endpoint=$endpoint served=$served =="
  local port
  port="$(echo "$endpoint" | sed -E 's|^https?://[^:/]+:([0-9]+)/.*$|\1|')"
  if ! ss -tln "sport = :$port" 2>/dev/null | grep -q LISTEN; then
    _pretty_fail "port $port not listening — start with scripts/serve-${role}.sh"
    return 1
  fi
  local rc_models=0 rc_probe=0
  _check_models "$endpoint" "$served" || rc_models=$?
  case "$role" in
    embedder) _check_embed "$endpoint" "$served" || rc_probe=$? ;;
    coder|planner) _check_chat "$endpoint" "$served" "$role" || rc_probe=$? ;;
  esac
  # WARN on model-name mismatch is not a hard fail if the probe still passed.
  if [ "$rc_models" -eq 1 ] || [ "$rc_probe" -eq 1 ]; then
    return 1
  fi
  return 0
}

# ---- main ----

REQUESTED="${1:-all}"
case "$REQUESTED" in
  all)    ROLES=(embedder coder planner) ;;
  coder|planner|embedder) ROLES=("$REQUESTED") ;;
  *)      echo "usage: $0 {all|coder|planner|embedder}" >&2; exit 2 ;;
esac

echo "===== check-production-endpoints — $(date -Iseconds) ====="
echo "selection: $SELECTION_FILE"
echo "roles:     ${ROLES[*]}"
echo ""
echo "-- server presence --"
bash "$REPO_ROOT/scripts/stop-large-model.sh" status || true

for role in "${ROLES[@]}"; do
  if ! _check_role "$role"; then
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

echo ""
echo "===== summary — $(date -Iseconds) ====="
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "ALL ROLES PASS"
  exit 0
fi
echo "$FAIL_COUNT role(s) FAILED" >&2
exit 1
