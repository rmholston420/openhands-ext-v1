#!/usr/bin/env bash
# scripts/install-oh-sdk.sh
#
# Installs the OpenHands SDK stack (openhands-sdk, openhands-tools,
# openhands-workspace, openhands-agent-server) into the project-local venv.
#
# Per spec §-1.1 and VERSIONS.lock: re-fetch the latest PyPI versions live
# rather than pinning from cache. Log the fetched versions to a per-run file
# in bench/results/ (created if absent) so the actual versions used are
# recoverable later.
#
# Log: /tmp/openhands-ext-v1-install-oh-sdk-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-install-oh-sdk-$(date +%s).log"
VENV_PY="$REPO_ROOT/.venv/bin/python"
VENV_PIP="$VENV_PY -m pip"

if [ ! -x "$VENV_PY" ]; then
  echo "FAIL: venv missing at $REPO_ROOT/.venv — run scripts/bootstrap-venv.sh first" >&2
  exit 1
fi

{
  echo "===== install-oh-sdk start — $(date -Iseconds) ====="
  echo "venv: $VENV_PY"

  echo ""
  echo "--- re-fetching PyPI versions ---"
  declare -A VERS
  for pkg in openhands-sdk openhands-tools openhands-workspace openhands-agent-server; do
    v="$(curl -sf https://pypi.org/pypi/$pkg/json | jq -r '.info.version')"
    if [ -z "$v" ] || [ "$v" = "null" ]; then
      echo "FAIL: could not fetch PyPI version for $pkg" >&2
      exit 1
    fi
    VERS[$pkg]="$v"
    echo "  $pkg == $v"
  done

  echo ""
  echo "--- pip install pinned versions ---"
  $VENV_PIP install --upgrade \
    "openhands-sdk==${VERS[openhands-sdk]}" \
    "openhands-tools==${VERS[openhands-tools]}" \
    "openhands-workspace==${VERS[openhands-workspace]}" \
    "openhands-agent-server==${VERS[openhands-agent-server]}"

  echo ""
  echo "--- installed versions (pip show) ---"
  for pkg in openhands-sdk openhands-tools openhands-workspace openhands-agent-server; do
    $VENV_PIP show "$pkg" 2>/dev/null | grep -E '^(Name|Version|Location):'
    echo "  ---"
  done

  echo ""
  echo "--- import sanity ---"
  $VENV_PY -c "
import openhands
print('openhands module:', openhands.__file__ if hasattr(openhands, '__file__') else '(namespace)')
try:
    import openhands.sdk as sdk
    print('openhands.sdk:', getattr(sdk, '__version__', 'unknown'))
except ImportError as e:
    print('sdk import warning:', e)
try:
    import openhands.tools as tools
    print('openhands.tools ok')
except ImportError as e:
    print('tools import warning:', e)
"

  # Record actuals for Phase 0.0c Category 7 metadata
  mkdir -p bench/results
  METADATA_FILE="bench/results/phase-neg-1-oh-sdk-$(date -u +%Y%m%dT%H%M%SZ).json"
  cat > "$METADATA_FILE" <<JSON
{
  "phase": "-1",
  "component": "openhands-sdk-stack",
  "fetched_at_utc": "$(date -u -Iseconds)",
  "source": "pypi.org live",
  "versions": {
    "openhands-sdk":         "${VERS[openhands-sdk]}",
    "openhands-tools":       "${VERS[openhands-tools]}",
    "openhands-workspace":   "${VERS[openhands-workspace]}",
    "openhands-agent-server": "${VERS[openhands-agent-server]}"
  }
}
JSON
  echo ""
  echo "recorded metadata: $METADATA_FILE"

  echo ""
  echo "===== install-oh-sdk done — $(date -Iseconds) ====="
} 2>&1 | tee "$LOG"
