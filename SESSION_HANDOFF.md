# Kosmos Session Handoff — 2026-08-11 12:46 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-3 **CLOSED**. Phase 0.4 (embedder Full-tier re-eval) is the next gate.
- **Plugin / kernel component:** bench harness (multi-turn, DockerWorkspace SDK path) — stable
- **Port(s) in progress:** none (verdict-only close-out)

## Verdict

**Phase 0.3 gate-3: CONFIRM AWQ** (`Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` on vLLM). ADR-0029 filed.

Macro: AWQ 88.1, 35b 66.0 (Δ −22.1). 35b omitted FinishAction on all 3 report-style tasks (F04, F05, F09), collapsing them to functional zero. All three `confirm_awq_if` reversal-criterion clauses fired independently; all three `flip_to_35b_a3b_q4kxl_if` clauses failed. Verdict is mechanical, not judgmental.

## Completed this session

- Runner verified end-to-end (SDK 1.41.0, docker0=172.17.0.1, digest pinned + pulled, no stubbed fallback path exercised)
- Both Full-tier probes executed successfully with real SDK+Docker (ws_boot ~4.4s, sdk_version=1.41.0 stamped in `notes`)
- Raw probe artifacts pushed to git (commit `7a03d49`): `bench/scoring/full-coder/probes/{awq,35b}.{probe,meta}.json`
- Extractor v2 built and run: `bench/scoring/full-coder/probes/{awq,35b}_v2.txt`
- Per-task scoring rationale filed: `bench/scoring/full-coder/SCORING_20260811.md`
- ADR-0029 filed and indexed
- BUILD_LOG 12:46 EDT entry appended
- This SESSION_HANDOFF overwritten

## Remaining before current Definition of Done

None — gate-3 DoD is fully met.

## Open questions / awaiting user answer

- Phase 0.4 (embedder Full-tier re-eval) scope: task-set design + candidate pair. **Not started.** Do you want to open Phase 0.4 in a new session, or continue in this one?
- Do you want 35b formally retired from the coder candidate pool now (would require its own ADR), or defer that to Phase 1 as noted in ADR-0029's Consequences section?

## Exact next action

If continuing to Phase 0.4:

```bash
# Draft the Phase 0.4 embedder Full-tier ADR opener (task-set + rubric + reversal criteria)
# — analogous shape to ADR-0028.
# (Wait for user to specify candidate pair and task-set scope first.)
```

If closing this session:

```bash
cd ~/dev/openhands-ext-v1 && git pull --ff-only origin main
# then read the latest ADR-0029 and SESSION_HANDOFF at your leisure
```

## Key file references

- `adrs/ADR-0029-phase-0-3-gate-3-coder-verdict-confirm-awq.md` — verdict ADR
- `bench/scoring/full-coder/SCORING_20260811.md` — per-task 0-100 scoring rationale
- `bench/scoring/full-coder/probes/awq.probe.json` — AWQ raw probe (203KB)
- `bench/scoring/full-coder/probes/35b.probe.json` — 35b raw probe (123KB)
- `bench/scoring/full-coder/probes/{awq,35b}_v2.txt` — compact extractions used for scoring
- `bench/rubrics/full-scored.json` — locked rubric (post_hoc_edit_locked)
- `bench/tasks/coder-full-multi-turn.json` — locked task-set
- `bench/gold/coder-full-multi-turn/*.md` — locked per-task gold rubrics
