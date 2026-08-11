# Kosmos Session Handoff — 2026-08-11 17:25 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 2.4 (Tiered multi-LLM routing) — **DoD MET**. Phase 3 (verification) unblocked.
- **Plugin / kernel component:** config surface + Phase 3 smoke harness.
- **Port(s) in progress:** none. ADR-0033 Ratified with two status amendments (17:20 EDT provenance, 17:25 EDT condenser cap placement).

## Completed this session

- 17:10 EDT — ADR-0033 Ratified; `config/agent.py` + `config/router.py` + `bench/smoke-phase-3/` authored (`c01c1e4`).
- 17:20 EDT — ADR-0033 amended: `max_output_tokens` provenance flipped to `SPEC_SHEET` (Phase 0.x bench harness records zero output-token fields). `scripts/populate-max-output-tokens.sh` (`335929d`).
- 17:25 EDT — ADR-0033 amended: condenser 1024 cap moved from `LLM.max_input_tokens` to `LLMSummarizingCondenser.max_tokens` (spec value was semantically mis-placed; SDK 1.41 enforces `MIN_CONTEXT_WINDOW_TOKENS=16384`). `b6dd540`.
- 17:25 EDT — Colossus verified `build_agent() OK: Agent`. Phase 2.4 DoD MET.

## Remaining before current Definition of Done

- **Phase 2.4:** none. DoD met.
- **Phase 3 row 1 (smoke):**
  1. Start coder endpoint (separate terminal): `bash scripts/serve-coder.sh` (must be pre-existing; if not, need to author).
  2. Run smoke: `bash bench/smoke-phase-3/run.sh`.
  3. Expect: event stream + tool calls + FinishAction, wall < 60s.
- **Phase 3 row 2 (role-switch):** Delegate via `DelegateTool` with `call_context.metadata["role"]="planner"`. Likely triggers the SDK 1.41 `RouterLLM.completion()` non-forwarding contingency; decide Path A (override `completion()` in `CoderPlannerRouter`) vs Path B (`fallback_message_heuristic=True` + `[role:planner]` marker) during execution. Path A preferred per ADR-0033 §Contingencies.

## Open questions / awaiting user answer

- Does `scripts/serve-coder.sh` already exist on Colossus? If not, we need to author it before Phase 3 row-1 can run. Confirm with:

  ```bash
  ls -la ~/dev/openhands-ext-v1/scripts/serve-coder.sh 2>&1
  ```

## Exact next action

- User: check for `scripts/serve-coder.sh`. If present, start it in a separate terminal, then run `bash bench/smoke-phase-3/run.sh` and paste result. If absent, request authoring.
