# Verification Matrix — Living Checklist

Mirrors the spec's Full Verification Matrix (§v16 spec). Update the "Result" column as
each phase completes on Colossus. Do not edit the "Pass condition" column — those come
verbatim from the spec.

| Phase | Verification | Pass condition | Result | Date |
|---|---|---|---|---|
| -1 | OpenHands + llama.cpp + vLLM versions re-verified live; Blackwell target set; smoke test passes | Per §-1 table | ⏳ pending Colossus | — |
| 0.1 (Fast) | ≤30 min; eliminations documented; version regressions distinguished from model failures | Per §0.1 table | ⏳ pending | — |
| 0.2 (Medium) | ≤60 min; attainability gate; rubrics fixed pre-run; cross-runtime equivalence checked | Per §0.2 table | ⏳ pending | — |
| 0.3 (Full) | <10 hr; MDE stated; variance reported; combination test uses shortlists; decision justified | Per §0.3 table | ⏳ pending | — |
| 0.4–0.6 | Tier-skip documented; config lock; security layering | Per §0.4–0.6 | ⏳ pending | — |
| 1 | Zero LocalWorkspace; isolation confirmed; code-explorer delegation | Per Phase 1 table | ⏳ pending | — |
| 2 | Deployment mode, MCP kill-test, skill capture, tiered routing against real endpoints | No Fast/Medium values leak into production config | ⏳ pending | — |
| 3 | Trivial task + role-switch under DockerWorkspace, real endpoints | Fully functional | ⚠️ partial — see [Phase 3 sign-off checklist](#phase-3-sign-off-checklist) | 2026-08-11 |
| 4 | Port collision resolved; contract inspected; backend switch renders unmodified | Per Phase 4 table | ⏳ pending | — |
| 5–6 | GPU telemetry and backend health reflect actual topology | Accurate, non-conflated | ⏳ pending | — |
| 7 | Neo4j persistence, indexer safety, panel render, scale test | Per Phase 7 table | ⏳ pending | — |
| 8 | Trigger HIGH-risk action | Risk badge shown; audit persisted | ⏳ pending | — |
| 9 | Repeated tool calls | Loop-guard flags repetition | ⏳ pending | — |
| 11 | Grep for remaining frontend imports | None found | ⏳ pending | — |

## Result legend

- ⏳ pending — not yet executed
- ✅ pass — verification table green
- ❌ fail — verification table red; see linked DEBUG_LOG entry
- ⚠️ partial — some checks pass, some fail or deferred; see notes

## Phase 3 sign-off checklist

Spec §Phase 3 Verification (`docs/specs/integration-execution-plan-v16.md:382-385`) requires DockerWorkspace + Agent Canvas + role-switch via delegation, plus code-explorer and MCP §2.2 reachability. Actual coverage as of 2026-08-11 18:06 EDT:

| # | Sign-off item | Status | Evidence / gap |
|---|---|---|---|
| 3.a | `code-explorer` tool registered (ADR-0032, deferred from Phase 1.2 to §2.4/Phase 3) | ✅ registration only | `build_agent()` registers built-in subagents via `register_builtins_agents(enable_browser=False)` and includes `TaskToolSet` via `get_default_tools(enable_sub_agents=True)`. Smoke `bench/smoke-phase-3-item-3a/` `pass=true` 2026-08-11 18:15 EDT (`code-explorer` in registry, tools=`["terminal"]`, level=builtin, source matches shipped preset; agent tools = `terminal`, `file_editor`, `task_tracker`, `task_tool_set`). Live-delegation coverage rolls into 3.h. |
| 3.b | MCP §2.2 tools callable | ✅ vacuously | §2.2 defines only the supergateway install pattern; concrete servers land in Phase 5 (GPU telemetry), Phase 6 (Inference health + Episodic memory), Phase 7 (RepoGraph Neo4j). Probe `bench/smoke-phase-3-item-3b/` 2026-08-11 18:33 EDT confirms prereqs green: `npx`, `uvx`, `supergateway` installed; SDK exposes `MCPClient`/`MCPToolDefinition`/`MCPToolObservation`/`create_mcp_tools`/`MCPServer`; `build_agent()` wires no MCP yet (as expected). Live tool-list smoke deferred to Phases 5-7. |
| 3.c | Trivial task under **DockerWorkspace** (not Local), real winning endpoints | ✅ (router bypassed) | Smoke `bench/smoke-phase-3-item-3c/` `pass=true` 2026-08-11 18:55 EDT. `DockerWorkspace(server_image=ghcr.io/openhands/agent-server:latest-python, network=host, host_port=8000, enable_gpu=False)` container healthy in ~4 s; 89 events; 27 `ActionEvent`s (`terminal`/`file_editor`/`think`/`finish`); `has_finish_action=true`, `has_docker_ok_string=true`, `has_hello_txt=true`; wall 51.25 s. Two DockerWorkspace bugs surfaced and logged: (a) SDK `network=host` + auto-picked random `host_port` → health-poll port mismatch (fix: pin `host_port=8000`, DEBUG_LOG 2026-08-11 18:38 EDT); (b) `_LOCAL_API_KEY=SecretStr("EMPTY")` triggers litellm sentinel path in `RemoteConversation` (fix: `SecretStr("local")`, DEBUG_LOG 2026-08-11 18:48 EDT). Router bypassed with `Agent(llm=build_coder_llm(...), condenser=build_condenser(coder), tools=<default>)` because `CoderPlannerRouter` does not serialize `llms_for_routing` — tracked as new item 3.j. |
| 3.d | Agent Canvas cloned, built, running against `http://127.0.0.1:8000` | ❌ not done | `git clone agent-canvas && npm run start` never executed |
| 3.e | Event stream renders in Canvas | ❌ not done | Blocked on 3.d |
| 3.f | Confirmation UI fires in Canvas | ❌ not done | Blocked on 3.d |
| 3.g | Tool-calling functional against every configured `base_url` | ⚠️ partial | Row-1 proved coder :8100 tool-calls work. Planner :8082 tool-calling untested. Embedder :8090 untested. |
| 3.h-1 | DelegateTool wiring (mechanism only; subagent inherits parent LLM per `manager.py:367`) | ✅ | Smoke `bench/smoke-phase-3-item-3h-1/` `pass=true` 2026-08-11 18:28 EDT. `TaskAction` + `TaskObservation` + `FinishAction` present; subagent located `task/definition.py:198`; wall 19.76 s. Also closes the live-delegation coverage deferred from 3.a. |
| 3.h-2 | Cross-endpoint hand-off (coder supervisor ↔ planner subagent on their real endpoints, via profile store or router marker inside subagent) | ⛔ blocked (hardware) | ADR-0017 XOR co-residency (coder AWQ-4 ~18 GiB + planner Q6_K ~23 GiB = ~41 GiB on a 32 GiB card). Achievable only via sequential model-swap orchestration (Phase 3.5) or new hardware. Documented gap; Row-2 (`bench/smoke-phase-3-row-2/`) provides the endpoint-swap coverage we have via direct `router.completion()` + marker. |
| 3.i | Both endpoints respond correctly during role-switch | ⚠️ partial | Coder + planner each verified independently (rows 1 and 2); joint hand-off untested |
| 3.j | `RouterLLM` / `CoderPlannerRouter` under `RemoteConversation` | ❌ not done | `RouterLLM(LLM)` in SDK 1.41 does not add `llms_for_routing` to its Pydantic field surface. Under `RemoteConversation`, `agent.model_dump(mode="json")` drops the child LLMs; the container-side rebuild instantiates the router with no children and its placeholder (`model=openai/coder-planner-router`, `base_url=null`) is what litellm calls — which routes to `api.openai.com`. Fix likely requires either (a) declaring `llms_for_routing` on `RouterLLM` with a proper discriminated-union type and re-exposing it in `openhands.sdk.llm`, or (b) a custom `model_dump`/`model_validate` override, and possibly an ADR (routing is spec §2.4). DEBUG_LOG 2026-08-11 18:52 EDT. Blocked on: Row-2/3.g planner tool-calling verification and Agent Canvas rows (3.d-f) come first. |

Order of remaining work (dependency-first):

1. ~~3.a inspection (`code-explorer` registration)~~ ✅ 2026-08-11 18:15 EDT
2. ~~3.b inspection (MCP §2.2 status)~~ ✅ vacuously 2026-08-11 18:33 EDT (no servers until Phases 5-7)
3. 3.c — wire DockerWorkspace, rerun row-1 style smoke
4. ~~3.h — wire DelegateTool coder→planner, rerun row-2 style smoke~~
   - ~~3.h-1: DelegateTool wiring (mechanism only)~~ ✅ 2026-08-11 18:28 EDT
   - 3.h-2: cross-endpoint hand-off — ⛔ hardware-blocked (documented gap)
5. 3.d/e/f — Agent Canvas up, trivial task through Canvas
6. 3.g — planner + embedder tool-calling smokes
7. Flip row 3 to ✅ pass
