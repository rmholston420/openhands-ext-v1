# Kosmos Session Handoff — 2026-08-11 10:49 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-2 · coder correctness harness v1 · staged smoke
- **Plugin / kernel component:** bench harness · stage-1 SDK-surface smoke ready to run
- **Port(s) in progress:** Coder correctness scoring (ADR-0022 medium tier → ADR-0026 v1 harness)

## Completed this session

- ADR-0026 v1 authored + ratified; amendments 1 (import path) and 2 (real SDK surface + harness contract) applied
- SDK freeze file pinned versions at 1.41.0
- Docker smoke: DockerWorkspace boots in ~10.5 s
- Task-set `bench/tasks/coder-medium-multi-turn.json` (10 tasks) + 10 gold rubric files + SHA-256 pins
- Schema extended with `harness_version`, `openhands_sdk_version`, `docker_image` on `run_metadata`; nullable-string so legacy runs remain valid
- `_probe_coder_sdk` in `bench/runner/probes.py`: full ADR-0026 amendment 2 implementation (~250 lines incl. `_run_sdk_task`)
- `bench/runner/main.py`: wired to populate the three new `RunMetadata` fields from task-set + SDK preflight; both paths validated in sandbox against extended schema
- `bench/tests/smoke_sdk_surface.py`: stage-1 SDK-surface smoke (no LLM, no runner)

## Remaining before current Definition of Done

1. **Stage-1 smoke** — run the SDK-surface script:
   ```bash
   cd ~/dev/openhands-ext-v1
   source .venv/bin/activate
   python -m bench.tests.smoke_sdk_surface
   ```
   Expect JSON on stdout with every step `"status": "ok"`. If any step reports `"fail"`, paste the JSON back — do not proceed to stage-2. Step 3 will report which of `stdout`/`output`/`exit_code`/`returncode` are actual attributes on the CommandResult; if the harness assumed the wrong names, a small edit will follow before stage-2.

2. **Stage-2 smoke** (only after stage-1 passes) — one task through the full runner:
   ```bash
   # bring up vLLM on :8100 serving qwen3-coder-30b-a3b-instruct-awq-4bit
   # then, from repo root:
   python -m bench.runner.main \
     --tier medium --role coder \
     --task-set bench/tasks/coder-medium-multi-turn.json \
     --smoke --results-dir bench/results/smoke \
     --candidate-file <one-candidate JSON pointing at :8100>
   ```
   Produces one BenchRun JSON validating against the extended schema with the three new fields populated. The candidate-file path is TBD in the next turn once we confirm the exact vLLM launcher settings.

3. **Full run**: 2 coder cells × 10 tasks (`qwen3-coder-30b-a3b-instruct-awq-4bit` + `qwen3_6-35b-a3b-q4kxl-gguf`).

4. **Score via Perplexity-Max** against the 10 gold files.

5. **File ADR-0027 verdict** applying the pre-registered ADR-0026 reversal criteria (post-hoc interpretation prohibited).

## Open questions / awaiting user answer

- none

## Exact next action

Run stage-1: `python -m bench.tests.smoke_sdk_surface` from the activated venv at `~/dev/openhands-ext-v1`. Paste the JSON output back. If `ok: true`, we proceed to stage-2; if any step fails, we edit `_probe_coder_sdk` before touching vLLM.
