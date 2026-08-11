# mcp-servers/ — Ported MCP Servers

Each subdirectory wraps one Forge-OH service as a standalone Model Context Protocol
server, exposed through `supergateway --stdio "..." --port <n>` per spec §2.2. This is
the install pattern for every Forge-OH MCP server (Phases 5-7).

| Directory | Phase | Source | Status |
|---|---|---|---|
| `gpu-monitor/` | 5 | `Forge-OH/bff/services/gpu_monitor.py` | scaffold (empty) |
| `inference-backends/` | 6 | `Forge-OH/bff/services/inference_backends/` | scaffold (empty) |
| `episodic-memory/` | 6 | `Forge-OH/bff/services/episodic_memory.py` | scaffold (empty) |
| `repograph/` | 7 | `Forge-OH/openhands_tools_ext/repograph/{index,parser,store}.py` | scaffold (empty) |

Each server will be populated during its owning phase after Phase 0.3 concludes and the
winning runtime is known. See `PORTING_LEDGER.md` for per-file source SHAs.
