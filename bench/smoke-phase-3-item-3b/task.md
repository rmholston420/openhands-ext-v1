# Phase 3 Sign-Off Item 3.b Probe — MCP §2.2 Reachability

## Scope

Spec `integration-execution-plan-v16.md` §2.2 defines only the
**install pattern** for Forge-OH MCP servers via supergateway proxy:

```bash
supergateway --stdio "npx @modelcontextprotocol/server-filesystem /" --port 8080
```

The specific MCP servers described by the plan are added in later phases:

- Phase 5 — GPU Telemetry as an MCP Server
- Phase 6 — Inference Backend Health + Episodic Memory as MCP Servers
- Phase 7 — RepoGraph: Neo4j + MCP Server + Canvas Panel

Phase 3's line 378 "verify MCP tools from §2.2 are callable" therefore
has no concrete servers to bind to at this point in the sequence,
because Phases 5-7 have not been executed.

## Interpretation

This probe treats item 3.b as **vacuously satisfied at Phase 3** and
converts it into a Phase-5-onwards prerequisites report:

- Are the toolchain prereqs (`npx`, `supergateway`, `uvx`) present on
  the box so Phases 5-7 won't be blocked on install-pattern surprises?
- Does `config/agent.py` currently wire any MCP config? (Expected: no.)
- Does the SDK expose the MCP surface Phases 5-7 will need?
- Do any shipped subagent presets already carry `mcp_servers`
  frontmatter? (`web-researcher` does — informational only.)

No live tool-list call is made because there is nothing to call yet.

## Pass criteria

- Probe runs without error.
- Verdict clearly reports zero §2.2 servers exist at Phase 3.
- Toolchain-prereq status is recorded so Phase-5-onwards work sees a
  green board.

## Deferred to Phases 5-7

- Actual `supergateway`-fronted server smoke.
- SDK `list_tools` against a live proxy.
- Round-trip tool call via `TaskAction` → subagent using a Phase-5+
  MCP server.
