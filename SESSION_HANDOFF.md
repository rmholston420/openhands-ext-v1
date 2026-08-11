# OpenHands-Ext v1 · Session Handoff — 2026-08-11 19:45 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 3 · Runtime sign-off
- **Plugin / kernel component:** OpenHands-Ext v1 verification matrix
- **Port(s) in progress:** none actively (3.d just closed)

## Completed this session
- 3.h-1 DelegateTool wiring smoke → ✅
- 3.b MCP §2.2 probe → ✅ vacuously
- 3.c DockerWorkspace trivial task smoke → ✅ (router bypassed)
- 3.g fully signed off:
  - Coder :8100 (from Row-1)
  - Planner :8082 tool-call smoke → ✅ (native OpenAI tool_calls in 2.92 s)
  - Embedder :8090 round-trip smoke → ✅ (dim 2560, cos 0.452 / 1.0, wall 0.54 s)
- **3.d Agent Canvas → ✅** (5/5 spec-relevant HTTP checks against ingress :8000 · Canvas v1.6.1 SHA `43f091b`)
- Item 3.j opened: RouterLLM under RemoteConversation

## Phase 3 checklist (current)

| # | Item | Status |
|---|---|---|
| 3.a | `code-explorer` tool registered | ✅ |
| 3.b | MCP §2.2 tools callable | ✅ vacuously |
| 3.c | DockerWorkspace trivial task | ✅ (router bypassed) |
| 3.d | Agent Canvas cloned + running | ✅ |
| 3.e | Event stream in Canvas | ❌ not done (3.d unblocked it) |
| 3.f | Confirmation UI in Canvas | ❌ not done (3.d unblocked it) |
| 3.g | Capability per `base_url` | ✅ (coder + planner + embedder) |
| 3.h-1 | DelegateTool wiring | ✅ |
| 3.h-2 | Cross-endpoint hand-off | ⛔ hardware gap (documented) |
| 3.i | Both endpoints during role-switch | ⚠️ partial |
| 3.j | RouterLLM under RemoteConversation | ❌ not done |

## Current endpoint state
- **Planner :8082 UP** (llama.cpp qwen3_6-27b-q6k-gguf, `--jinja`)
- **Embedder :8090 UP** (llama.cpp qwen3-embedding-4b-q8-gguf, CPU, always-resident per ADR-0017 amd #3)
- **Coder :8100 DOWN** (stopped this session for planner co-residency)

## Canvas state (Colossus, running orphaned from initial boot)
- Ingress :8000 UP (200 with `<title>OpenHands</title>`)
- Vite :3002 UP (frontend; remapped from :3001 which is Gitea)
- Agent-server :18000 UP (`uvx openhands-agent-server`)
- Automation :18001 DOWN — stale `automations.db` moved aside; not required for §3.d (see DEBUG_LOG 2026-08-11 19:44 EDT)
- Canvas parent `npm` process is gone (orphans survive); need clean full-restart before 3.e/3.f.

## Remaining before Phase 3 sign-off
- 3.e/3.f: exercise Canvas against a live conversation
  - Requires configuring an LLM in Canvas Settings (coder :8100 or planner :8082 or a DockerWorkspace-managed agent-server)
  - 3.e = event stream renders
  - 3.f = confirmation UI fires when a tool needs approval
- 3.i: joint role-switch coverage (needs 3.j fix if RouterLLM is in path)
- 3.j: RouterLLM serialization fix (SDK-side) or ADR deferring routing under RemoteConversation
- 3.h-2: ⛔ hardware-blocked (Phase 3.5 model-swap orchestration or new hardware)

## Open questions / awaiting user answer
- **Next up: {3.e/3.f Canvas conversation, 3.j RouterLLM, 3.i via model-swap}?**
  - **3.e/3.f Canvas** — natural continuation; requires deciding which LLM to point Canvas at (coder :8100 offline right now; planner :8082 up but role mismatch for coding tasks) and whether Canvas should back onto our DockerWorkspace or its own agent-server.
  - **3.j RouterLLM** — retroactively strengthens 3.c (removes "router bypassed" caveat); SDK-level Pydantic field work; single-file scope but delicate.
  - **3.i via orchestration** — would require Phase 3.5 model-swap harness; more infra work than a single smoke.

## Exact next action
Await user's choice. **Recommended: 3.e/3.f Canvas conversation smoke.** Two 3.d follow-ups first:

1. **Clean restart of Canvas** (current stack is orphaned; parent is gone). Kill by PID and re-launch cleanly:
   ```bash
   for pid in 2188115 2188283 2188187; do sudo kill -TERM $pid 2>/dev/null; done
   sleep 3
   cd ~/dev/agent-canvas-stock
   export OH_CANVAS_SAFE_VITE_PORT=3002
   nohup npm run dev >/tmp/oh-serve/canvas-dev.log 2>&1 & disown
   ```
2. **Decide LLM target for Canvas** — the coder is down; either bring it up (stop planner to reclaim VRAM) OR point Canvas at the planner (:8082) with a coding-role prompt for the smoke.
