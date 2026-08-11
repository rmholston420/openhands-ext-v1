# Kosmos Session Handoff — 2026-08-11 03:19 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.1 · Fast tier
- **Plugin / kernel component:** `bench/runner/server.py::VLLMServer` role-flag policy (ADR-0010 + ADR-0011)
- **Port(s) in progress:** none active; fast-tier smoke gate for the coder cell is unblocked

## Completed this session

- ADR-0010 filed and ratified — `VLLMServer.ROLE_FLAGS` mechanism (per-role vLLM launch flags mirroring `LlamaCppServer.ROLE_FLAGS`). Coder role gains `--enable-auto-tool-choice`, `--tool-call-parser <name>`, `--reasoning-parser qwen3`. Planner gains `--reasoning-parser qwen3`. Embedder gains nothing.
- `bench/runner/server.py::VLLMServer.__init__` gains required `role: str` kwarg + `ROLE_FLAGS` dict; `main.py::_make_server` plumbed to pass `role=role_str`.
- `bench/runner/probes.py` gains `HttpPostError` so vLLM's validation error bodies land in probe `detail` (up to 1024 chars) instead of being swallowed by `HTTPError.__str__`. All three transport-error catch sites (planner probe, embedder probe, coder-fallback) catch it first.
- ADR-0011 filed and ratified — amends ADR-0010's coder `--tool-call-parser` value from `qwen3_coder` to `hermes`. `qwen3_coder` in vLLM 0.27 targets Qwen3-Coder XML wire format; Qwen3-Thinking-2507 emits Hermes-style `<tool_call>{json}</tool_call>`, matched by the `hermes` parser (`Hermes2ProToolParser`, regex `<tool_call>(.*?)</tool_call>|<tool_call>(.*)`). ADR-0010 status → `Amended · see ADR-0011`.
- Coder-fast smoke re-verified 2026-08-11 03:18 EDT: **PASS 5/5** on `qwen3-30b-a3b-thinking-2507-awq/vllm/gpu`. Each task returns populated `tool_calls[0].function.name` + JSON `arguments`; `content=""`; `finish_reason=stop`. VRAM peak 30753 MiB, temp peak 51 °C, NVML coverage 100 %.
- All commits pushed: last SHA `f76f307` on `origin/main`. Pending in-checkout: BUILD_LOG + DEBUG_LOG verification append + this SESSION_HANDOFF.

## Remaining before current Definition of Done

- Widen the coder-fast smoke past a single-candidate file. Options:
  - Run the full real coder-pool candidate file (not `/tmp/single-coder.json`) and gate every candidate through the smoke.
  - Or move on to planner-fast full-matrix (planner-fast smoke already passed earlier under ADR-0008/0009; ADR-0010 landed the launch-flag mechanism it needed).
- No open ADRs. No open guard suppression (`--smoke` still bypasses §0.0b only; `--rubric` still required).

## Open questions / awaiting user answer

- Should the next step be (a) widen coder-fast to the full pool, or (b) pivot to planner-fast full-matrix, or (c) drop into embedder-fast?

## Exact next action

Commit + push the three log updates from this session (BUILD_LOG, DEBUG_LOG, SESSION_HANDOFF). Then await user decision on the next fast-tier gate scope.
