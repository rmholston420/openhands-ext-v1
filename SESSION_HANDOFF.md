# Kosmos Session Handoff — 2026-08-11 17:20 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 2.4 (Tiered multi-LLM routing) — authoring COMPLETE; awaiting user to populate `config/max-output-tokens.json` on Colossus, then Phase 3 verification (row-1 smoke + row-2 role-switch).
- **Plugin / kernel component:** config surface (`config/agent.py`, `config/router.py`), Phase 3 smoke harness (`bench/smoke-phase-3/`).
- **Port(s) in progress:** none new. ADR-0033 (Ratified, amended 17:20 EDT) locks the config surface. Router uses SDK 1.41 `RouterLLM` base; dispatch via `LLMCallContext.metadata["role"]` (option 6c). Condenser reuses coder endpoint (option 7a).

## Completed this session

- 17:10 EDT — ADR-0033 Ratified; `config/agent.py` + `config/router.py` + `bench/smoke-phase-3/` authored; commit `c01c1e4` pushed.
- 17:20 EDT — ADR-0033 amended: `max_output_tokens` provenance flipped from EMPIRICAL to SPEC_SHEET after Colossus investigation confirmed Phase 0.x bench harness records zero output-token fields. Replaced `extract-max-output-tokens.sh` with `populate-max-output-tokens.sh` (spec-sheet ceiling 8192 for both roles, provenance flavor SPEC_SHEET, empirical override deferred to ADR-0035).

## Remaining before current Definition of Done

- User runs on Colossus:
  1. `cd ~/dev/openhands-ext-v1 && git pull`
  2. `bash scripts/populate-max-output-tokens.sh`
  3. `cat config/max-output-tokens.json`
  4. `.venv/bin/python -c "from config.agent import build_agent; a = build_agent(); print('build_agent OK', type(a).__name__)"`
- Then Phase 3 verification:
  - Row 1: `bash bench/smoke-phase-3/run.sh` (trivial task, coder endpoint, expects event stream + FinishAction, wall < 60s).
  - Row 2: role-switch via `DelegateTool` with `call_context.metadata["role"]="planner"` — likely triggers the SDK 1.41 `RouterLLM.completion()` non-forwarding contingency; decide Path A (override `completion()` in `CoderPlannerRouter`) vs Path B (`fallback_message_heuristic=True`) during execution. Path A is preferred per ADR-0033 §Contingencies.

## Open questions / awaiting user answer

- None. The `SPEC_SHEET` provenance flavor was chosen agent-side under the "make the optimal choice when the spec or evidence makes it clear" clause (spec-sheet ceilings are conservative upper bounds; empirical measurement path is preserved via ADR-0035 deferral).

## Exact next action

- User: run the four Colossus commands above (`git pull`, `populate-max-output-tokens.sh`, `cat`, `build_agent` import test). Paste output. Then Phase 3 row-1 smoke.
