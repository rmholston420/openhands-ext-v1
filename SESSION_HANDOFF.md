# Kosmos Session Handoff — 2026-08-11 22:47 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 3 sign-off · item 3.j complete (LocalWorkspace scope per ADR-0036)
- **Plugin / kernel component:** Vendored openhands-sdk (`vendor/openhands-sdk/openhands/sdk/llm/llm.py`) — ADR-0034 patch
- **Port(s) in progress:** none (Phase 3.j signed off)

## Completed this session
- ADR-0036 authored + ratified: published `ghcr.io/openhands/agent-server:*-python` image is PyInstaller `binary` target (frozen `openhands.sdk` bytecode in ELF); no overlay-image approach can inject the ADR-0034 patch.
- ADR-0035 (container-side overlay Dockerfile) superseded by ADR-0036; overlay artifacts moved to `docs/rejected/`; `PORTING_LEDGER.md` entry marked REJECTED.
- Verification matrix row 3.j scoped to LocalWorkspace ✅; new row 3.k ⛔ deferred (needs source-target agent-server image build via Option A or Option C).
- 3.j smoke rewritten to LocalWorkspace: `bench/smoke-phase-3-item-3j/run.sh` — dumps agent, reconstructs CoderPlannerRouter via `LLM.model_validate(payload)`, verifies base URLs preserved, runs `Conversation.run()` to completion with local coder :8100.
- False-negative round 1: `openai` substring matched litellm's `openai/<model>` provider prefix → renamed to `events_mention_openai_host` with `api.openai.com`.
- False-negative round 2: `api.openai.com` also appears inert inside litellm cost-warning docstring + OpenHands SystemPromptEvent doc URLs → switched load-bearing negative check to `events_mention_openai_auth_error` (AuthenticationError / Incorrect API key).
- **3.j smoke PASS end-to-end 2026-08-11 22:45 EDT:** `pass=true` at `~/.forge-oh/bench_smoke_phase_3_item_3j/20260811_224545_run/verdict.json`. Load-bearing evidence: `rebuild_is_router=true`, both base URLs preserved, `router-ok-3j` file created + verified via `has_finish_action=true`, `wall_seconds=3.27`, stdout `CoderPlannerRouter: default → coder` + `RouterLLM routing to coder...` at every step, no auth errors, no ConversationErrorEvent.
- ADR-0034 status amendment 2026-08-11 22:47 EDT: RATIFIED end-to-end (LocalWorkspace scope).
- Verification matrix row 3.j evidence line updated with `20260811_224545_run` path + passing signals.

## Remaining before current Definition of Done
- Phase 3.j Definition of Done (LocalWorkspace scope per ADR-0036): **met**.
- 3.k (container-side under DockerWorkspace with source-target agent-server image): deferred to Phase 3.5 or Phase 4 pickup. Choose Option A (local build of upstream `source` target + overlay ADR-0034 patch) vs Option C (fork + rebuild `binary` + private registry). Not blocking Phase 3 gate.

## Open questions / awaiting user answer
- Proceed to Phase 3.k now, or move to next item in `docs/verification/verification-matrix.md`?

## Exact next action
- User's choice: (A) start Phase 3.k Option A build against upstream `source` target at pin `ca46719d5e9a0b0af79f7de2da37067a5b94563c`, or (B) advance to next Phase 3 sign-off row (3.h-2, 3.i joint hand-off, or move to Phase 4).
