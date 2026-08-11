# OpenHands-Ext v1 Session Handoff — 2026-08-11 02:56 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.1 · Fast-tier planner probe · smoke gate CLEARED.
- **Plugin / kernel component:** `bench/runner/probes.py::probe_planner` + `bench/tasks/planner-fast.json`.
- **Port(s) in progress:** none. Fast-tier planner probe contract is now locked (ADR-0008 + ADR-0009).

## Completed this session
- Diagnostic gap fixed: `TaskResult.raw_content` sidecar (commit 94bafbb).
- ADR-0008: Fast tier disables thinking mode for planner via `chat_template_kwargs` (commit bd09e1a).
- ADR-0009: Fast-tier planner uses OpenAI-compat guided decoding via `response_format=json_schema, strict=true` (commit 1fa2495).
- Task calibration: `planner-fast-02.min_steps` 4→3 to match natural DAG (commit ab5ff74).
- **Verified end-to-end on Colossus (smoke run 20260811T065511Z): `overall verdict: pass`, all 3 planner-fast tasks pass, 2s total probe time, VRAM 30648 MiB, temp 49 °C, NVML coverage 100%.**

## Remaining before Phase 0.1 Definition of Done
- Coder-fast probe smoke gate. Task set `bench/tasks/coder-fast.json` (if it exists) + `probe_coder` need the same shakedown against a real coder candidate (e.g. `qwen3-coder-30b-a3b-instruct` or similar).
- Multi-candidate pool run (drop `--smoke` and `--candidate-file /tmp/single-plan.json`, use the real pool config).
- Rank candidates and record verdict in an ADR per ADR-0007 methodology.

## Open questions / awaiting user answer
- None. Fast-tier planner probe is production-ready for pool bake.

## Exact next action
1. Confirm which coder-fast candidate set to bake first, then run:

    ```bash
    cd ~/dev/openhands-ext-v1 && source .venv/bin/activate
    export CUDA_VISIBLE_DEVICES=0
    pkill -x ollama 2>/dev/null; pkill -f "vllm serve" 2>/dev/null; sleep 2

    .venv/bin/python scripts/benchmark-tier-runner.py \
      --tier fast --role coder --smoke \
      --task-set bench/tasks/coder-fast.json \
      --rubric bench/rubrics/fast-elimination.json \
      --candidate-file /tmp/single-coder.json
    ```

2. If the coder probe fails R2 in the same prose-instead-of-tool-call mode, apply the same guided-decoding pattern to tool-calling via `tool_choice="required"` + a strict tool-schema.
