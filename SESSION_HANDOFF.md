# Kosmos Session Handoff — 2026-08-11 10:52 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-2 · coder correctness harness v1 · **stage-1 PASS, stage-2 ready**
- **Plugin / kernel component:** bench harness · runner + probes wired to v1 SDK contract
- **Port(s) in progress:** Coder correctness scoring (ADR-0022 medium tier → ADR-0026 v1 harness)

## Completed this session

- ADR-0026 v1 authored + ratified; amendments 1 (import path) and 2 (real SDK surface + harness contract) applied
- SDK freeze file pinned versions at 1.41.0
- Task-set + 10 gold rubric files + SHA-256 pins
- Schema extended with `harness_version`, `openhands_sdk_version`, `docker_image` on `run_metadata`
- `_probe_coder_sdk` full implementation (~250 lines) per ADR-0026 amendment 2
- Runner (`main.py`) wired to populate the three new fields; both v1 and legacy null-fields cases validate
- `bench/tests/smoke_sdk_surface.py` written and run: **9/9 steps PASS in 15 s**
- SDK surface **locked**: `CommandResult` has `stdout` + `exit_code`; `Conversation` returns `RemoteConversation`; `send_message` fires `ConversationStateUpdate`, `SystemPrompt`, `Message`, `ConversationStateUpdate` synchronously
- Port check: `PORTS[("vllm","coder")] = 8501` in `main.py` — runner boots its own vLLM; no manual :8100 needed

## Remaining before current Definition of Done

1. **Stage-2 smoke** (one task through full runner, `medium-01` only via `--smoke`):
   ```bash
   cd ~/dev/openhands-ext-v1
   source .venv/bin/activate
   python scripts/benchmark-tier-runner.py \
     --tier medium --role coder \
     --task-set bench/tasks/coder-medium-multi-turn.json \
     --smoke --results-dir bench/results/smoke \
     --candidate-file bench/candidates/coder-medium-stage2-single.json
   ```
   Runner launches its own vLLM on :8501 with `awq_marlin`, `--tool-call-parser qwen3_coder`, `--reasoning-parser qwen3`. Expect one `BenchRun` JSON under `bench/results/smoke/`. Success = artifact validates against the extended schema **and** the three new `run_metadata` fields are populated:
   - `harness_version = "v1"`
   - `openhands_sdk_version = "1.41.0"`
   - `docker_image = "ghcr.io/openhands/agent-server:latest-python"`

   Failure modes to watch:
   - vLLM launch failure on :8501 (port already bound → kill first, or the launcher will surface it)
   - AWQ marlin compilation error (fallback to `--quantization awq` — will require a launcher-flags check)
   - `_probe_coder_sdk` raising because of an SDK-surface case the smoke didn't cover — paste the traceback back

2. **Full run**: 2 coder cells × 10 tasks (`qwen3-coder-30b-a3b-instruct-awq-4bit` + `qwen3_6-35b-a3b-q4kxl-gguf`).

3. **Score via Perplexity-Max** against the 10 gold files (dump → paste → score → verify against raw content per local-llm-bench skill).

4. **File ADR-0027 verdict** applying the pre-registered ADR-0026 reversal criteria (post-hoc interpretation prohibited).

## Open questions / awaiting user answer

- none

## Exact next action

Run stage-2:
```bash
cd ~/dev/openhands-ext-v1 && git pull --ff-only
source .venv/bin/activate
python scripts/benchmark-tier-runner.py \
  --tier medium --role coder \
  --task-set bench/tasks/coder-medium-multi-turn.json \
  --smoke --results-dir bench/results/smoke \
  --candidate-file bench/candidates/coder-medium-stage2-single.json
```
Paste the tail of stdout + the resulting JSON path. If a `BenchRun` JSON lands under `bench/results/smoke/` and its `run_metadata` shows all three v1 fields populated, we proceed to the full 2×10 run.
