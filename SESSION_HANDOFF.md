# OpenHands-Ext v1 Session Handoff — 2026-08-11 11:53 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.3 gate-2 — **CLOSED**
- **Plugin / kernel component:** Coder role selection (production routing)
- **Port(s) in progress:** None. Next gate (0.3 gate-3) not yet opened; ADR-0028 reserved.

## Completed this session

- Committed default_tools kwarg fix (`8963a10`)
- First stage-2 pass at tool_trace v1 (10/10) — trace schema flagged as under-specified (`list[str]`)
- Authored ADR-0026 amendment 3 (transport + tools + scoping + trace schema v1.1); committed (`74e17ae`)
- Rewrote `_on_event` to emit `tool_trace: list[dict]` with ActionEvent↔ObservationEvent FIFO correlation; bumped harness_version v1→v1.1 in probes.py + task-set file
- Regenerated AWQ stage-2 artifact at v1.1 (10/10 pass): `smoke-medium-coder-qwen3-coder-30b-a3b-instruct-awq-4bit-vllm-gpu-20260811T153712Z.probe.json`
- Committed SESSION_HANDOFF + BUILD_LOG (`faa30e6`)
- Added stage-2 candidate file for 35b fallback: `bench/candidates/coder-medium-stage2-35b.json` (`215fb14`)
- Ran 35b stage-2 (10/10 pass): `smoke-medium-coder-qwen3_6-35b-a3b-q4kxl-gguf-llama-cpp-gpu-20260811T154307Z.probe.json`
- Scored both candidates (Perplexity Max, gold-bounded, post_hoc_edit_locked): AWQ macro 85.4, 35b macro 88.7
- Applied pre-registered reversal criteria mechanically; verdict robust to strict/loose <70 reading
- Filed **ADR-0027** (Phase 0.3 gate-2 coder verdict: CONFIRM AWQ) + updated adrs/README.md index
- BUILD_LOG entry appended; this SESSION_HANDOFF overwritten

## Remaining before current Definition of Done

- None. Phase 0.3 gate-2 DoD met. Coder-medium production role locked as AWQ (`qwen3-coder-30b-a3b-instruct-awq-4bit`, vLLM, GPU, :8501).

## Open questions / awaiting user answer

- **Gate-3 opener:** which role to attack next (planner Full-tier vs coder Full-tier vs embedder re-eval)? ADR-0028 reserved for whichever the user chooses.
- **35b T05/T08 finish-omission follow-up:** filed as non-blocking in ADR-0027 §Sub-decision 6. Investigate opportunistically. Decision on when to characterize: after user selects gate-3 target.

## Exact next action

Await user direction on Phase 0.3 gate-3 opener. When directed, load `kosmos-adr-authoring` + `local-llm-bench` and open ADR-0028 skeleton for the selected role.

## Key production selections locked as of this handoff

- **Coder (Medium):** `qwen3-coder-30b-a3b-instruct-awq-4bit` — vLLM, GPU, port :8501 (ADR-0017 + ADR-0023 + ADR-0027)
- **Planner (Medium):** `qwen3_6-27b-q6k-gguf` — llama.cpp, GPU, port :8082 (ADR-0023 + ADR-0025)
- **Embedder:** `qwen3-embedding-4b-Q8_0` (ADR-0017)
- **Co-residency:** Option 2 (ADR-0017)
