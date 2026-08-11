# Kosmos-style Session Handoff — 2026-08-11 08:49 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 1 · Full-suite live smoke — **COMPLETE**
- **Next queued:** **Phase 0.2** (Medium-tier scored model selection) — coder + planner cells outstanding; embedder Medium verdict already locked
- **Then:** Phase 0.3 (Full tier — ~10 hr final ranking + combination test)

> **PHASE NAMING CORRECTION (2026-08-11 08:49 EDT):** Prior handoff called the next-queued step "Phase 0.3." Per `docs/specs/integration-execution-plan-v16.md`, that step is **Phase 0.2 (Medium tier)**, not Phase 0.3. Phase 0.3 is the Full tier (~10 hr, SWE-bench-Verified for coder, MDE with 3+ repeats, combination test). Medium-tier embedder work already ran under this misnaming; the artifact IS Phase 0.2 (see `bench/results/verdicts/medium-verdict-embedder-20260811T100541Z.json`). ADR-0016 rubric title ("Medium-tier scoring rubric") confirms the correct phase.

## Completed this session

- ADR-0018 filed · Phase −1 version pins (commit `d45cb2f`)
- Phase 2.1 / 2.2 / 2.3 implemented — MCP port range, mode wrapper, skills convention (ADR-0019, commit `7dad739`)
- Phase 1 full-suite API smoke passed 5/5 (ADR-0020 — UFW bridge egress fix, commit `a987ddf`)
- Phase 1 live UI Playwright smoke — headless 7/8 hard PASS + UI6 SOFT (ADR-0021)
- Phase 1 live UI headed v2 — real streaming visible on Colossus display, natural stop at t+28.5 s, +74565 prompt / +931 generation tokens, terminal & editor Canvas tabs captured
- Sandbox reaper installed — `scripts/sandbox_reaper.py` + systemd-user timer running every 5 min, first reap verified; zero-container path now prints status (commit `03a1279`)
- Phase 0.2 pool files authored: `coder-medium-pool.json` (4 cells per ADR-0014), `planner-medium-pool.json` (2 llama.cpp survivors per ADR-0015), `embedder-medium-pool.json` (6 cells, retroactive record; verdict locked)
- Phase 0.2 embedder verdict already locked: 4B bf16 vLLM/gpu (nDCG@10 macro 0.5505)
- Phase naming corrected across SESSION_HANDOFF (this file)
- BUILD_LOG: entries appended for Phase 1 + reaper + Phase 0.2 pool authorship
- ADR-0021 filed with headless + headed v2 baselines
- ADR index updated

## Remaining before current Definition of Done

- **Phase 1 DoD is met.** No blockers.

## Phase 0.2 (Medium tier) — remaining work

**Embedder-Medium: DONE.** Verdict at `bench/results/verdicts/medium-verdict-embedder-20260811T100541Z.json`.

**Coder-Medium: NOT started.** Blockers:
- `bench/tasks/coder-medium.json` — task set not authored
- `bench/gold/coder-medium/` — Perplexity-Max gold tool-call transcripts + expected diffs not authored
- Task-set + gold-reference authorship IS a decision surface (task shape, tool surface, gold format) — requires ADR before task-set freeze

**Planner-Medium: NOT started.** Blockers:
- `bench/tasks/planner-medium.json` — task set not authored (thinker-probe files exist but are ADR-0015-scoped probes, not the Medium task set)
- `bench/gold/planner-medium/` — Perplexity-Max gold plans not authored
- Same ADR-authorship requirement as coder

## Sandbox / runtime state on Colossus (as of session end)

- `openhands-app` container LIVE on :3000, mount `~/.openhands-smoke-2026-08-11/`
- `coder` vLLM 0.27.0 LIVE on :8100, `VLLM_USE_FLASHINFER_SAMPLER=0`
- `embedder` llama.cpp CPU LIVE on :8090 (dim 2560)
- UFW rule `ALLOW IN from 172.17.0.0/16 to any` — persistent
- Settings persisted at `/api/v1/settings` pointing to coder + CodeActAgent
- VRAM ~31.4 GiB used (coder saturating, headroom on planner slot)
- Sandbox reaper: systemd-user timer firing every 5 min, verified unattended

## Open questions awaiting user answer

- **Phase 0.2 continuation ADR authorship:** coder-medium + planner-medium task set + gold-reference protocol. Options and scope to be presented as Block 43c.

## Exact next action

**Block 43c** — present Phase 0.2 task-set + gold-reference ADR-authoring options for coder-medium and planner-medium. Decision surfaces:

1. Task count + shape per role (coder: how many tool-call tasks, real OpenHands surface vs. synthetic; planner: how many multi-step plans, structural-JSON schema)
2. Gold-reference generation protocol (single-shot Perplexity Max vs. multi-sample consensus; freeze + hash policy)
3. Scoring pass structure (single Perplexity-Max scoring pass vs. multi-sample; tie policy from `medium-scored.json` tiebreak)
4. VRAM co-residency during scored runs (embedder always-CPU-resident per ADR-0017 amendment #3; coder vs. planner cell-swap policy)

Await user approval on ADR scope before authoring task sets or gold references. Sandbox cleanup remains automated.
