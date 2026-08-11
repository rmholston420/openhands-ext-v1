#!/usr/bin/env bash
# scripts/stop-large-model.sh
#
# Stop the currently-running large-model server (coder or planner). Used to
# enforce co-residency Option 2 per ADR-0017 — only one of {coder, planner}
# holds VRAM at a time. Never touches the embedder.
#
# Usage:
#   scripts/stop-large-model.sh coder     # stops vLLM on port 8100 (was 8000->8001->8100; amended ADR-0017 twice)
#   scripts/stop-large-model.sh planner   # stops llama-server on port 8082
#   scripts/stop-large-model.sh both      # stops both if either is up
#   scripts/stop-large-model.sh status    # print who is up

set -euo pipefail

CODER_PORT="8100"   # amended twice 2026-08-11 (ADR-0017): 8000->8001 06:10 EDT, 8001->8100 06:24 EDT; OpenHands holds 8000 (agent) + 8001 (node)
PLANNER_PORT="8082"
EMBEDDER_PORT="8090"

target="${1:-status}"

_port_listening() {
  ss -tln "sport = :$1" 2>/dev/null | grep -q LISTEN
}

_pids_on_port() {
  local port="$1"
  # Prefer ss for owning-pid; fall back to fuser.
  ss -tlnp "sport = :$port" 2>/dev/null | \
    grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true
  fuser -n tcp "$port" 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+$' | sort -u || true
}

_kill_port() {
  local port="$1"
  local label="$2"
  if ! _port_listening "$port"; then
    echo "  $label (port $port): not running"
    return 0
  fi
  local pids
  pids="$(_pids_on_port "$port" | sort -u | xargs || true)"
  if [ -z "$pids" ]; then
    echo "  $label (port $port): listener present but no owning pid — using fuser -k"
    fuser -k -TERM "-n" tcp "$port" 2>/dev/null || true
  else
    echo "  $label (port $port): killing pids $pids"
    for pid in $pids; do
      kill -TERM "$pid" 2>/dev/null || true
    done
  fi
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if ! _port_listening "$port"; then
      echo "  $label: stopped after ${i}s"
      return 0
    fi
    sleep 1
  done
  echo "  $label: TERM did not stop it; escalating to KILL"
  local pids2
  pids2="$(_pids_on_port "$port" | sort -u | xargs || true)"
  for pid in $pids2; do
    kill -KILL "$pid" 2>/dev/null || true
  done
  sleep 2
  if _port_listening "$port"; then
    echo "  $label: STILL LISTENING — manual intervention required" >&2
    return 1
  fi
  echo "  $label: stopped (KILL)"
}

case "$target" in
  status)
    echo "Large-model server status:"
    if _port_listening "$CODER_PORT"; then
      echo "  coder    (port $CODER_PORT): RUNNING"
    else
      echo "  coder    (port $CODER_PORT): stopped"
    fi
    if _port_listening "$PLANNER_PORT"; then
      echo "  planner  (port $PLANNER_PORT): RUNNING"
    else
      echo "  planner  (port $PLANNER_PORT): stopped"
    fi
    if _port_listening "$EMBEDDER_PORT"; then
      echo "  embedder (port $EMBEDDER_PORT): resident (always-on)"
    else
      echo "  embedder (port $EMBEDDER_PORT): NOT RUNNING (start with scripts/serve-embedder.sh)"
    fi
    ;;
  coder)
    echo "Stopping coder ..."
    _kill_port "$CODER_PORT" coder
    ;;
  planner)
    echo "Stopping planner ..."
    _kill_port "$PLANNER_PORT" planner
    ;;
  both)
    echo "Stopping both large-model servers ..."
    _kill_port "$CODER_PORT" coder || true
    _kill_port "$PLANNER_PORT" planner || true
    ;;
  *)
    echo "usage: $0 {coder|planner|both|status}" >&2
    exit 2
    ;;
esac
