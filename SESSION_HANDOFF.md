# Kosmos Session Handoff — 2026-08-11 03:37 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.1 · Fast tier
- **Plugin / kernel component:** coder pool composition (`bench/candidates/registry.json` `roles.coder`)
- **Port(s) in progress:** none active; coder-fast POOL not closed — needs repopulation before §0.0b `min_pool=3` is met with real text-only candidates

## Completed this session

- Launcher-flag mechanism verified (ADR-0010 amended by ADR-0011; both ratified in-practice; commit `f76f307` / `84adc1a`).
- Registry amended for dual-role 30B thinker (ADR-0012 ratified; commit `9a42313` / `920d7c7`).
- Ran real Phase 0.1 coder-fast POOL against `bench/candidates/coder-fast-vllm.json` (3 vLLM cells):
  - `qwen3-30b-a3b-thinking-2507-awq` — **PASS**. 5/5 tool_calls; wall p50=1.14s, p95=5.06s, cold=29.0s. VRAM peak 30660 MiB, util 94.9%, temp 51 °C.
  - `qwen3_6-27b-int4-autoround` — **R1 launch_failure** (torch.OutOfMemoryError during KV profiling; Qwen3.5-VL multimodal, vision tower consumed ~12 GiB beyond text weights).
  - `qwen3_6-35b-a3b-awq` — **R1 launch_failure** (same class of failure; Qwen3.5-VL, 22.23 GiB weights + vision + KV → OOM).
- ADR-0013 filed and ratified: Qwen3.5-VL (`Qwen3_5*ForConditionalGeneration`) excluded from coder + planner pools; registry-authoring rule added (`architectures[0]` must end in `ForCausalLM`, or model card must document text-only path).
- `bench/candidates/registry.json` amended: removed `qwen3_6-27b-int4-autoround` + `qwen3_6-35b-a3b-awq`. Registry now lists 4 coder entries.
- Logs current: DEBUG_LOG entry (multimodal-in-coder-pool → torch.OutOfMemoryError symptom + fix + files) and BUILD_LOG entry (pool run + verdicts + stop-condition status). This SESSION_HANDOFF overwritten.

## Remaining before current Definition of Done

- Coder-fast pool has **1 vLLM survivor** — below `min_pool=3` for a real Phase 0.1 fast-tier elimination. To close the coder-fast gate for real, either:
  - (a) Verify the two llama.cpp GGUF entries (`qwen3_6-27b-q6k-gguf`, `qwen3_6-35b-a3b-q4kxl-gguf`) are text-only (check GGUF metadata via `llama-gguf-inspect` or the model card, not just the file), and smoke them via the llama.cpp launcher (`LlamaCppServer.ROLE_FLAGS`). If they are Qwen3.5-VL GGUFs, they must be excluded under ADR-0013 too.
  - (b) Pull additional text-only vLLM coder candidates. Concrete options to add to `bench/candidates/registry.json`: `Qwen3-Coder-30B-A3B-Instruct-*-AWQ` (Alibaba official coder), `DeepSeek-Coder-V2-Lite-16B-AWQ`, `Codestral-22B-v0.1-AWQ`. Each must have `config.json.architectures[0]` ending in `ForCausalLM` per ADR-0013.
- Local uncommitted changes (unpushed): `adrs/ADR-0013-*.md`, `adrs/README.md`, `bench/candidates/registry.json`, `BUILD_LOG.md`, `DEBUG_LOG.md`, this `SESSION_HANDOFF.md`. Result files already exist on Colossus at `bench/results/phase-0-fast-coder-*20260811T07*.json` — those live in the Colossus checkout and should be committed on that side alongside the ADR-0013 pull.
- No open ADRs; no open guard suppression.

## Open questions / awaiting user answer

1. Verify + include the two GGUF cells (path a), or pull new text-only vLLM candidates (path b), or both. My recommendation is (b) — the coder role wants a real coder-instruct model; the 30B thinker passed only because ADR-0011 got the parser right, not because a thinker is the best coder. Path (a) may reveal the GGUFs are also VL-tainted, giving no net pool growth.
2. Result files landed in Colossus checkout (`bench/results/phase-0-fast-coder-*`) but were not committed. Confirm whether to submit them in the next commit or leave them in Colossus's working tree.

## Exact next action

Commit + push the three docs + ADR-0013 + registry amendment from this session (agent checkout `/tmp/oh-ext`). Then pull on Colossus and decide between path (a) and (b) for pool repopulation.
