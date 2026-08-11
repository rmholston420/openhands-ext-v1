# OpenHands-Ext v1 Session Handoff — 2026-08-11 11:57 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-3 — **OPENED** (fixture lock-in pending)
- **Plugin / kernel component:** Coder role Full-tier re-eval (AWQ production vs 35b challenger)
- **Port(s) in progress:** None — no new adapters at gate-3 (same runtimes as Medium).

## Completed this session

- Committed default_tools kwarg fix (`8963a10`)
- Authored ADR-0026 amendment 3 (transport + tools + scoping + trace schema v1.1); committed (`74e17ae`)
- Regenerated AWQ stage-2 artifact at v1.1 (10/10 pass)
- Added stage-2 candidate file for 35b (`215fb14`); ran 35b stage-2 (10/10 pass)
- Scored both candidates against gold rubric (AWQ 85.4 vs 35b 88.7 macro; 35b fails T05/T08 finish-action)
- Filed ADR-0027 (Phase 0.3 gate-2 verdict: CONFIRM AWQ) + index update + BUILD_LOG entry; committed `af732e2`
- Filed **ADR-0028** (Phase 0.3 gate-3 opener: coder Full-tier re-eval, Proposed) + index update
- Scaffolded `bench/tasks/coder-full-multi-turn.json` with schema + reversal criteria LOCKED, fixtures UNFROZEN
- BUILD_LOG entry appended; this SESSION_HANDOFF overwritten

## Remaining before current Definition of Done

Phase 0.3 gate-3 DoD (ADR-0028 §Sub-decision 5) — 7 steps, 0 complete:

1. Populate `bench/tasks/coder-full-multi-turn.json` fixtures + prompts + gold_hashes; set `post_hoc_edit_locked=true`; flip ADR-0028 Proposed → Ratified
2. Write `bench/gold/coder-full-multi-turn/*.md` (10 per-task rubric files) and hash-lock
3. Write `bench/rubrics/full-scored.json` (extends medium-scored.json with −10 no-FinishAction-on-report-style deduction) and hash-lock
4. Land `bench/candidates/coder-full-awq.json` and `bench/candidates/coder-full-35b.json`
5. Run both candidate probes: v1.1 shape, 10/10 R1/R2 pass, agent_errors=0, run_errors=0, harness_commit_sha recorded
6. Perplexity-Max scoring pass; per-task scores + macro means logged
7. Apply reversal criteria mechanically; file ADR-0029 with verdict

## Open questions / awaiting user answer

- **Fixture authoring drives next work.** Options:
  - **(a) Author all 10 fixtures + prompts + gold rubrics + candidate files in one lock-in commit** — full DoD step 1-4 in one shot; then run probes and score. Highest throughput; largest single commit.
  - **(b) Author F01-F05 first (mixed-class + first report-style), run partial probe, then F06-F10.** Lower per-commit risk; delays macro comparison since scoring runs only after all 10 land.
  - **(c) Author only fixtures + prompts first (locking task-side), score-side (gold + rubric) after** — decouples task authoring from scoring authoring. Adds a lock-in step but lets probes run before rubric drift risk closes off.

- **Docker image + SDK version.** Same as Medium (`ghcr.io/openhands/agent-server:latest-python`, openhands-sdk 1.41.0) unless directed otherwise. Encoded in the scaffold.

- **Third candidate?** ADR-0028 §Rationale rejects introducing a third candidate at gate-3. Confirm this holds if a Q6_K coder variant or hybrid tempts.

## Exact next action

Decide fixture-authoring path (a/b/c above), then load `kosmos-port-workflow` + `local-llm-bench` and begin the lock-in commit for path (a) unless a/c chosen.

## Key production selections locked as of this handoff

- **Coder (Medium):** `qwen3-coder-30b-a3b-instruct-awq-4bit` — vLLM, GPU, :8501 (ADR-0017 + ADR-0023 + ADR-0027)
- **Planner (Medium):** `qwen3_6-27b-q6k-gguf` — llama.cpp, GPU, :8082 (ADR-0023 + ADR-0025)
- **Embedder:** `qwen3-embedding-4b-Q8_0` (ADR-0017)
- **Co-residency:** Option 2 (ADR-0017)

## ADR pipeline

- **ADR-0028** — Proposed · flips to Ratified at fixture lock-in commit
- **ADR-0029** — Reserved for Phase 0.3 gate-3 verdict (after scoring)
