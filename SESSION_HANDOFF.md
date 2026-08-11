# Kosmos-Style Session Handoff — 2026-08-11 19:14 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 3 · Runtime sign-off
- **Plugin / kernel component:** OpenHands-Ext v1 verification matrix
- **Port(s) in progress:** none actively (3.g planner just closed)

## Completed this session
- 3.h-1 DelegateTool wiring smoke → ✅
- 3.b MCP §2.2 probe → ✅ vacuously
- 3.c DockerWorkspace trivial task smoke → ✅ (router bypassed)
  - Bug 1: `network=host` + auto `host_port` → health-URL mismatch (fix: pin `host_port=8000`)
  - Bug 2: `_LOCAL_API_KEY="EMPTY"` → litellm sentinel → OpenAI provider (fix: `"local"`)
  - Bug 3 (deferred): `CoderPlannerRouter` doesn't serialize `llms_for_routing` → tracked as new item 3.j
  - Bug 4: `has_terminal_error` predicate too broad (fix: `ConversationErrorEvent` only)
- 3.g planner tool-calling smoke → ✅
  - Native OpenAI `tool_calls` verified against llama.cpp :8082 in 2.92 s
  - `--jinja` chat template working
  - Predicate learning: SDK auto-derives OpenAI tool name from class name
- Item 3.j opened: RouterLLM under RemoteConversation

## Phase 3 checklist (current)

| # | Item | Status |
|---|---|---|
| 3.a | `code-explorer` tool registered | ✅ |
| 3.b | MCP §2.2 tools callable | ✅ vacuously |
| 3.c | DockerWorkspace trivial task | ✅ (router bypassed) |
| 3.d | Agent Canvas cloned + running | ❌ not done |
| 3.e | Event stream in Canvas | ❌ blocked on 3.d |
| 3.f | Confirmation UI in Canvas | ❌ blocked on 3.d |
| 3.g | Tool-calling per `base_url` | ⚠️ coder ✓, planner ✓, embedder-round-trip open |
| 3.h-1 | DelegateTool wiring | ✅ |
| 3.h-2 | Cross-endpoint hand-off | ⛔ hardware gap (documented) |
| 3.i | Both endpoints during role-switch | ⚠️ partial |
| 3.j | RouterLLM under RemoteConversation | ❌ not done |

## Remaining before Phase 3 sign-off
- 3.g embedder half: embedding round-trip smoke against `:8090` (NOT tool-calling — that's not what an embedding endpoint does). Requires embedder up (co-resident with planner per ADR-0017).
- 3.d: `git clone agent-canvas && npm run start` against `http://127.0.0.1:8000`
- 3.e-f: exercise Canvas against a live DockerWorkspace-backed conversation
- 3.i: joint role-switch coverage (now unblocked by 3.g planner — but requires 3.j fix if RouterLLM is in the path)
- 3.j: RouterLLM serialization fix or ADR deferring routing

## Current endpoint state
- **Planner :8082 UP** (llama.cpp qwen3_6-27b-q6k-gguf, `--jinja`) — brought up this session
- **Coder :8100 DOWN** — stopped this session for planner co-residency
- **Embedder :8090 DOWN** — never brought up this session

## Open questions / awaiting user answer
- **Which item next?** Sensible orders:
  - **Cheap-and-momentum**: 3.g embedder half — planner is already up, embedder is co-resident with planner (ADR-0017 Option 2), so `scripts/serve-embedder.sh` should work right now with no VRAM swap. Small, isolated round-trip.
  - **Milestone**: 3.d Agent Canvas — unlocks 3.e/3.f in one shot; longer build.
  - **Deferrable-cleanest**: 3.j RouterLLM fix — retroactively strengthens 3.c; SDK-level change.

## Exact next action
Await user's choice among {3.g embedder, 3.d Canvas, 3.j RouterLLM}. Default recommendation: **3.g embedder** — cheapest, unblocks nothing else, but closes the remaining half of 3.g while the planner-plus-embedder co-residency is already live.
