# Kosmos Session Handoff — 2026-08-11 03:52 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.1 → Phase 0.2 (transitioning)
- **Plugin / kernel component:** coder-fast POOL closed with 3 survivors; Phase 0.2 slow tier is next for coder role (quality ranking)
- **Port(s) in progress:** none active

## Completed this session

- ADR-0011 ratified in-practice (fast-tier coder tool-call parser = hermes; commit `f76f307`).
- ADR-0012 ratified (30B thinker is dual-role coder+planner; commit `9a42313` / `920d7c7`).
- Ran real Phase 0.1 coder-fast POOL (vLLM slice only, 3 cells): 1 PASS + 2 R1 eliminated (Qwen3.5-VL multimodal, coder role has no use for vision tower).
- ADR-0013 ratified (registry exclusion: Qwen3.5-VL not coder-pool; registry-authoring rule added; commit `4aa257d`).
- GGUF metadata verified 2026-08-11 03:45 EDT: both `qwen3_6-27b-q6k-gguf` and `qwen3_6-35b-a3b-q4kxl-gguf` are text-only (0 VL tensors of 851/733; arch `qwen35` and `qwen35moe`).
- llama.cpp build state confirmed: vendor built at tag `b10356` with CUDA 13.0 + gcc-13 + SM_120 per ADR-0004. `/usr/local/cuda → cuda-13.0`, RUNPATH baked in, `llama-server --version` clean.
- Added `bench/candidates/coder-fast-pool.json` — canonical combined pool file spanning vLLM + llama.cpp cells to satisfy §0.0b min_pool=3 in one runner invocation (commit `58a741e`).
- Ran combined coder-fast POOL 2026-08-11 03:50-03:52 EDT: **3/3 PASS**.
  - `qwen3-30b-a3b-thinking-2507-awq` (vLLM 0.27.0) — pass, cold 38s.
  - `qwen3_6-27b-q6k-gguf` (llama.cpp b10356) — pass, cold 13s.
  - `qwen3_6-35b-a3b-q4kxl-gguf` (llama.cpp b10356) — pass, cold 19s.
- BUILD_LOG entries current for both pool runs. DEBUG_LOG has the multimodal-in-coder-pool root-cause entry from earlier this session. This SESSION_HANDOFF overwritten.

## Remaining before current Definition of Done

- **Coder-fast POOL is CLOSED.** All 3 candidates advance to Phase 0.2 slow tier per ADR-0007 methodology. Phase 0.1 coder role Definition of Done met.
- **Optional pre-Phase 0.2 enrichment:** pull `cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` — purpose-built coder-instruct. Belongs in coder pool on principle alongside the thinker. Would give Phase 0.2 four candidates instead of three, adding architectural diversity (coder-instruct trained specifically for tool-calling & code, distinct from thinker+parser combo). Registry entry + pull invocation pending.
- **Planner-fast POOL:** registry has only 1 planner entry (the dual-role 30B thinker via ADR-0012). §0.0b min_pool=3 for planner-fast will fail without new candidates. Deferred until user directs — options: (a) pull additional planner-flavored models, (b) use `--smoke` for verification only, (c) skip planner and go embedder-fast first (registry has 4 embedder entries, guard passes).
- **Embedder-fast POOL:** registry has 4 embedder entries (0.6B bf16, 0.6B q8 GGUF, 4B bf16, 4B q8 GGUF). Would pass §0.0b at min_pool=4. Requires embedder ROLE_FLAGS already defined; llama.cpp embedder side is `--embedding -c 4096`. vLLM embedder side needs a mode flag (`--task embed`?). To be inspected before running.
- Uncommitted at `/tmp/oh-ext`: `BUILD_LOG.md`, `SESSION_HANDOFF.md`. Need push.

## Open questions / awaiting user answer

1. Pull `cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` now to give Phase 0.2 four candidates? (My recommendation: yes.)
2. After that: which POOL next — planner (needs candidates pulled first) or embedder (already ready)? (My recommendation: embedder first — the pool is ready, guard passes, and it exercises the embedder-role code path which is otherwise unvalidated.)

## Exact next action

Commit + push these two log files, then pull `cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` — registry patch + `pull-models.sh --slug qwen3-coder-30b-a3b-instruct-awq` (or equivalent) + verify `config.json.architectures[0]` ends in `ForCausalLM` per ADR-0013 rule before adding to `roles.coder`.
