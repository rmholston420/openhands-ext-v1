# Phase 2 — Suite-Wide Configuration

**Spec:** `docs/specs/integration-execution-plan-v16.md` § Phase 2.
**Status:** 2.1 · 2.2 · 2.3 implemented 2026-08-11 07:18 EDT (this file). 2.4 explicitly untouched until Phase 0.3 concludes. 2.5 deferred to Phase 3+.

## 2.1 Deployment mode selection

Three modes; pick by task shape.

| Mode | Command | When to use | Constraint |
|---|---|---|---|
| TUI | `openhands` | Interactive human-in-the-loop | Interactive only |
| Headless | `openhands --headless -t "..."` | Scoped one-shot / CI | Always `always-approve`; `--llm-approve` unavailable — must explicitly acknowledge before invocation (see wrapper) |
| Serve (Canvas) | `openhands serve --gpu` | Full visual workspace | Docker required |

Reserve headless/CI automation for low-risk, well-scoped tasks only (spec §2.1). This repo does not encode an allowlist — the human invoker must acknowledge each headless run via the wrapper's `--acknowledge-low-risk` flag. This is deliberate: an automated allowlist would either be too permissive (grep-only) or too restrictive (require task metadata that doesn't exist yet).

**Wrapper:** `scripts/openhands-mode.sh <tui|headless|serve> [args]` (this repo).

- Verifies DockerWorkspace-only preconditions before dispatch (relies on Phase 1 grep policy per ADR-0002).
- For `headless`, requires `--acknowledge-low-risk` as a bare flag before the task string.
- For `serve`, verifies Docker daemon reachable before invoking.
- Fails loud with an install command if `openhands` CLI is not on `PATH`.

## 2.2 MCP servers via proxy, not direct stdio

Install pattern for every Forge-OH MCP server (Phases 5–7):

```bash
supergateway --stdio "npx @modelcontextprotocol/server-filesystem <root>" --port <port>
```

**No MCP servers ship in Phase 2.2.** This phase reserves the port range and locks the pattern. Concrete MCP servers land in Phases 5–7 and MUST use this template.

**Port range:** `8110–8199` — see [`docs/MCP_PORT_ALLOCATION.md`](MCP_PORT_ALLOCATION.md).

**Prereq (not installed by this repo; document only):**

```bash
npm install -g supergateway
# or as a per-repo dev dep once Phase 5 lands package.json
```

**Template:** `scripts/mcp-supergateway.sh` (this repo).

- Takes `--name`, `--port`, `--stdio-cmd` args.
- Validates `--port` is within 8110–8199.
- Fails loud if `supergateway` is not on `PATH`.
- Backgrounds the process and writes pid to `/tmp/mcp-<name>.pid`.
- Refuses to run if the port is already in use.

## 2.3 Skills captured retroactively

Convention: after completing a workflow that could be automated, capture the pattern as an OpenHands skill.

```
/skill-creator Create a skill for automating this workflow in the future
```

Storage:

| Location | Purpose | Scope |
|---|---|---|
| `<repo>/.agents/skills/` | Shared across all users of this repo | Committed |
| `~/.agents/skills/` | Personal / cross-repo | Not committed |

**This repo creates:** `.agents/skills/README.md` documenting the retroactive-capture workflow and file naming convention. No actual skills ship in Phase 2.3 — they arrive retroactively during Phases 3+.

## 2.4 Tiered multi-LLM routing

**DO NOT EDIT.** Populated only after Phase 0.3 concludes with winning model + endpoint per role. See spec §2.4 for the frozen template.

## 2.5 Delegation model per task shape

Deferred to Phase 3+. See spec §2.5 for the trigger (Full-tier GPU-embedder winner, coder+planner concurrent VRAM audit).

## Files added by Phase 2.1–2.3

- `docs/PHASE-2-CONFIG.md` (this file)
- `docs/MCP_PORT_ALLOCATION.md`
- `scripts/openhands-mode.sh`
- `scripts/mcp-supergateway.sh`
- `.agents/skills/README.md`
- `.agents/skills/.gitkeep`
- `adrs/ADR-0019-phase-2-mcp-port-range-and-mode-wrapper.md`
