# Kosmos Session Handoff — 2026-08-11 16:39 EDT

## Current build-sequencing position
- **Project:** OpenHands-Ext v1 (this Space)
- **Stage / phase:** Phase 0.4 gate-4 · CLOSED (verdict deferred per ADR-0031)
- **Production embedder:** 4B-Q8 (`qwen3-embedding-4B-Q8_0.gguf`, llama.cpp GPU cold) — **unchanged**

## Completed this session
- Real q-c01 slice labeled (15 g3 / 3 g2 / 4 g1 / 81 g0)
- q-c02 calibration retained; q-c09 + q-c32 labeled unanswerable at pinned SHA
- q-d29 (ADR-0030 L145 P1): 2 g3 / 12 g2 / 8 g1 / 100 g0
- q-c40 (MemoryPort link_entities + TemporalIndex.record_event): 6 g3 / 6 g2 / 10 g1 / 86 g0
- q-d18 (SESSION_HANDOFF L26-35 next-action): 3 g3 / 2 g2 / 20 g1 / 79 g0
- Combined `qrels.jsonl` locked (437 rows, SHA256 `f7137c7bebbf9b10da14091488c185921f4cda2e071880c838eefff4aaca48f8`)
- Offline scorer authored (`bench/scoring/embedder-full-multi-block-calibration/score_offline.py`) — reads step-6b per-cell top-20 without embedder re-run
- 4-query calibration scored on Colossus
- **ADR-0031 filed and Ratified**: verdict DEFER, retain 4B-Q8 incumbent, ADR-0030 execution deferred, ADR-0030b deferred

## Calibration results (frozen, N=4, informational — not a verdict)

| cell | composite |
|---|---|
| e006b_q8_cpu (0.6B Q8) | 16.41 |
| e04b_q8_cpu (4B Q8 incumbent) | **29.11** (retained) |
| e08b_q6k_cpu (8B Q6_K) | 32.04 |
| enomicc_q6k_gpu (nomic, informational) | 28.94 |

## Remaining before Definition of Done
- None for Phase 0.4 gate-4. Gate closed via defer decision.

## Persisted resume state (for any future full re-eval)
- Step-6b pool: `~/.forge-oh/bench_embedder_full_multi_block/pool_*.jsonl` (16 files, ranked top-20 per query)
- Calibration qrels: `bench/gold/embedder-full-multi-block/qrels.jsonl` (SHA256 f7137c7...)
- Rubric: `bench/rubrics/full-embedder-scored.json` (post_hoc_edit_locked=true)
- Corpus SHAs: openhands-ext-v1 `a9d5bd6`, Kosmos `1f33519a`, Rigpa-LMS `55b55539`
- Resume path: expand qrels (append rows for additional queries) → re-lock SHA → rerun offline scorer. **No embedder re-launch required.**

## Open questions / awaiting user answer
- None.

## Exact next action
Move on to the next Phase 0.4 / Phase 1 build task. Phase 0.4 gate-4 is closed.

## Reminders (binding)
- Rubric + gold `post_hoc_edit_locked=true` per ADR-0016 + ADR-0022 — no silent rubric edits when re-eval resumes
- Post-hoc reversal-criteria interpretation remains PROHIBITED
- 4B-Q8 stays as production embedder until a future ratified verdict says otherwise
