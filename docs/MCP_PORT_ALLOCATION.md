# MCP Port Allocation

**Spec:** § Phase 2.2 (install pattern) · § Phases 5–7 (concrete MCP servers).
**Ratified:** ADR-0019 (2026-08-11).

Reserved range for all supergateway-proxied MCP servers in this repo:

## Reserved: 8110–8199

## Occupied host ports (do not reassign)

| Port | Owner | Role | Source |
|---|---|---|---|
| 8000 | OpenHands agent (default) | agent-server | OpenHands default; may be reallocated when Phase 1 lands DockerWorkspace-only container |
| 8001 | OpenHands frontend (default) | Node/Canvas frontend | OpenHands default |
| 8082 | llama.cpp | planner (qwen3_6-35b-a3b-q4kxl-gguf) | ADR-0017 |
| 8090 | llama.cpp | embedder (qwen3-embedding-4b-q8-gguf, CPU) | ADR-0017 amendment #3 |
| 8100 | vLLM | coder (qwen3-coder-30b-a3b-instruct-awq-4bit) | ADR-0017 amendment #2 |

## MCP allocation (8110–8199)

Each Phase 5–7 MCP server MUST take a port from this range and record it here on first launch. Format: append a row; never renumber existing rows.

| Port | Phase | Server name | stdio command | Status |
|---|---|---|---|---|
| 8110 | 5 (reserved) | — | — | reserved |
| 8111 | 5 (reserved) | — | — | reserved |
| … | … | … | … | … |
| 8199 | — | — | — | reserved |

_Rows 8112–8198 collapsed for readability; use any unassigned port in the range._

## Rules

1. **All MCP servers use supergateway proxy** (spec §2.2). Never launch an MCP server on direct stdio to the agent — supergateway is the only supported transport.
2. **Port bind failures MUST be loud.** No silent fallback to an alternative port. `scripts/mcp-supergateway.sh` enforces this.
3. **When adding a server:** append a row to the allocation table BEFORE the first launch. First-launch script may fail otherwise (nothing enforces this at code level; discipline only).
4. **When retiring a server:** mark `status=retired` and record retirement date in the row. Do not delete rows; do not renumber.
5. **Never allocate outside 8110–8199** without amending this file + adding an ADR.

## Collision check pattern

Before starting any MCP server:

```bash
ss -tln "sport = :$PORT" | grep -q LISTEN && { echo "port $PORT in use"; ss -tln "sport = :$PORT"; exit 1; }
```

`scripts/mcp-supergateway.sh` runs this check automatically.
