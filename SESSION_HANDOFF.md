# Kosmos Session Handoff — 2026-08-11 21:11 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 3 · trivial-task subset ✅ (3.a, 3.b, 3.c, 3.d, 3.e, 3.f, 3.g, 3.h-1). Row 3 remains ⚠️ partial pending joint role-switch (3.h-2 ⛔ hardware / 3.i ⚠️ / 3.j ❌).
- **Plugin / kernel component:** OpenHands-Ext v1 · Agent Canvas UI verified · Phase 3 sign-off checklist.
- **Port(s) in progress:** none (between phase items).

## Completed this session
- Phase 3.e — Event stream renders in Canvas: ✅ HTTP + Canvas UI Playwright PASS.
- Phase 3.f — Confirmation UI fires in Canvas: ✅ HTTP + Canvas UI Playwright PASS.
- Bonus: fresh live conversation created through Canvas UI via Playwright (`d49697e9-224e-4093-bbdb-0f3c0183fd67`), agent called `terminal` (echo, exit 0) + `finish`, `execution_status=finished` in ~3 s, 11 events on disk against `hosted_vllm/qwen3-coder-30b-a3b-instruct-awq-4bit` @ :8100.
- `bench/smoke-phase-3-item-3ef/README.md` written with results matrix, environment, and key findings.
- BUILD_LOG entry appended (2026-08-11 21:11 EDT).
- DEBUG_LOG: three entries appended (Canvas Basic-tab combobox hang → use Advanced tab, `agent_settings_diff` field name required by PATCH, Fernet-encrypted `settings.json` breaks on session-API-key rotation).
- verification-matrix.md updated: 3.e ✅, 3.f ✅, row 3 now flagged as trivial-task ✅ / joint-role-switch remaining; remaining-work list reordered around 3.j and 3.i.

## Remaining before current Definition of Done
Row 3 of the verification matrix (Trivial task + role-switch under DockerWorkspace, real endpoints, fully functional):
- **3.j** — `RouterLLM` / `CoderPlannerRouter` under `RemoteConversation`. `RouterLLM(LLM)` does not add `llms_for_routing` to its Pydantic field surface; `agent.model_dump(mode="json")` in `RemoteConversation` drops the child LLMs; container-side rebuild routes to `api.openai.com`. Likely needs (a) `llms_for_routing` declared as a Pydantic field with a discriminated-union type and re-exposed in `openhands.sdk.llm`, or (b) custom `model_dump` / `model_validate` overrides, plus possibly a spec ADR (routing is spec §2.4).
- **3.i** — joint coder + planner role-switch under `RemoteConversation`. Currently ⚠️ partial: coder and planner each verified independently (rows 1 and 2). Depends on 3.j landing first, then hardware envelope allows a joint hand-off (ADR-0017 XOR co-residency is only a hard block on 3.h-2's co-resident case; 3.i's endpoint-swap variant is achievable if 3.j serialization is fixed).
- Pending ADR (deferred from earlier): DockerWorkspace-based isolation moved to a separate Forge-OH sub-port (LocalWorkspace only accepted at the outer HTTP surface).

## Open questions / awaiting user answer
- Which next: **3.j first (RouterLLM serialization under RemoteConversation)** or **3.i first (both endpoints during role-switch)**? Dependency order suggests 3.j → 3.i, but user may want to hand-verify 3.i's endpoint-swap variant before committing to a serialization fix.

## Exact next action
- Wait for user's answer on 3.i vs 3.j.
- On 3.j: read `openhands.sdk.llm.router.base.RouterLLM` and `CoderPlannerRouter`; probe `RemoteConversation.agent.model_dump(mode="json")` output to confirm which fields drop; scope the fix (Pydantic field + type vs. custom (de)serialization) and note whether a spec ADR is needed before writing code.
- On 3.i: draft the endpoint-swap flow (sequential coder → planner via bench/smoke-phase-3-row-2 harness under `RemoteConversation`), confirm stop condition against spec v16 §Phase 3 verification.
