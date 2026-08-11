# Kosmos Session Handoff — 2026-08-11 11:40 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-2 · stage-2 → stage-3 transition
- **Plugin / kernel component:** bench/runner/probes.py (coder multi-turn correctness harness v1.1)
- **Port(s) in progress:** LLMPort (coder role · AWQ path); scoring stage (Perplexity-Max gold + rubric)

## Completed this session

- Diagnosed + fixed LLM transport (host↔container via 172.17.0.1 + 0.0.0.0 bind) — commit `034dad6`
- Diagnosed + fixed empty `tools=[]` in Agent construction — commit `4c05562`
- Diagnosed + fixed `default_tools` scoping (thread as kwarg to `_run_sdk_task`) — commit `8963a10`
- Stage-2 gate FIRST PASS at commit `8963a10` (10/10 tasks, 0 agent_errors, 129.7s run, 94s probe, artifact `20260811T152400Z`) — but `tool_trace` was `list[str]` (tool names only)
- Authored ADR-0026 amendment 3: bundled all four wire-up fixes (transport + tools + scoping + trace schema v1 → v1.1) + task-10 mode clarification
- Expanded `_on_event` to build `tool_trace: list[dict]` with `{tool, args, success, observation}` — commit `74e17ae`
- Stage-2 gate REGENERATED at commit `74e17ae` with v1.1 trace (artifact `20260811T153712Z`)

## Canonical stage-2 artifact (ready for stage-3 scoring)

- Path: `bench/results/smoke/smoke-medium-coder-qwen3-coder-30b-a3b-instruct-awq-4bit-vllm-gpu-20260811T153712Z.probe.json`
- Sidecar: `bench/results/smoke/smoke-medium-coder-qwen3-coder-30b-a3b-instruct-awq-4bit-vllm-gpu-20260811T153712Z.json`
- `harness_version`: v1.1
- `openhands_sdk_version`: 1.41.0
- `harness_commit_sha`: 74e17ae
- Cell verdict: pass · 10/10 tasks · 0 agent_errors · 0 run_errors
- Tools observed exercising: `file_editor` (view + str_replace + create), `terminal`, `think`, `finish`

## Invalidated stage-2 artifacts (retained on disk per "never rm bench/results/*.json" rule)

- `20260811T151156Z` — tools=[] Action/Error loop (pre-`4c05562`)
- `20260811T152029Z` — NameError on default_tools (pre-`8963a10`)
- `20260811T152400Z` — first PASS run but v1 trace (list[str]; superseded by `20260811T153712Z`)

## Remaining before current Definition of Done

- **Stage-3: score against Perplexity-Max gold.** Feed `20260811T153712Z.probe.json` + rubric + gold to the scoring stage. Rubric at `bench/rubrics/coder-medium-multi-turn.rubric.json` (locked, `post_hoc_edit_locked=true`). Gold at `bench/gold/coder-medium/` (locked).
- Pre-registered reversal criteria (POST-HOC INTERPRETATION PROHIBITED):
  1. Flip to `qwen3_6-35b-a3b-q4kxl-gguf` if ALL 10 scores ≥85 AND macro lead >3 pts
  2. Confirm ADR-0023 coder if AWQ macro leads ≥3 pts OR 35b <70 on any 2 tasks
  3. Intermediate: confirm + log per-task mix
- After scoring, author verdict ADR (ADR-0027 or amendment to ADR-0023, TBD by outcome shape).

## Open questions / awaiting user answer

- **Stage-3 execution mode.** Options:
  - (a) Feed the artifact + rubric + gold to Perplexity Max (this thread) for immediate scoring — no additional Colossus work needed.
  - (b) Score the sole AWQ candidate now; the 35b-a3b-q4kxl fallback candidate would need its own stage-2 pass (~2 min) before the reversal criteria can be evaluated.
- Recommendation: (b) — even if AWQ scores ≥85 across the board, the reversal criteria require comparison against 35b. Running 35b now costs one extra 2-min stage-2 pass and unblocks the full verdict decision tree.

## Exact next action

Ask user: "Run stage-2 on the 35b-a3b-q4kxl fallback candidate now (2 min) so both candidates can be scored in one shot? Or score the AWQ candidate alone first and decide about 35b after?"
