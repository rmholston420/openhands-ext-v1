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
