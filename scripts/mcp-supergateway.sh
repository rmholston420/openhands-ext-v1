#!/usr/bin/env bash
# scripts/mcp-supergateway.sh
#
# Phase 2.2 template — launch an MCP server behind supergateway. See spec §2.2
# and docs/MCP_PORT_ALLOCATION.md.
#
# Usage:
#   scripts/mcp-supergateway.sh \
#     --name <server-name> \
#     --port <port-in-8110-8199> \
#     --stdio-cmd "<full stdio command>"
#
# Example:
#   scripts/mcp-supergateway.sh \
#     --name fs-root \
#     --port 8110 \
#     --stdio-cmd "npx @modelcontextprotocol/server-filesystem /"
#
# Behavior:
#   - Requires supergateway on PATH; fails loud with install command otherwise.
#   - Rejects port outside 8110-8199 (Phase 2.2 reserved range).
#   - Refuses to run if port is already in use.
#   - Backgrounds the process; writes pid to /tmp/mcp-<name>.pid.
#   - Logs stdout+stderr to /tmp/mcp-<name>.log.

set -euo pipefail

NAME=""
PORT=""
STDIO_CMD=""

while [ $# -gt 0 ]; do
  case "$1" in
    --name) NAME="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --stdio-cmd) STDIO_CMD="$2"; shift 2;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "FAIL: unknown arg '$1'" >&2
      exit 2
      ;;
  esac
done

if [ -z "$NAME" ] || [ -z "$PORT" ] || [ -z "$STDIO_CMD" ]; then
  echo "FAIL: --name, --port, and --stdio-cmd are all required" >&2
  echo "See: scripts/mcp-supergateway.sh --help" >&2
  exit 2
fi

# Port range gate (Phase 2.2 reserved range 8110-8199).
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 8110 ] || [ "$PORT" -gt 8199 ]; then
  echo "FAIL: port $PORT outside reserved MCP range 8110-8199" >&2
  echo "See docs/MCP_PORT_ALLOCATION.md" >&2
  exit 2
fi

# Prereq: supergateway CLI.
if ! command -v supergateway >/dev/null 2>&1; then
  cat >&2 <<'EOF'
FAIL: `supergateway` not on PATH.

Install (spec §2.2 prereq; not installed by this repo):

  npm install -g supergateway

Then re-run this script.
EOF
  exit 127
fi

# Port collision check.
if ss -tln "sport = :$PORT" | grep -q LISTEN; then
  echo "FAIL: port $PORT already in use" >&2
  ss -tln "sport = :$PORT" >&2
  exit 1
fi

PIDFILE="/tmp/mcp-${NAME}.pid"
LOGFILE="/tmp/mcp-${NAME}.log"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "FAIL: mcp server '$NAME' already running (pid $(cat "$PIDFILE"))" >&2
  exit 1
fi

echo "===== mcp-supergateway start — $(date -Iseconds) ====="
echo "name:      $NAME"
echo "port:      $PORT"
echo "stdio:     $STDIO_CMD"
echo "log:       $LOGFILE"
echo "pidfile:   $PIDFILE"

# shellcheck disable=SC2086
setsid supergateway --stdio "$STDIO_CMD" --port "$PORT" >"$LOGFILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PIDFILE"

# Confirm bind within 5s.
for i in $(seq 1 10); do
  if ss -tln "sport = :$PORT" | grep -q LISTEN; then
    echo "READY (pid $NEW_PID, port $PORT) after ${i}x500ms"
    exit 0
  fi
  sleep 0.5
done

echo "FAIL: supergateway did not bind port $PORT within 5s" >&2
echo "See $LOGFILE" >&2
kill "$NEW_PID" 2>/dev/null || true
rm -f "$PIDFILE"
exit 1
