# Phase 3 Sign-Off Item 3.a Smoke — code-explorer Registration

Verifies that the `code-explorer` subagent (from `openhands.tools.preset.subagents/code_explorer.md`) is registered by `build_agent()` and reachable via the SDK's registered-agent lookup.

Satisfies ADR-0032 deferred DoD line item: "register `code-explorer` in the runtime tool registry alongside the router table; verify with a read-only investigation smoke test."

## Purpose

Prove:
1. `build_agent()` registers the `code-explorer` subagent by default (side-effect of `register_builtins_agents`).
2. The registered subagent's definition matches the shipped preset (name, tools list, constraint of read-only shell commands).
3. `TaskToolSet` (the delegation tool) is present in the agent's tool list — the mechanism by which the agent invokes subagents at runtime.

Rationale for offline verification: exercising a full delegate hand-off requires DockerWorkspace (sign-off item 3.c) and Agent Canvas (3.d). Item 3.a alone verifies REGISTRATION, which is the ADR-0032 DoD requirement.

## Pass criteria

- `build_agent()` returns without exception.
- The SDK's registered-agent list contains `"code-explorer"`.
- The `code-explorer` `AgentDefinition` has `tools == ["terminal"]` (as shipped in the preset markdown).
- The `Agent.tools` list contains a tool whose name matches `TaskToolSet.name`.
- Total wall time under 10 seconds (pure Python + registry lookup, no HTTP).

## Fail criteria

- `build_agent()` raises.
- `"code-explorer"` not in the registered-agent list.
- Subagent tools list drifted from `["terminal"]` (registration read a different file).
- `TaskToolSet.name` missing from `Agent.tools`.

## Deferred to later sign-off items

- Actually delegating a task to `code-explorer` and receiving a response. Requires 3.c (DockerWorkspace) + 3.h (DelegateTool coder→sub-agent handoff via a supervisor turn). Deferred.
- Verifying `code-explorer` cannot write/execute. Requires a live delegation with a task that TRIES to write and observing the constraint enforced. Deferred to the DockerWorkspace smoke (3.c).
