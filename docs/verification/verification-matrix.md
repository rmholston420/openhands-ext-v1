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
| 3.a | `code-explorer` tool registered (ADR-0032, deferred from Phase 1.2 to §2.4/Phase 3) | ⏳ pending inspection | Need to grep `config/agent.py` and `openhands.tools` for registration |
| 3.b | MCP §2.2 tools callable | ⏳ pending inspection | Need to verify MCP servers from §2.2 are live and their tools list is non-empty |
| 3.c | Trivial task under **DockerWorkspace** (not Local), real winning endpoints | ❌ not done | Row-1 smoke ran on `LocalWorkspace` (SDK default). Need Docker-workspace smoke. |
| 3.d | Agent Canvas cloned, built, running against `http://127.0.0.1:8000` | ❌ not done | `git clone agent-canvas && npm run start` never executed |
| 3.e | Event stream renders in Canvas | ❌ not done | Blocked on 3.d |
| 3.f | Confirmation UI fires in Canvas | ❌ not done | Blocked on 3.d |
| 3.g | Tool-calling functional against every configured `base_url` | ⚠️ partial | Row-1 proved coder :8100 tool-calls work. Planner :8082 tool-calling untested. Embedder :8090 untested. |
| 3.h | Coder → planner role-switch **via DelegateTool** (supervisor swap) | ❌ not done | Row-2 exercised `router.completion()` directly, bypassing the delegation pathway |
| 3.i | Both endpoints respond correctly during role-switch | ⚠️ partial | Coder + planner each verified independently (rows 1 and 2); joint hand-off untested |

Order of remaining work (dependency-first):

1. 3.a inspection (`code-explorer` registration)
2. 3.b inspection (MCP §2.2 status)
3. 3.c — wire DockerWorkspace, rerun row-1 style smoke
4. 3.h — wire DelegateTool coder→planner, rerun row-2 style smoke
5. 3.d/e/f — Agent Canvas up, trivial task through Canvas
6. 3.g — planner + embedder tool-calling smokes
7. Flip row 3 to ✅ pass
