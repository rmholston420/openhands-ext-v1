# Kosmos Session Handoff — 2026-08-11 10:27 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-2 · coder correctness harness v1
- **Plugin / kernel component:** bench harness · `_probe_coder_sdk` implementation slice
- **Port(s) in progress:** Coder correctness scoring (ADR-0022 medium tier → superseded by ADR-0026 v1 harness at medium tier)

## Completed this session

- ADR-0026 authored + ratified (six decisions: DockerWorkspace, Perplexity-Max scoring 0-100, supersede at medium tier only, new task-set `coder-medium-multi-turn.json`, SDK pin captured, D4 co-residency envelope 12-34 min)
- ADR-0026 amendment 1: SDK 1.41.0 import path correction (`openhands.workspace.DockerWorkspace`)
- SDK freeze file `bench/runner/openhands-sdk-freeze-20260811T142200Z.txt` (versions locked at 1.41.0)
- Docker smoke run succeeded — DockerWorkspace boots container in ~10.5 s
- Full SDK 1.41.0 surface introspected: DockerWorkspace, Agent, Conversation factory + LocalConversation/RemoteConversation, LLM, Event types
- ADR-0026 amendment 2: real SDK surface locked (execute_command, file_upload, file_download, Conversation(agent=..., workspace=..., callbacks=..., max_iteration_per_run=20), event capture via callback, container reuse across 10 tasks per cell, LLM adapter contract for local vLLM)

## Remaining before current Definition of Done

1. **Author `bench/tasks/coder-medium-multi-turn.json`** — 10 tasks derived from existing `coder-medium.json`, extended with `expected_final_state` (path → expected content), `smoke_test_command` (per task, optional), `reversal_criteria` (pre-registered per ADR-0026), and `gold_hashes` (computed post-gold-authoring).
2. **Author 10 gold rubric files** at `bench/gold/coder-medium-multi-turn/coder-medium-01-*.md` … `coder-medium-10-*.md` — three-input rubric (tool sequence, final file state, code correctness), 0-100 bands.
3. **Compute SHA-256 hashes** of the 10 gold files and pin them in the task-set JSON `gold_hashes` block.
4. **Extend `bench/schema/run.py` + `bench/schema/run.schema.json`** — add `harness_version`, `openhands_sdk_version`, `docker_image` fields to `run_metadata`.
5. **Promote `_probe_coder_sdk` in `bench/runner/probes.py:418`** from stub to full implementation per the contract locked in ADR-0026 amendment 2 (fixture-seed → Conversation.run → verify → smoke test → event trace persistence).
6. **Smoke run**: 1 task on 1 cell (coder cell = `qwen3-coder-30b-a3b-instruct-awq-4bit` at vLLM :8100) to validate the harness end-to-end before the full 2×10 run.
7. **Full run**: 2 cells (`qwen3-coder-30b-a3b-instruct-awq-4bit` + fallback `qwen3_6-35b-a3b-q4kxl-gguf`) × 10 tasks.
8. **Score via Perplexity-Max** against the 10 gold files.
9. **File ADR-0027 verdict** applying the pre-registered ADR-0026 reversal criteria.

## Open questions / awaiting user answer

- none

## Exact next action

Author `bench/tasks/coder-medium-multi-turn.json` (derived 1:1 from `bench/tasks/coder-medium.json` with the four new fields per task) + the 10 gold files at `bench/gold/coder-medium-multi-turn/` in a single agent commit. This is a volume-heavy write; scope is fully determined by ADR-0026 amendment 2 + the existing `coder-medium.json` shape.
