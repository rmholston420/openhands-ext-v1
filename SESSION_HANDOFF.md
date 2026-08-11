# OpenHands-Ext v1 Session Handoff — 2026-08-11 10:15 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.3 gate-2 — **coder multi-turn correctness harness scope-locked (ADR-0026)**
- **Plugin / kernel component:** `bench/runner/probes.py` `_probe_coder_sdk` scheduled for promotion from stub to full SDK path
- **Port(s) in progress:** none (implementation slice not yet started)

## Completed this session
- Phase 0.2 Medium-tier verdicts filed (commit `8681ebb`)
- ADR-0023 filed: Phase 0.3 router-selection post-Medium (commit `40255c4`)
- ADR-0024 filed: planner migration-ordering probe task-set + reversal criteria (commit `15fd2cd`)
- Probe run at 10:07-10:08 EDT (commit `012e8b1`)
- ADR-0025 filed + pushed: planner probe verdict CONFIRMS ADR-0023 (commit `5550771`)
- ADR-0026 filed (this commit): coder multi-turn correctness harness v1, scope-locked, six decisions:
  1. DockerWorkspace via `openhands.sdk.Conversation`
  2. Perplexity-Max scored 0-100 (tool sequence + file state + code correctness)
  3. Supersede Phase 0.2 medium-tier coder verdict
  4. New `bench/tasks/coder-medium-multi-turn.json` + `bench/gold/coder-medium-multi-turn/*` (existing files stay locked)
  5. `openhands-sdk` + `openhands-tools` into `.oh-venv`, version pinned in `run_metadata`
  6. Sequential-block co-residency (coder OR planner, not both; embedder CPU-resident)

## Production router role assignments (LOCKED at gate-1; coder awaits gate-2 re-verification)
- **coder:** `qwen3-coder-30b-a3b-instruct-awq-4bit` (vLLM, :8100) — held in force until ADR-0027+ files the multi-turn re-verification verdict
- **planner:** `qwen3_6-27b-q6k-gguf` (llama.cpp, :8082) — locked by ADR-0025
- **embedder:** `qwen3-embedding-4b-q8-gguf` (llama.cpp, CPU, :8090)
- **Fallbacks retained:** coder → `qwen3_6-35b-a3b-q4kxl-gguf`; planner → same

## Remaining before current Definition of Done (Phase 0.3 gate-2)
Ordered implementation slice (do NOT re-order; each step depends on prior):

1. **Install SDK into runner venv** — `.oh-venv` on Colossus; `pip install openhands-sdk openhands-tools`; capture `pip freeze | grep -Ei 'openhands|docker' > bench/runner/openhands-sdk-freeze-<ts>.txt`; capture pinned version into `bench/runner/candidates.py` metadata.
2. **Verify DockerWorkspace image starts** — smoke test that `openhands.sdk.workspace.DockerWorkspace(...).start()` succeeds on Colossus Docker. If image pull fails, stop and escalate.
3. **Author `bench/tasks/coder-medium-multi-turn.json`** — copy 10 tasks from `coder-medium.json`, add `expected_final_state` + `smoke_test_command` per task, add `reversal_criteria` block, add `gold_hashes` field (empty pending gold file authoring), update `gold_dir` to `bench/gold/coder-medium-multi-turn`.
4. **Author 10 gold rubric files** at `bench/gold/coder-medium-multi-turn/*.md` — 0-100 bands per task using three-input scoring (tool sequence + file state + code correctness). Perplexity-Max as scoring authority.
5. **Compute gold SHA-256 hashes**, update `bench/tasks/coder-medium-multi-turn.json#/gold_hashes`.
6. **Extend `bench/schema/run.py` + `run.schema.json`** — add `harness_version`, `openhands_sdk_version`, `docker_image` to `run_metadata`.
7. **Promote `_probe_coder_sdk`** in `bench/runner/probes.py` from stub to full implementation — real Conversation loop, per-task fixture seeding via DockerWorkspace, expected-file-state verification after each task, smoke_test_command execution.
8. **Smoke run** — 1 task on 1 cell (30B-instruct-awq) as sanity check that harness produces schema-valid JSON with `harness_version=v1-multi-turn-sdk`.
9. **Full run** — 2 cells × 10 tasks; produces `bench/results/medium-coder-*-<ts>.json` tagged v1.
10. **Score via Perplexity Max** — dump stripped outputs, score against gold bands, apply reversal criteria.
11. **File ADR-0027 verdict** — confirm or supersede ADR-0023 coder row.

## Open questions / awaiting user answer
- None at scope-lock. Implementation slice may raise ADR-0026-flagged stop conditions (SDK install failure, Docker image failure, per-task turn cap exceeded).

## Exact next action
Pull ADR-0026 and start implementation slice step 1 on Colossus:

```bash
cd ~/dev/openhands-ext-v1
git pull
cat adrs/ADR-0026-coder-multi-turn-correctness-harness-v1.md

# then when ready to start step 1:
source .oh-venv/bin/activate
which python  # sanity check
pip install openhands-sdk openhands-tools
```

Or say "proceed with step 1" and I will emit exact install + capture commands.
