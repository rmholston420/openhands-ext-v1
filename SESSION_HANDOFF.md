# Kosmos-style Session Handoff — 2026-08-11 08:35 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 1 · Full-suite live smoke — **COMPLETE**
- **Next queued:** Phase 0.3 (Medium-tier model selection: coder/planner/embedder re-benchmark)

## Completed this session

- ADR-0018 filed · Phase −1 version pins (commit `d45cb2f`)
- Phase 2.1 / 2.2 / 2.3 implemented — MCP port range, mode wrapper, skills convention (ADR-0019, commit `7dad739`)
- Phase 1 full-suite API smoke passed 5/5 (ADR-0020 — UFW bridge egress fix, commit `a987ddf`)
- Phase 1 live UI Playwright smoke — headless 7/8 hard PASS + UI6 SOFT (ADR-0021)
- Phase 1 live UI headed v2 — real streaming visible on Colossus display, natural stop at t+28.5 s, +74565 prompt / +931 generation tokens, terminal & editor Canvas tabs captured
- Sandbox reaper installed — `scripts/sandbox_reaper.py` + systemd-user timer running every 5 min, first reap verified
- BUILD_LOG: three new entries appended
- ADR-0021 filed with headless + headed v2 baselines
- ADR index updated

## Remaining before current Definition of Done

- **Phase 1 DoD is met.** No blockers.

## Sandbox / runtime state on Colossus (as of session end)

- `openhands-app` container LIVE on :3000, mount `~/.openhands-smoke-2026-08-11/`
- `coder` vLLM 0.27.0 LIVE on :8100, `VLLM_USE_FLASHINFER_SAMPLER=0`
- `embedder` llama.cpp CPU LIVE on :8090 (dim 2560)
- UFW rule `ALLOW IN from 172.17.0.0/16 to any` — persistent
- Settings persisted at `/api/v1/settings` pointing to coder + CodeActAgent
- VRAM ~31.4 GiB used (coder saturating, headroom on planner slot)

## Open questions awaiting user answer

- None. Ready to proceed to Phase 0.3 (Medium-tier re-benchmark) when user says go.

## Exact next action

**Phase 0.3** — Medium-tier model matrix re-benchmark (coder / planner / embedder) to lock in production role selection. Uses `local-llm-bench` skill.

Sandbox cleanup is DONE (see systemd/README.md).
