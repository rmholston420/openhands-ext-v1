# Kosmos Session Handoff — 2026-08-11 10:35 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-2 · coder correctness harness v1
- **Plugin / kernel component:** bench harness · `_probe_coder_sdk` implementation slice
- **Port(s) in progress:** Coder correctness scoring (ADR-0022 medium tier → superseded by ADR-0026 v1 harness at medium tier)

## Completed this session

- ADR-0026 authored + ratified (six decisions locked)
- ADR-0026 amendment 1: SDK 1.41.0 import path correction (`openhands.workspace.DockerWorkspace`)
- ADR-0026 amendment 2: real SDK surface locked (execute_command, file_upload, file_download, Conversation factory, callbacks, max_iteration_per_run=20, container reuse across 10 tasks per cell, LLM adapter contract for local vLLM)
- SDK freeze file `bench/runner/openhands-sdk-freeze-20260811T142200Z.txt`
- Docker smoke run passed — DockerWorkspace boots container in ~10.5 s
- Full SDK 1.41.0 surface introspected (DockerWorkspace, Agent, Conversation/LocalConversation/RemoteConversation, LLM, Event types)
- Task-set `bench/tasks/coder-medium-multi-turn.json` authored (10 tasks × 4 new fields; 422 lines)
- 10 gold rubric files authored under `bench/gold/coder-medium-multi-turn/`
- SHA-256 hashes pinned in task-set `gold_hashes` block

## Remaining before current Definition of Done

1. **Extend `bench/schema/run.py` + `bench/schema/run.schema.json`** — add `harness_version`, `openhands_sdk_version`, `docker_image` fields to `run_metadata`.
2. **Promote `_probe_coder_sdk` in `bench/runner/probes.py:418`** from stub to full implementation per ADR-0026 amendment 2 contract:
   - Construct one `DockerWorkspace` per cell (auto-boots container).
   - For each task: wipe → seed fixtures via `file_upload` (or init git for task-08) → build `LLM` targeting the cell's local endpoint → build `Agent(llm=llm, tools=[])` → build `Conversation(agent=agent, workspace=ws, callbacks=[on_event], max_iteration_per_run=20)` → `conv.send_message(task["prompt"])` → `conv.run()` → verify final state via `execute_command('cat ...')` per `expected_final_state_mode` → smoke test if `smoke_test_command` is not null → capture event trace (ActionEvent count, tool names in order, AgentErrorEvents) → persist per-task record.
   - After all 10 tasks: `ws.cleanup()`.
   - Handle `fixture_seed_failed`, `agent_error`, `max_iteration_hit` as distinct outcomes.
3. **Smoke run**: 1 task (medium-01) on 1 cell (coder = `qwen3-coder-30b-a3b-instruct-awq-4bit` at vLLM :8100) to validate the harness end-to-end.
4. **Full run**: 2 cells × 10 tasks (`qwen3-coder-30b-a3b-instruct-awq-4bit` + `qwen3_6-35b-a3b-q4kxl-gguf`).
5. **Score via Perplexity-Max** against the 10 gold files.
6. **File ADR-0027 verdict** applying the pre-registered ADR-0026 reversal criteria.

## Open questions / awaiting user answer

- none

## Exact next action

Extend `bench/schema/run.py` + `bench/schema/run.schema.json` with the three new `run_metadata` fields, then rewrite `_probe_coder_sdk` in `bench/runner/probes.py` per the ADR-0026 amendment 2 contract. Single commit.
