# Kosmos Session Handoff — 2026-08-11 10:42 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-2 · coder correctness harness v1
- **Plugin / kernel component:** bench harness · smoke run on 1 task × 1 cell
- **Port(s) in progress:** Coder correctness scoring (ADR-0022 medium tier → ADR-0026 v1 harness at medium tier)

## Completed this session

- ADR-0026 authored + ratified (six decisions locked)
- ADR-0026 amendment 1: SDK 1.41.0 import path
- ADR-0026 amendment 2: real SDK surface + harness contract
- SDK freeze file pinned versions at 1.41.0
- Docker smoke run passed — DockerWorkspace boots in ~10.5 s
- Full SDK surface introspected
- Task-set `bench/tasks/coder-medium-multi-turn.json` (10 tasks, 422 lines)
- 10 gold rubric files under `bench/gold/coder-medium-multi-turn/`
- SHA-256 hashes pinned in task-set
- `bench/schema/run.schema.json` extended with `harness_version`, `openhands_sdk_version`, `docker_image` (nullable) on `run_metadata`
- `bench/schema/run.py` dataclass `RunMetadata` extended with three new `Optional[str]` fields
- `_probe_coder_sdk` in `bench/runner/probes.py` promoted from `NotImplementedError` stub to full implementation per ADR-0026 amendment 2 contract (~250 lines including `_run_sdk_task` helper)

## Remaining before current Definition of Done

1. **Wire the caller** (runner CLI / driver) to route the medium-tier multi-turn task set through `_probe_coder_sdk` and populate the new `run_metadata` fields (`harness_version="v1"`, `openhands_sdk_version` from installed package, `docker_image="ghcr.io/openhands/agent-server:latest-python"`). This is a small runner change — inspect `bench/runner/runner.py` (or equivalent driver) next session.
2. **Smoke run**: 1 task (medium-01) on 1 cell (coder = `qwen3-coder-30b-a3b-instruct-awq-4bit` at vLLM :8100). Requires vLLM up on port 8100 with that model served. Validates end-to-end harness before the full 2×10 run.
3. **Full run**: 2 cells × 10 tasks (`qwen3-coder-30b-a3b-instruct-awq-4bit` + `qwen3_6-35b-a3b-q4kxl-gguf`).
4. **Score via Perplexity-Max** against the 10 gold files.
5. **File ADR-0027 verdict** applying pre-registered ADR-0026 reversal criteria.

## Open questions / awaiting user answer

- none

## Exact next action

Inspect `bench/runner/runner.py` (or the CLI entrypoint that invokes `probe_coder`) to determine what runner-level change is needed to (a) route medium-tier `coder-medium-multi-turn.json` to `_probe_coder_sdk` (currently routing is likely already role/tier-based) and (b) populate the three new `run_metadata` fields per run. Single small commit.
