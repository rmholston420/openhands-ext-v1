#!/usr/bin/env bash
# scripts/openhands-mode.sh
#
# Phase 2.1 wrapper — verified dispatch to one of three OpenHands deployment
# modes. See docs/PHASE-2-CONFIG.md § 2.1.
#
# Modes:
#   tui                 -> openhands  (interactive; no wrapping needed but kept
#                                       here for a single entry point)
#   serve               -> openhands serve --gpu  (requires Docker daemon)
#   headless -t "..."   -> openhands --headless -t "..."
#                          MUST be preceded by --acknowledge-low-risk (per spec
#                          §2.1 "reserve headless/CI automation for low-risk,
#                          well-scoped tasks only")
#
# Common preflight:
#   1. `openhands` CLI must be on PATH.
#   2. Phase 1 policy (DockerWorkspace-only, ADR-0002) must not be violated by
#      environment (checked via existing pre-commit hook when files change; here
#      we only warn if OPENHANDS_WORKSPACE_TYPE is set to something other than
#      docker).
#
# Fails loud on any precondition miss.

set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage:
  scripts/openhands-mode.sh tui
  scripts/openhands-mode.sh serve [additional openhands serve args]
  scripts/openhands-mode.sh headless --acknowledge-low-risk -t "task description" [additional args]

See docs/PHASE-2-CONFIG.md § 2.1.
USAGE
  exit 2
}

_require_cli() {
  if ! command -v openhands >/dev/null 2>&1; then
    cat >&2 <<'EOF'
FAIL: `openhands` CLI not on PATH.

The Phase 2.1 wrapper requires the OpenHands CLI. This repo only installs the
PyPI SDK packages; the CLI is separate.

To install (choose one):

  # Option A — PyPI CLI (if published under this name):
  pip install openhands-cli

  # Option B — from software-agent-sdk monorepo (canonical):
  #   see https://github.com/OpenHands/software-agent-sdk

Then re-run this script.
EOF
    exit 127
  fi
}

_check_workspace_env() {
  # Phase 1 policy: DockerWorkspace only. If a user has manually set
  # OPENHANDS_WORKSPACE_TYPE to something else, warn but do not abort — the
  # ADR-0002 pre-commit hook already enforces this at commit time.
  local wtype="${OPENHANDS_WORKSPACE_TYPE:-}"
  if [ -n "$wtype" ] && [ "$wtype" != "docker" ] && [ "$wtype" != "DockerWorkspace" ]; then
    echo "WARN: OPENHANDS_WORKSPACE_TYPE=$wtype — Phase 1 requires DockerWorkspace only" >&2
    echo "      (see ADR-0002; not aborting because env may be legacy)" >&2
  fi
}

_check_docker_serve() {
  if ! docker info >/dev/null 2>&1; then
    cat >&2 <<'EOF'
FAIL: Docker daemon not reachable.

`openhands serve --gpu` requires Docker (spec §2.1). Start Docker and retry:
  sudo systemctl start docker
EOF
    exit 1
  fi
}

# --- dispatch ------------------------------------------------------------

MODE="${1:-}"
[ -z "$MODE" ] && usage
shift || true

case "$MODE" in
  tui)
    _require_cli
    _check_workspace_env
    exec openhands "$@"
    ;;

  serve)
    _require_cli
    _check_workspace_env
    _check_docker_serve
    exec openhands serve --gpu "$@"
    ;;

  headless)
    _require_cli
    _check_workspace_env
    # Require --acknowledge-low-risk as the FIRST positional after "headless".
    ACK="${1:-}"
    if [ "$ACK" != "--acknowledge-low-risk" ]; then
      cat >&2 <<'EOF'
FAIL: headless mode requires explicit --acknowledge-low-risk before task args.

Spec §2.1: "Reserve headless/CI automation for low-risk, well-scoped tasks only."

Invoke as:
  scripts/openhands-mode.sh headless --acknowledge-low-risk -t "task description"

The wrapper does not encode an allowlist — you the invoker are asserting the
task is low-risk. This is deliberate; automation to grep task intent is
premature until Phase 3+ delegates task-shape metadata.
EOF
      exit 2
    fi
    shift
    # openhands --headless implies --always-approve per spec §2.1 (--llm-approve unavailable)
    exec openhands --headless "$@"
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    echo "FAIL: unknown mode '$MODE'" >&2
    usage
    ;;
esac
