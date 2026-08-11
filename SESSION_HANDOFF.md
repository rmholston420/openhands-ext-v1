# OpenHands-Ext v1 · Session Handoff — 2026-08-11 19:19 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 3 · Runtime sign-off
- **Plugin / kernel component:** OpenHands-Ext v1 verification matrix
- **Port(s) in progress:** none actively (3.g fully closed)

## Completed this session
- 3.h-1 DelegateTool wiring smoke → ✅
- 3.b MCP §2.2 probe → ✅ vacuously
- 3.c DockerWorkspace trivial task smoke → ✅ (router bypassed)
- 3.g fully signed off →
  - Coder :8100 (from Row-1)
  - Planner :8082 tool-call smoke → ✅ (native OpenAI tool_calls in 2.92 s)
  - Embedder :8090 round-trip smoke → ✅ (dim 2560, cos 0.452 / 1.0, wall 0.54 s)
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
| 3.g | Capability per `base_url` | ✅ (coder + planner + embedder) |
| 3.h-1 | DelegateTool wiring | ✅ |
| 3.h-2 | Cross-endpoint hand-off | ⛔ hardware gap (documented) |
| 3.i | Both endpoints during role-switch | ⚠️ partial |
| 3.j | RouterLLM under RemoteConversation | ❌ not done |

## Current endpoint state
- **Planner :8082 UP** (llama.cpp qwen3_6-27b-q6k-gguf, `--jinja`)
- **Embedder :8090 UP** (llama.cpp qwen3-embedding-4b-q8-gguf, CPU, always-resident per ADR-0017 amd #3)
- **Coder :8100 DOWN** (stopped this session for planner co-residency)

## Remaining before Phase 3 sign-off
- 3.d Agent Canvas: `git clone agent-canvas && npm run start` against `http://127.0.0.1:8000`
- 3.e/3.f: exercise Canvas against a live DockerWorkspace-backed conversation
- 3.i: joint role-switch coverage (needs 3.j fix if RouterLLM is in path)
- 3.j: RouterLLM serialization fix (SDK-side) or ADR deferring routing under RemoteConversation

## Open questions / awaiting user answer
- **Which next among {3.d Canvas, 3.j RouterLLM, 3.i via model-swap orchestration}?**
  - **3.d Canvas** — biggest milestone; unlocks 3.e + 3.f simultaneously; longer build (npm/frontend).
  - **3.j RouterLLM** — retroactively strengthens 3.c (removes "router bypassed" caveat); SDK-level Pydantic field work; single-file scope but delicate.
  - **3.i via orchestration** — would require Phase 3.5 model-swap harness (stop coder, start planner mid-turn); more infra work than a single smoke.

## Exact next action
Await user's choice. Default recommendation: **3.d Agent Canvas** — largest per-hour ROI (three items collapse into one build). If 3.d proves painful, fall back to **3.j** for a clean single-file win before returning.
