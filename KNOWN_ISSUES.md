# KNOWN_ISSUES.md — OpenHands-Ext v1

Running list of open, unresolved issues that block progress. Editable (not append-only).
When resolved, move the entry into `DEBUG_LOG.md` as a closed diagnosis.

---

_No open issues._

### 2026-08-11 — Deferred: embedder placement re-evaluation (4B CPU vs. 0.6B GPU co-resident)

- **Blocks:** no blockers (current ADR-0017 amendment #3 config — 4B on CPU — is working; this is an optimization question, not a bug)
- **Symptom:** Two viable embedder configs, each with tradeoffs, not yet empirically compared on production workload:
  - **Config A (current, ADR-0017 amendment #3):** `qwen3-embedding-4b-q8-gguf` on **CPU**, ctx 4096, always-resident. Highest MTEB quality (4B > 0.6B by measurable margin), zero VRAM cost, but embed latency higher (CPU inference) and CPU RAM ~5 GiB.
  - **Config B (proposed alternative):** `qwen3-embedding-0.6b-*` on **GPU** co-resident with coder. ~0.6-1 GiB VRAM at Q8_0. Coder `--gpu-memory-utilization` would need reduction from 0.90 → ~0.85 to leave room. Lower MTEB quality vs. 4B, but embed latency drops substantially (GPU).
- **Attempted fixes:** n/a — deferred until production embed-latency measurements exist under real OpenHands retrieval load.
- **Next investigation (when triggered):**
  1. Measure Config A embed latency (p50, p95) on realistic OpenHands retrieval payloads (code chunks, doc snippets — ~200–2000 tokens each) at typical batch sizes.
  2. If Config A p95 > threshold that blocks agent responsiveness, benchmark Config B against same corpus.
  3. Score MTEB quality delta on the actual retrieval task (code search) — 4B may or may not win on domain-specific data.
  4. Decision matrix: if 0.6B-GPU beats 4B-CPU on latency by ≥3× AND quality delta on the retrieval task is <5%, switch to Config B. Otherwise keep Config A.
  5. Any switch requires ADR-0017 amendment #4 documenting the empirical basis.
- **Related DEBUG_LOG search terms:** `embedder`, `ADR-0017 amendment #3`, `VRAM co-residency`, `-ngl`, `qwen3-embedding`
- **Trigger to unblock:** first sign of retrieval latency causing OpenHands agent slowdown, OR when Medium-tier planning starts and embed throughput becomes measurable.

### 2026-08-11 — llama.cpp vendor drift (b10356 installed, b10359 available)

- **Blocks:** nothing (planner + embedder PASS on b10356)
- **Symptom:** `git -C vendor/llama.cpp describe` shows `b10356` (committed 2026-08-10 19:53 UTC); `gh release view ggml-org/llama.cpp` shows `b10359` (published 2026-08-11 10:48 UTC).
- **Attempted fixes:** none — drift-tolerant policy per ADR-0018.
- **Next investigation:** review b10357..b10359 commit log if a Blackwell/SM_120 or GGUF-loader fix is announced; otherwise leave alone. Rolling-tag stream will always drift within hours.
- **Upgrade command (when needed):**
  ```bash
  cd ~/dev/openhands-ext-v1
  bash scripts/stop-large-model.sh coder
  bash scripts/stop-large-model.sh planner
  bash scripts/build-llama-cpp.sh    # rebuilds to current top-of-releases
  bash scripts/serve-embedder.sh &
  bash scripts/serve-coder.sh &
  bash scripts/check-production-endpoints.sh
  ```
- **Related DEBUG_LOG search terms:** llama.cpp, vendor, SM_120, GGUF loader

### 2026-08-11 — vLLM patch drift (0.27.0 installed, 0.27.1 available)

- **Blocks:** nothing (coder PASSes chat probe on 0.27.0 with `VLLM_USE_FLASHINFER_SAMPLER=0`)
- **Symptom:** `pip show vllm` shows `0.27.0` (published 2026-08-10 21:18 UTC); `gh release list vllm-project/vllm` top non-prerelease is `v0.27.1` (published 2026-08-11 10:47 UTC).
- **Attempted fixes:** none — drift-tolerant policy per ADR-0018.
- **Next investigation:** check 0.27.1 changelog specifically for FlashInfer sampler SM 12.0 support or CUDA 12.8 kernel fallback improvements. If either lands, motivates upgrade + potential removal of `VLLM_USE_FLASHINFER_SAMPLER=0`. Otherwise leave alone.
- **Upgrade command (when needed):**
  ```bash
  cd ~/dev/openhands-ext-v1
  source .venv/bin/activate
  bash scripts/stop-large-model.sh coder
  pip install --upgrade "vllm==0.27.1"
  bash scripts/serve-coder.sh &
  bash scripts/check-production-endpoints.sh
  # If FlashInfer sampler is now Blackwell-compatible in 0.27.1:
  #   remove `VLLM_USE_FLASHINFER_SAMPLER=0` from scripts/serve-coder.sh and retest
  ```
- **Related DEBUG_LOG search terms:** vLLM, FlashInfer, SM 12.0, CUDA 12.8
