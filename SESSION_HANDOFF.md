# Kosmos Session Handoff — 2026-08-11 05:20 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.1 · Fast tier · **complete for all three roles**
- **Next slice:** Phase 0.2 Medium tier authoring
- **Port(s) in progress:** none

## Fast-tier pools locked

| Role | Cells | Members |
|---|---:|---|
| Coder | 4 | thinker-2507-awq (vllm/gpu), coder-30b-a3b-instruct-awq-4bit (vllm/gpu), qwen3_6-27b-q6k-gguf (llama.cpp/gpu), qwen3_6-35b-a3b-q4kxl-gguf (llama.cpp/gpu) |
| Planner | 2 | qwen3_6-27b-q6k-gguf (llama.cpp/gpu), qwen3_6-35b-a3b-q4kxl-gguf (llama.cpp/gpu) |
| Embedder | 6 | 0.6B bf16 vllm/gpu, 0.6B Q8 llama.cpp gpu+cpu, 4B bf16 vllm/gpu, 4B Q8 llama.cpp gpu+cpu |

## Completed this session
- Coder-fast (early): pool built 4 → prior lock 2 (04:36 + 04:45 EDT).
- Planner-fast POOL run (04:57–04:59 EDT); embedder-fast POOL run (04:59–05:03 EDT). Embedder 6/6 pass.
- Diagnosed rubric-compliance bug in `_apply_fast_rubric`: single-task-malformed was being flipped to full-cell fail via `verdict_from_probe`, contradicting ratified rubric R2 (">1 malformed → eliminate"). Rubric text untouched.
- Fixed harness (commit `9d4f6b0`) + rescore tool (`scripts/rescore-fast-verdicts.py`) + import fix (`3022385`) + probe-sidecar-skip (`abefe9c`) + summarizer (`b0d44c3`).
- Rescored on Colossus. Planner-fast pool locked at 2 (27B Q6_K + 35B Q4_K_XL). Thinker-2507 legitimately eliminated on planner (R2 fail on merit: cannot honor `enable_thinking=false` at 4096-token budget).
- **Wider rescore revealed both prior coder-fast eliminations (04:36, 04:45) were made under the same rubric bug.** Rescore evidence shows `qwen3_6-27b-q6k-gguf` 4/4 pass and `qwen3-coder-30b-a3b-instruct-awq-4bit` 1 pass + 1 fail. Filed **ADR-0014**: coder-fast pool reinstated from 2 → 4 cells. ADR-0011 amended (AMENDMENT 3 partially reversed).

## Remaining before current Definition of Done
- Nothing spec-blocking. All Fast-tier pools locked.

## Open questions / awaiting user answer
- Medium-tier authoring order: coder, planner, or embedder first?
- Whether to run an optional Fast-tier confirmation smoke on the reinstated 27B Q6_K + coder-instruct AWQ (spec does NOT require it; rescored evidence is authoritative). If chosen, run against the 4-cell pool file to also re-verify the two survivors.

## Exact next action

```bash
cd ~/dev/openhands-ext-v1 && git fetch origin && git reset --hard origin/main

# Verify the 4-cell coder-fast pool file is valid and matches ADR-0014:
python3 -c "import json,sys; d=json.load(open('bench/candidates/coder-fast-pool.json')); print(f'cells={len(d)}'); [print(f'  {c[\"model\"]}  {c[\"runtime\"]}/{c[\"device\"]}') for c in d]"

# Optional confirmation smoke on the 4-cell pool (spec-optional):
# .venv/bin/python scripts/benchmark-tier-runner.py --tier fast --role coder \
#   --task-set bench/tasks/coder-fast.json \
#   --rubric bench/rubrics/fast-elimination.json \
#   --candidate-file bench/candidates/coder-fast-pool.json --smoke
```
