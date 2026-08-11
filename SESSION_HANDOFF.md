# OpenHands-Ext v1 Session Handoff — 2026-08-11 05:43 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 (Medium tier) — rubric locked; task-set authoring in progress.
- **Plugin / kernel component:** bench harness (Medium-tier tasks).
- **Port(s) in progress:** none.

## Completed this session
- ADR-0014 filed (Ratified): Coder-fast pool reinstated 2→4 cells.
- ADR-0011 amendment 3 partially reversed by ADR-0014.
- Pushed 66249e1.
- ADR-0015 filed (Proposed) + probe runs (8k, 16k).
- **ADR-0015 amended to Ratified · Confirmed** — thinker-2507-awq unfit for planner Medium (both probes malformed ≥ 2). Pushed dbfa0fd.
- **ADR-0016 filed (Ratified) 2026-08-11 05:43 EDT** — Medium-tier scoring rubric = hybrid: embedder programmatic (recall@k, MRR, nDCG@10); planner/coder Perplexity-gold (0-100). `bench/rubrics/medium-scored.json` frozen at same commit.

## Locked pool state (Fast tier)
- **Coder-Fast:** 4 cells — thinker-2507-awq (vllm), coder-30b-a3b-instruct-awq-4bit (vllm), qwen3_6-27b-q6k-gguf (llama.cpp), qwen3_6-35b-a3b-q4kxl-gguf (llama.cpp)
- **Planner-Fast:** 2 cells — qwen3_6-27b-q6k-gguf (llama.cpp/gpu), qwen3_6-35b-a3b-q4kxl-gguf (llama.cpp/gpu)
- **Embedder-Fast:** 6 cells — 0.6B ×3 + 4B ×3

## Locked pool state (Medium tier)
- **Planner-Medium (pre-authoring):** 2 cells expected — llama.cpp Fast-tier planner survivors only. thinker-2507-awq excluded (ADR-0015).
- **Coder-Medium:** to be authored. thinker-2507-awq retains eligibility (dual-role per ADR-0012).
- **Embedder-Medium:** to be authored.
- **Rubric:** locked at `bench/rubrics/medium-scored.json` per ADR-0016. Post-hoc edit prohibited.

## Phase 0.2 authoring order (confirmed by user)
1. **embedder-medium** ← next
2. planner-medium
3. coder-medium

## Remaining before current Definition of Done
- Author `bench/tasks/embedder-medium.json` + qrels file (or inline qrels).
- Extend harness with `--score` phase (recall@k / MRR / nDCG for embedder role).
- Run embedder-medium; record scores.
- Repeat for planner-medium, then coder-medium (with Perplexity-gold pipeline).

## Open questions / awaiting user answer
- **Embedder-medium corpus + query design.** Options: (a) synthetic corpus authored for OpenHands-Ext domain (code-search, doc-search over the repo itself); (b) BEIR subset (industry-standard, portable); (c) hybrid (BEIR subset + a small OpenHands-Ext-specific subset for domain fit). Need decision before task-set authoring.
- **qrels file location.** Inline in `embedder-medium.json` (smaller, one-file) vs sibling `embedder-medium-qrels.json` (cleaner if qrels grows). Decide at authoring time based on size.

## Exact next action
- Await user answer on embedder-medium corpus/query design choice, then author `bench/tasks/embedder-medium.json` + qrels + harness `--score` extension.
