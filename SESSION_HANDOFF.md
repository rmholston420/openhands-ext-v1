# OpenHands-Ext v1 Session Handoff — 2026-08-11 05:40 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.1 complete, Phase 0.2 (Medium-tier) authoring **unblocked**.
- **Plugin / kernel component:** bench harness (Medium-tier tasks pending).
- **Port(s) in progress:** none.

## Completed this session
- ADR-0014 filed (Ratified): Coder-fast pool reinstated 2→4 cells after harness rubric-compliance fix (9d4f6b0) invalidated the two prior eliminations. Rubric file untouched.
- ADR-0011 amendment 3 partially reversed by ADR-0014; ADR-0011 marked accordingly in index.
- Pushed 66249e1.
- ADR-0015 filed (Proposed): Pre-registered budget-hypothesis probe for thinker-2507-awq on planner role. Two probes (8k, 16k) sequential with immutable Falsified/Confirmed criteria.
- Pushed c5c3a95.
- Ran Probe A (budget=8192) — malformed 2/3, median wall 16.2s. Did NOT falsify H0; escalated to Probe B per pre-registered ladder.
- Ran Probe B (budget=16384) — malformed 2/3 again, task 01 wall 74.2s (2× Probe A), task 03 regressed to schema violation.
- **ADR-0015 amended to Ratified · Confirmed** (2026-08-11 05:38 EDT): thinker-2507-awq unfit for planner Medium-tier pool. Corrected failure diagnosis (planner-role structural incompatibility, not budget-bound, not think-block-bound).

## Locked pool state (Fast tier)
- **Coder-Fast:** 4 cells — thinker-2507-awq (vllm), coder-30b-a3b-instruct-awq-4bit (vllm), qwen3_6-27b-q6k-gguf (llama.cpp), qwen3_6-35b-a3b-q4kxl-gguf (llama.cpp)
- **Planner-Fast:** 2 cells — qwen3_6-27b-q6k-gguf (llama.cpp/gpu), qwen3_6-35b-a3b-q4kxl-gguf (llama.cpp/gpu)
- **Embedder-Fast:** 6 cells — 0.6B ×3 + 4B ×3

## Locked pool state (Medium tier)
- **Planner-Medium (pre-authoring):** 2 cells expected — llama.cpp Fast-tier planner survivors only. thinker-2507-awq excluded (ADR-0015).
- **Coder-Medium:** to be authored. thinker-2507-awq retains eligibility here (dual-role per ADR-0012; Fast-tier 5/5 pass on coder).
- **Embedder-Medium:** to be authored.

## Remaining before current Definition of Done
- Author Phase 0.2 Medium-tier task set(s). Order TBD by user.
- Decide whether Medium-tier gets its own scored-rubric ADR (Medium is first scored tier, not elimination-only) — likely required before first Medium task set lands.

## Open questions / awaiting user answer
- **Phase 0.2 authoring order.** Recommendation: embedder → planner → coder. Reasons: (1) embedder is the smallest task-surface (single latency+recall benchmark, no rubric); (2) planner Medium pool is already 2 cells so authoring the task set produces immediate scored evidence with no discovery risk; (3) coder Medium pool is largest and will benefit from planner-tier rubric shape landing first.
- **Scored-rubric ADR timing.** Author before or after first Medium task set? Recommendation: before, because Medium is elimination-plus-scoring (different rubric shape than Fast's elimination-only).

## Exact next action
- Await user answer on Phase 0.2 authoring order.
