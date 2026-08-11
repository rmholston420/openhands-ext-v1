# SESSION_HANDOFF — 2026-08-11 12:19 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.3 gate-3 (coder Full-tier re-eval)
- **Plugin / kernel component:** bench harness (multi-turn) · coder role
- **Port(s) in progress:** none (bench-only)
- **Governing ADR:** ADR-0028 (Ratified 2026-08-11 12:05 EDT · amended 2026-08-11 12:17 EDT for F05 runner-constraint swap)

## Completed this session
- ADR-0027 (gate-2 verdict: CONFIRM AWQ) authored and Ratified; commit `af732e2` pushed.
- ADR-0028 gate-3 opener + Full-tier task-set scaffold committed; commit `cffda04` pushed.
- Gate-3 fixture lock-in (`27d4869`): populated 10 fixtures, authored 10 gold rubric files, `bench/rubrics/full-scored.json` (adds `-10` deduction for FinishAction omission on report-style tasks), 2 candidate cell files, pinned docker SHA digest.
- **F05 amendment (this commit):** ADR-0028 amended; F05 class swapped from "git status + git log summary" (unrunnable — required `fixture_setup_command` hook that `bench/runner/probes.py` does not honor) to "JSON config schema report" (runner-friendly, report-style class preserved, finish-action clause in reversal criteria preserved). Old gold file removed, new gold file authored, task-set + gold_hashes + report_style_task_ids updated.

## Remaining before current Definition of Done
Gate-3 DoD steps 5–7 (from ADR-0028 §Sub-decision 5):
5. Execute probe runs — one run per candidate on the 10-task set.
6. Score all 20 (2 candidates × 10 tasks) via Perplexity Max against `bench/gold/coder-full-multi-turn/*.md`. Compute per-task scores + macro. Mechanically apply reversal criteria (no post-hoc reinterpretation).
7. Author verdict ADR-0029 (CONFIRM AWQ / FLIP to 35b / INTERMEDIATE + log per-task mix), update `adrs/README.md`, append BUILD_LOG, overwrite SESSION_HANDOFF.

## Open questions / awaiting user answer
- **None.** All fixture-lock choices made; F05 amendment applied; docker digest pinned; reversal criteria + post-hoc lock in place.

## Exact next action

**Note:** the runner launches its own vLLM (coder :8501) and llama.cpp (coder-35b :8082) servers via `bench/runner/server.py`. **Stop any pre-existing servers on those ports** before running; the runner will fail to bind otherwise. Correct entrypoint is `scripts/benchmark-tier-runner.py` (NOT `python -m bench.run_multi_turn` — that module does not exist; earlier BUILD_LOG entry 2026-08-11 10:56 EDT confirms).

On Colossus, after pulling:

```bash
cd ~/dev/openhands-ext-v1 && git pull --ff-only

# Stop pre-existing servers on the runner-managed ports:
sudo systemctl stop vllm@coder 2>/dev/null || true
pkill -f "vllm.*--port 8501" 2>/dev/null || true
pkill -f "llama-server.*--port 8082" 2>/dev/null || true

# Candidate A — AWQ (vLLM, :8501, runner-launched)
.venv/bin/python scripts/benchmark-tier-runner.py \
  --tier full --role coder \
  --task-set bench/tasks/coder-full-multi-turn.json \
  --candidate-file bench/candidates/coder-full-awq.json \
  --rubric bench/rubrics/full-scored.json \
  --vllm-release v0.27.0

# Candidate B — 35b (llama.cpp, :8082, runner-launched)
.venv/bin/python scripts/benchmark-tier-runner.py \
  --tier full --role coder \
  --task-set bench/tasks/coder-full-multi-turn.json \
  --candidate-file bench/candidates/coder-full-35b.json \
  --rubric bench/rubrics/full-scored.json \
  --llama-cpp-build b10356
```

Results land in `bench/results/` as `phase-0-full-coder-*.json` (metadata) + `.probe.json` (per-task tool_trace). Dump traces per the `local-llm-bench` skill scoring protocol and paste back for Perplexity-Max scoring against `bench/gold/coder-full-multi-turn/*.md`.

## Notes / caveats
- `expected_final_state_mode: "rubric_only_with_immutable_check"` is a **scorer-only** semantic — the runner accepts it but treats it identically to `rubric_only`. The immutable-check (files must be byte-identical for report-style tasks) is enforced by the Perplexity-Max scoring pass, not by the runner. Do not treat runner coarse_pass as evidence of immutable-check compliance.
- Gate-2 stage-2 coder runs on record used `task_set.identity: "coder-medium"` (single-turn) — see `bench/results/phase-0-medium-coder-qwen3-coder-30b-a3b-instruct-awq-4bit-vllm-gpu-20260811T132200Z.json` `run_metadata.notes` = "degraded: sdk path stubbed". If the Full-tier run produces the same "sdk path stubbed" note, the multi-turn correctness harness (ADR-0026 v1.1) may not be wired end-to-end for the coder role at Full-tier either. Stop and investigate before scoring if that note appears.
