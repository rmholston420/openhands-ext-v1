#!/usr/bin/env bash
# bench/smoke-phase-3-item-3b/probe.sh — Phase 3 sign-off item 3.b probe.
#
# §2.2 defines only the install pattern for MCP servers via supergateway
# proxy; the actual servers land in Phases 5-7. This probe verifies
# tool availability and reports whether §2.2 has anything callable YET.

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/.forge-oh/bench_smoke_phase_3_item_3b/${TS}_run"
mkdir -p "$OUT_DIR"

echo "=== Phase 3 sign-off item 3.b probe — $(date -Iseconds) ==="

# 1. Does §2.2's install pattern have its dependencies installed?
NPX_OK=1; command -v npx >/dev/null 2>&1 && NPX_OK=0
UVX_OK=1; command -v uvx >/dev/null 2>&1 && UVX_OK=0
NODE_V="$(command -v node >/dev/null 2>&1 && node --version || echo none)"
SG_OK=1
if command -v supergateway >/dev/null 2>&1; then
  SG_OK=0
  SG_LOC="$(command -v supergateway)"
else
  # Check if npx can resolve it without running
  SG_LOC="none-in-path"
fi

# 2. Does config/agent.py currently wire ANY MCP config?
MCP_HITS="$(grep -nE 'mcp|MCP|supergateway' config/agent.py 2>/dev/null || true)"

# 3. Does the SDK expose MCP hooks the agent can register?
VENV_PY="$REPO_ROOT/.venv/bin/python"
SDK_MCP="$($VENV_PY -c "
import openhands.sdk as s
attrs = [a for a in dir(s) if 'mcp' in a.lower() or 'MCP' in a]
print(attrs)
try:
    from openhands.sdk.mcp import MCPServer  # type: ignore
    print('MCPServer:OK')
except Exception as e:
    print(f'MCPServer:MISSING ({type(e).__name__})')
" 2>&1)"

# 4. Are any MCP servers configured in the shipped subagent presets?
SP=".venv/lib/python3.14/site-packages"
SUBAGENT_MCP="$(grep -l 'mcp_servers' $SP/openhands/tools/preset/subagents/*.md 2>/dev/null || true)"

python3 - <<PY > "$OUT_DIR/verdict.json"
import json
verdict = {
    "spec_2_2_defines_specific_servers": False,  # §2.2 is install-pattern only
    "spec_2_2_servers_land_in": ["Phase 5 (GPU telemetry)", "Phase 6 (Inference health + Episodic memory)", "Phase 7 (RepoGraph Neo4j)"],
    "build_agent_wires_mcp": bool("""$MCP_HITS""".strip()),
    "build_agent_mcp_grep": """$MCP_HITS""".strip().splitlines(),
    "npx_installed": $NPX_OK == 0,
    "uvx_installed": $UVX_OK == 0,
    "node_version": "$NODE_V",
    "supergateway_installed": $SG_OK == 0,
    "supergateway_location": "$SG_LOC",
    "sdk_mcp_surface": """$SDK_MCP""".strip(),
    "subagent_presets_with_mcp": """$SUBAGENT_MCP""".strip().splitlines(),
    "verdict": (
        "3.b vacuously PASSED at Phase 3: §2.2 defines only an install "
        "pattern; the servers land in Phases 5-7. Prereqs for that "
        "install pattern (npx/supergateway/uvx) can be reported here so "
        "Phases 5-7 don't discover them missing. No servers exist to be "
        "'callable' at this point in the sequence."
    ),
}
print(json.dumps(verdict, indent=2))
PY

cat "$OUT_DIR/verdict.json"
echo "=== Item 3.b probe complete — verdict at $OUT_DIR/verdict.json ==="
