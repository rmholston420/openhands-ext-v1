# Kosmos Session Handoff — 2026-08-11 04:07 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.1 · Fast tier
- **Plugin / kernel component:** coder-fast POOL — expanding from 3 to 4 cells; parser plumbing complete
- **Port(s) in progress:** none active. Runner-internal changes only.

## Completed this session

- Interpreted 2026-08-11 03:52 EDT combined 3-cell coder-fast POOL result: **3/3 PASS** (vLLM thinker 38s cold, llama.cpp 27B Q6_K 13s cold, llama.cpp 35B/A3B Q4_K_XL 19s cold). Runner exit_code=0. §0.0b guard satisfied. All 3 advance to Phase 0.2 slow tier per ADR-0007.
- Committed pool-closed ledger (`1cd1a30`).
- Verified `cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit` via web search + llm-explorer metadata: `Qwen3MoeForCausalLM`, `qwen3_moe`, no `vision_config`, Apache-2.0, 16.9 GiB. Committed registry addition (`8cab7b5`).
- Pulled candidate (193s, rev `4bd30395b72e`, rollup sha `1c0f6074f956`). Manifest §0.0a snapshot for all 5 coder candidates at 04:05 EDT.
- Inspected `models/qwen3-coder-30b-a3b-instruct-awq-4bit/chat_template.jinja` (6211 chars). Confirmed Qwen3-Coder XML wire format: outer `<tool_call>` wrapping `<function=name><parameter=arg>value</parameter></function>`. Requires `--tool-call-parser qwen3_coder`, NOT the ROLE_FLAGS default `hermes`.
- Amended ADR-0011: parser is per-cell (default hermes; per-cell override via `tool_call_parser` field). Locked in registry-authoring rule mapping chat_template signature → required parser.
- Wired per-cell parser through the stack:
  - `ExpandedCandidate.tool_call_parser: Optional[str] = None` (new field).
  - `expand_for_role()` propagates from registry (GPU + CPU-embedder cells).
  - `_from_candidate_dict` propagates from `--candidate-file` rows.
  - `_make_server` for vLLM coder cells appends `--tool-call-parser <value>` to `extra_flags`.
  - `VLLMServer.__init__` unchanged (already accepted `extra_flags`; last-value-wins).
- Registry and pool file updated: `hermes` explicit on thinker, `qwen3_coder` on coder-instruct.
- All 4 files syntax-checked (2 Python parse OK, 2 JSON valid).
- DEBUG_LOG search-first done: 4 prior parser entries found (03:06/03:15/03:18 EDT). New territory (per-cell mechanism) not previously covered. Appended 2 new DEBUG_LOG entries (per-cell parser plumbing + verdict-print KeyError from post-run inspection tooling).
- BUILD_LOG appended. This SESSION_HANDOFF overwritten.

## Remaining before current Definition of Done

- Commit + push these changes to origin/main.
- **Run 4-cell coder-fast POOL** to verify the new coder-instruct passes with the qwen3_coder parser (must show `--tool-call-parser qwen3_coder` in server log launch cmd + non-empty `tool_calls[]` in the sidecar for the new cell).
- Expected outcome: all 4 pass. If coder-instruct fails with `tool_calls=[]`, the parser choice or the plumbing has a defect — inspect the sidecar's `raw_content` before reverting anything.
- After 4-cell pass: Phase 0.1 coder-fast POOL is fully closed with 4 survivors. Move to Phase 0.2 slow tier for coder role (gold-standard scoring against Perplexity Max), OR pivot to embedder-fast POOL first (registry has 4 embedder entries; §0.0b passes at min_pool=4).

## Open questions / awaiting user answer

1. After the 4-cell coder-fast POOL passes: which comes next — Phase 0.2 slow tier for coder role (quality-ranked gold-scoring), or embedder-fast POOL first (already-ready pool)? My recommendation: **embedder-fast first** — it's the fastest to execute given the pool is already sized correctly, and it validates the embedder code path which is otherwise unexercised. Slow tier for coder is a bigger investment (needs a Perplexity-gold suite generated first).

## Exact next action

Commit + push the parser-plumbing changeset, then user runs:

```bash
cd ~/dev/openhands-ext-v1
git pull --ff-only
.venv/bin/python -m bench.runner.main \
  --candidate-file bench/candidates/coder-fast-pool.json \
  --tier fast --role coder \
  --rubric bench/rubrics/fast-tier-coder-r1.json
```

(Substitute actual entry-point invocation if different — runner CLI unchanged from the prior 3-cell run.)

Then paste the run log so we can verify (a) launch cmd for cell 4 shows `--tool-call-parser qwen3_coder`, (b) all 4 cells reach `verdict=pass`, (c) sidecar for cell 4 shows non-empty `tool_calls[]` (not the DEBUG_LOG 03:15 EDT parser-mismatch failure mode).
