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
| 3 | Trivial task + role-switch under DockerWorkspace, real endpoints | Fully functional | ⏳ pending | — |
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
