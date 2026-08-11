# Kosmos Session Handoff — 2026-08-11 17:10 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 2.4 (config surface authored) → Phase 3 (verification, pending execution)
- **Plugin / kernel component:** OpenHands-Ext v1 canonical config surface — `config/agent.py` + `config/router.py`
- **Port(s) in progress:** none formally; `CoderPlannerRouter` is a config-surface subclass, not a port

## Completed this session

- Filed ADR-0031 (Ratified) — Phase 0.4 gate-4 embedder verdict DEFER; retain 4B-Q8 incumbent
- Filed ADR-0032 (Ratified) — Phase 1 spec-scope closure: 1.1 DockerWorkspace-only policy CLOSED; 1.2 code-explorer registration deferred to Phase 2.4/3
- Committed offline scorer + 4-query calibration markdown to `bench/scoring/embedder-full-multi-block-calibration/`
- Amended spec §Phase 1 L292 with 1.2 deferral footnote
- Amended pre-commit allow-list to exempt `docs/BENCHMARK_UNPAUSE_GATES.md`
- Inspected openhands-sdk 1.41.0 on Colossus: RouterLLM base class + MultimodalRouter reference impl + LLMSummarizingCondenser + openhands.tools.delegate + openhands.tools.task.TaskToolSet
- Filed ADR-0033 (Ratified) — Phase 2.4 config surface: Python module, not TOML; option 6c LLMCallContext dispatch; option 7a coder-as-condenser
- Authored `config/agent.py` (build_coder_llm / build_planner_llm / build_embedder_llm / build_router / build_condenser / build_agent)
- Authored `config/router.py` (CoderPlannerRouter subclass dispatching via `LLMCallContext.metadata['role']`)
- Authored `scripts/extract-max-output-tokens.sh` (measured provenance → `config/max-output-tokens.json`)
- Authored `bench/smoke-phase-3/{task.md, README-target.txt, run.sh}` for Phase 3 row-1 verification
- Amended spec §2.4 with ADR-0033 pointer; rewrote `config/README.md`

## Remaining before current Definition of Done

Phase 2.4 authoring is complete. Phase 3 verification matrix (spec L378-386) is the next DoD gate:

1. User runs `scripts/extract-max-output-tokens.sh` on Colossus to populate `config/max-output-tokens.json`
2. User clones agent-canvas donor: `git clone https://github.com/OpenHands/agent-canvas.git ~/dev/agent-canvas-stock && cd ~/dev/agent-canvas-stock && git checkout v1.6.1`
3. User starts coder endpoint: `scripts/serve-coder.sh` (foreground) in a separate terminal
4. User runs Phase 3 row-1 smoke: `bash bench/smoke-phase-3/run.sh` → confirm event stream + tool action + FinishAction + expected line + wall < 60s
5. Phase 3 row-2 (role-switch): dispatch a planner task via `DelegateTool` with `call_context.metadata["role"]="planner"` → confirm CoderPlannerRouter selects planner, supervisor swap completes
6. File ADR-0034 (Phase 3 verdict) after both rows pass

## Open questions / awaiting user answer

- **LLMCallContext metadata propagation:** the SDK 1.41 `RouterLLM.completion()` signature does NOT forward `call_context` to `select_llm()` by default (base class only passes `messages`). Two paths, decidable at Phase 3 row-2:
    - **Path A:** Override `completion()` in `CoderPlannerRouter` to intercept `call_context` before calling `select_llm(messages, call_context=call_context)`.
    - **Path B:** Flip `CoderPlannerRouter.fallback_message_heuristic = True` and use `[role:planner]` marker in the last user message as the dispatch signal (option 6b fallback documented in ADR-0033).
    Recommendation: Path A (cleaner, matches option 6c intent). Decide during row-2 execution.

## Exact next action

Run on Colossus:

```bash
cd ~/dev/openhands-ext-v1 && git pull
bash scripts/extract-max-output-tokens.sh
cat config/max-output-tokens.json
```

Paste output. Then decide whether to clone agent-canvas + run the smoke immediately or in a follow-up session.
