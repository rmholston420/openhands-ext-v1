# Kosmos Session Handoff — 2026-08-11 16:50 EDT

## Current build-sequencing position
- **Project:** OpenHands-Ext v1 (this Space)
- **Stage / phase:** Phase 1 CLOSED (spec-scope 1.1 done; 1.2 deferred to §2.4/3 per ADR-0032) → **opening Phase 2.4 (tiered multi-LLM routing) + Phase 3 (baseline verification)** next session
- **Production embedder:** 4B-Q8 (`qwen3-embedding-4B-Q8_0.gguf`, llama.cpp GPU cold) — unchanged (ADR-0031)

## Completed this session (Phase 0.4 gate-4 + Phase 1)
- 4-query calibration labeled + locked qrels (SHA256 `f7137c7bebbf9b10da14091488c185921f4cda2e071880c838eefff4aaca48f8`)
- Offline scorer authored + ran (`bench/scoring/embedder-full-multi-block-calibration/score_offline.py`)
- ADR-0031 Ratified: verdict DEFER, retain 4B-Q8 incumbent
- ADR-0030 amended: execution deferred; ADR-0030b deferred
- Phase 1 hook installer executed on Colossus
- Hook allow-list amended for `docs/BENCHMARK_UNPAUSE_GATES.md`; full-tree dispatch now clean
- ADR-0032 Ratified: Phase 1 spec-scope closure (1.1 done, 1.2 deferred)

## Ratified this session
- ADR-0031 (embedder verdict DEFER)
- ADR-0032 (Phase 1 spec-scope closure + 1.2 defer)

## Deferred (queue items, not blockers)
- Phase 0.4 full-tier re-eval: resume by appending to `bench/gold/embedder-full-multi-block/qrels.jsonl` → re-lock SHA → rerun offline scorer. No embedder relaunch. Rubric post_hoc_edit_locked=true.
- ADR-0030 (still Proposed pending future execution)
- ADR-0030b (still Proposed, deferred to post-verdict)

## Next session: Phase 2.4 + Phase 3 opener
- **Spec:** `docs/specs/integration-execution-plan-v16.md` §2.4 (L328+) + §Phase 3 (L367+)
- **Prerequisite:** Phase 0.3 concludes ✅ (ADR-0029 Ratified, AWQ retained)
- **Scope to restate before executing:**
  - Populate `[llm]` router table with Phase 0.3 winners (AWQ coder, 27B-Q6_K planner per ADR-0023/0025/0029)
  - Register `code-explorer` (Phase 1.2 rollover per ADR-0032)
  - Runtime config surface: `config/agent.toml` (or SDK equivalent — investigate donor Forge-OH config layout first per Kosmos port workflow)
  - Coder XOR planner enforcement: verify orchestration primitive prevents concurrent GPU-resident LLMs beyond corrected co-residency contract
  - Phase 3 verification matrix (§Phase 3 L378-386)
- **Ambiguity to flag on kickoff:**
  - Config file format + location (Forge-OH uses `.env` + Python config classes; OpenHands SDK canonical config format needs a donor inspection before greenfield authoring)
  - Router table implementation surface (config-only vs code-based dispatcher) — the spec is thin here

## Remaining before Definition of Done
- **None for Phase 1 as scoped.** Gate closed via ADR-0032.

## Open questions / awaiting user answer
- None (Phase 2.4 opener will surface any).

## Exact next action
Kick off Phase 2.4 opener. Load `kosmos-port-workflow` skill, inspect Forge-OH donor config, restate exact scope from spec §2.4 + §Phase 3, flag ambiguities, wait for confirmation before scaffolding runtime config.

## Reminders (binding)
- `code-explorer` (Phase 1.2) registers in Phase 2.4 runtime tool registry per ADR-0032
- Router config populated with Phase 0.3 winners only: AWQ coder + 27B-Q6_K planner
- No LocalWorkspace anywhere in runtime config (pre-commit hook enforces on every commit)
