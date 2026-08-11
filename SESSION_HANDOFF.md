# Kosmos-Style Session Handoff — 2026-08-11 18:57 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 3 · Runtime sign-off
- **Plugin / kernel component:** OpenHands-Ext v1 verification matrix
- **Port(s) in progress:** none actively (3.c just closed)

## Completed this session
- 3.h-1 DelegateTool wiring smoke → ✅ (`8853337`)
- 3.b MCP §2.2 probe → ✅ vacuously (`25b722c`)
- 3.c DockerWorkspace trivial task smoke → ✅ (final commit for verdict predicate + matrix + BUILD_LOG)
  - Bug 1: SDK `network=host` + auto `host_port` → health-URL mismatch. Fix: pin `host_port=8000`. (`a57684f`)
  - Bug 2: `_LOCAL_API_KEY="EMPTY"` → litellm sentinel → OpenAI provider path. Fix: `"local"`. (`b35eeae`)
  - Bug 3: `CoderPlannerRouter` doesn't serialize `llms_for_routing` → placeholder routed to `api.openai.com`. Workaround: rebuild `Agent(llm=coder, condenser=build_condenser(coder), tools=<default>)`. (`2636241`, `656cf15`)
  - Bug 4: `has_terminal_error` too broad (any observation with "error" substring). Fix: `ConversationErrorEvent` only. (`692f074`)
- New sign-off item opened: **3.j** RouterLLM/CoderPlannerRouter under RemoteConversation.

## Phase 3 checklist (current)

| # | Item | Status |
|---|---|---|
| 3.a | `code-explorer` tool registered | ✅ |
| 3.b | MCP §2.2 tools callable | ✅ vacuously |
| 3.c | DockerWorkspace trivial task | ✅ (router bypassed) |
| 3.d | Agent Canvas cloned + running | ❌ not done |
| 3.e | Event stream in Canvas | ❌ blocked on 3.d |
| 3.f | Confirmation UI in Canvas | ❌ blocked on 3.d |
| 3.g | Tool-calling per `base_url` | ⚠️ coder ✓, planner/embedder open |
| 3.h-1 | DelegateTool wiring | ✅ |
| 3.h-2 | Cross-endpoint hand-off | ⛔ hardware gap (documented) |
| 3.i | Both endpoints during role-switch | ⚠️ partial |
| 3.j | RouterLLM under RemoteConversation | ❌ not done |

## Remaining before Phase 3 sign-off
- 3.d: `git clone agent-canvas && npm run start` against `http://127.0.0.1:8000`
- 3.e-f: exercise Canvas against a live DockerWorkspace-backed conversation
- 3.g planner half: tool-calling smoke against `:8082` (llama.cpp planner)
- 3.g embedder half: verify `:8090` responds to embedding calls (no tool-calling expected)
- 3.i: joint role-switch coverage (depends on 3.g planner)
- 3.j: RouterLLM serialization fix or ADR deferring routing to a boundary that survives RemoteConversation

## Open questions / awaiting user answer
- **Which item next?** Sensible orders:
  - Cheap first: 3.g planner + embedder smokes (no Canvas dep, no hardware conflict since planner+embedder are XOR-co-resident with coder — need to bring planner up)
  - Milestone first: 3.d Agent Canvas (unlocks 3.e/3.f in one shot)
  - Deferrable-cleanest: 3.j RouterLLM fix (would retroactively strengthen 3.c but is not required for 3.c sign-off)

## Exact next action
Await user's choice among {3.g planner, 3.d Canvas, 3.j RouterLLM}. Default recommendation: **3.g planner smoke** — it's the cheapest and unblocks 3.i joint hand-off directly.
