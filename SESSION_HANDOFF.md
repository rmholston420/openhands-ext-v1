# Kosmos Session Handoff — 2026-08-11 10:44 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-2 · coder correctness harness v1
- **Plugin / kernel component:** bench harness · ready for smoke run
- **Port(s) in progress:** Coder correctness scoring (ADR-0022 medium tier → ADR-0026 v1 harness)

## Completed this session

- ADR-0026 v1 authored + ratified (six locked decisions)
- ADR-0026 amendment 1: SDK 1.41.0 import path
- ADR-0026 amendment 2: real SDK surface + harness contract
- SDK freeze file pinned versions at 1.41.0
- Docker smoke: DockerWorkspace boots in ~10.5 s
- Full SDK surface introspected
- Task-set `bench/tasks/coder-medium-multi-turn.json` (10 tasks, 422 lines) + 10 gold rubric files + SHA-256 pins
- Schema: `bench/schema/run.schema.json` + `bench/schema/run.py` extended with `harness_version`, `openhands_sdk_version`, `docker_image` on `run_metadata`
- `_probe_coder_sdk` in `bench/runner/probes.py`: full ADR-0026 amendment 2 implementation (~250 lines including `_run_sdk_task` helper)
- `bench/runner/main.py` wired: reads `harness_version` + `docker_image_expected` from task set, captures `openhands_sdk_version` at SDK preflight, threads all three into `RunMetadata` on both real and dry-run paths. Non-coder / SDK-unavailable cells force the SDK/Docker fields null so the artifact only records the SDK path when it actually ran.

## Remaining before current Definition of Done

1. **Smoke run:** 1 task on medium tier through the coder cell.
   ```bash
   cd ~/dev/openhands-ext-v1
   source .venv/bin/activate
   # vLLM must be serving qwen3-coder-30b-a3b-instruct-awq-4bit on :8100
   python -m bench.runner.main \
     --tier medium \
     --role coder \
     --task-set bench/tasks/coder-medium-multi-turn.json \
     --smoke \
     --results-dir bench/results/smoke \
     --candidate-file <one-candidate JSON pointing at :8100>
   ```
   (Smoke flag bypasses the open-pool guard; produces one BenchRun JSON validating against the extended schema.)
2. **Full run:** two coder candidates × 10 tasks (`qwen3-coder-30b-a3b-instruct-awq-4bit` at :8100 + `qwen3_6-35b-a3b-q4kxl-gguf`).
3. **Score via Perplexity-Max** against the 10 gold files.
4. **File ADR-0027 verdict** applying the pre-registered ADR-0026 reversal criteria (post-hoc interpretation prohibited).

## Open questions / awaiting user answer

- none

## Exact next action

Bring vLLM up on `:8100` serving `qwen3-coder-30b-a3b-instruct-awq-4bit` (AWQ 4-bit, awq_marlin, `--served-model-name qwen3-coder-30b-a3b-instruct-awq-4bit`, `--max-model-len 32768`, `--gpu-memory-utilization 0.90`), then run the smoke command above with a one-candidate file pointing at the endpoint. First smoke run should produce one BenchRun JSON with the new fields populated and pass `validate_dict`.
