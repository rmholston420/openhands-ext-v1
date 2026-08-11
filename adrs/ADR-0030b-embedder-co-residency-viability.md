# ADR-0030b — Embedder co-residency viability under coder XOR planner

**Status:** Proposed (executed on ADR-0030 quality winners; verdict folded into ADR-0031)
**Lock-in phase:** Phase 0.4 gate-4 (paired with ADR-0030)
**Supersedes:** ADR-0017 amend #3 (embedder CPU placement, on the specific ground of coder+planner co-residency VRAM budget only)
**Extends:** ADR-0030 (embedder quality re-eval, three-way)
**Related:** ADR-0025 (planner Qwen3.6-27B-Q6_K llama.cpp GPU), ADR-0029 (coder Qwen3-Coder-30B AWQ vLLM GPU)

## Context

ADR-0030 was originally scoped with all three embedder candidates on **llama.cpp CPU** on the stated ground that `coder + planner + embedder` could not fit in 32 GB VRAM. Per user clarification 2026-08-11 14:43 EDT, this is factually wrong: **coder and planner never run concurrently** in Phase 1 orchestration — the runtime dispatches to one or the other per task, not both. The correct co-residency contract is:

- **Scenario A:** `coder + embedder` — agent is generating code, embedder serves retrieval for code context.
- **Scenario B:** `planner + embedder` — agent is planning/thinking, embedder serves retrieval for planning context.

Both scenarios need the embedder co-resident with a single generative model, not both.

VRAM math for the 32 GB Blackwell (RTX 5090):

**Scenario A: Coder + Embedder**

| Component | Weight (GiB) | KV/activations (GiB) | Total (GiB) | Headroom vs 32 GiB |
|---|---:|---:|---:|---:|
| Coder Qwen3-Coder-30B AWQ-4 | ~17 | ~4-6 | ~21-23 | — |
| Embedder 0.6B Q8_0 | 0.6 | ~0.3 | ~1 | ~8-10 GiB |
| Embedder 4B Q8_0 | 4.0 | ~1-2 | ~5-6 | ~3-6 GiB |
| Embedder 8B Q6_K | 5.8 | ~1-2 | ~7-8 | ~1-4 GiB (tight) |

**Scenario B: Planner + Embedder**

| Component | Weight (GiB) | KV/activations (GiB) | Total (GiB) | Headroom vs 32 GiB |
|---|---:|---:|---:|---:|
| Planner Qwen3.6-27B Q6_K | ~22 | ~2-3 | ~24-25 | — |
| Embedder 0.6B Q8_0 | 0.6 | ~0.3 | ~1 | ~6-7 GiB |
| Embedder 4B Q8_0 | 4.0 | ~1-2 | ~5-6 | ~1-3 GiB (tight) |
| Embedder 8B Q6_K | 5.8 | ~1-2 | ~7-8 | **~-1 GiB (overrun)** |

**A-priori feasibility summary:**
- **0.6B**: co-resides in both scenarios with comfortable headroom.
- **4B**: co-resides in Scenario A comfortably; tight in Scenario B.
- **8B**: co-resides in Scenario A tightly; **does not fit** in Scenario B — requires embedder unload/reload on every plan→code transition.

VRAM math alone cannot decide the winner because:
1. Live activations may deviate from static estimates (attention window, batch size effects).
2. Contention effects on throughput and tail latency are not captured by budget math.
3. The router (Phase 1 dispatcher) has non-zero swap cost if the embedder must unload/reload.

## Decision

Author ADR-0030b as a **separate Proposed ADR paired with ADR-0030**, with the following methodology:

### Sub-decision 1 — Which candidates are measured

Only candidates that survive ADR-0030's quality gate are measured under co-residency. Specifically:

- **Incumbent** (`e04b_q8_cpu`): always measured (baseline).
- **Upsize challenger** (`e08b_q6k_cpu`): measured if ADR-0030 shows meaningful quality lift over incumbent per §Reversal Criteria V3 predicate.
- **Downsize challenger** (`e006b_q8_cpu`): measured if ADR-0030 shows the downsize does not violate the W3 strict guard.

Candidates that fail their ADR-0030 quality gate are not measured for viability — they lose on quality regardless of viability.

### Sub-decision 2 — Contention scenarios

For each surviving candidate, run two contention tests:

- **Test A (Coder contention):** Start coder (vLLM, Qwen3-Coder-30B AWQ) at its normal `--gpu-memory-utilization` setting, then start embedder (llama.cpp, `-ngl 999`) alongside. Warm coder + embedder with a short warmup batch. Then run 60 seconds of coder inference (a small generation loop on a benchmark prompt) **concurrently** with 60 seconds of embedder inference (looped batch-16 embeds of a fixed chunk set).
- **Test B (Planner contention):** Same protocol with planner (llama.cpp, Qwen3.6-27B-Q6_K) replacing coder.

### Sub-decision 3 — Metrics captured

Per (candidate, scenario) cell, capture:

- **Embedder latency:** p50, p95, p99 per embed request (batch-16). Measured client-side (curl wrapping) and server-side (`slot print_timing` log).
- **Coder/planner throughput degradation:** tokens/sec generated under contention vs solo baseline. Solo baseline captured in a preceding 60-sec run without embedder loaded.
- **VRAM peak:** `nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits` sampled every 1 sec during the run; report peak.
- **Startup swap cost:** wall-clock time for embedder to serve its first request after `llama-server` process start with `-ngl 999` and the model already in page cache. Sampled 3 times per candidate; report median. This is the cost the router would pay on a plan↔code transition if the embedder had to unload.

### Sub-decision 4 — Verdict criteria for viability

A candidate is **viable** for the intended runtime if, in **both** contention scenarios:

- Embedder p99 latency under contention < 500 ms for batch-16 (approx 2× solo baseline is acceptable).
- Coder or planner throughput degradation < 15%.
- No OOM. No VRAM overrun beyond `--gpu-memory-utilization` budgets.

A candidate is **viable-with-swap** if it fails contention in one scenario but the startup swap cost is < 2 seconds (acceptable to route-level unload/reload).

A candidate is **not-viable** otherwise.

### Sub-decision 5 — ADR-0031 verdict combination

ADR-0031 picks the winner as follows:

1. Filter candidates by ADR-0030 quality: any candidate that fails its per-role reversal predicate (V3 for upsize, W3 for downsize) is eliminated.
2. Filter surviving candidates by ADR-0030b viability: **viable > viable-with-swap > not-viable**.
3. Among tied viability tiers, pick the candidate with the highest ADR-0030 composite score.

If the incumbent (`e04b_q8_cpu`) survives both filters, verdict is CONFIRM incumbent. Otherwise verdict is FLIP to the surviving winner.

## Alternatives considered

1. **Skip co-residency measurement, decide on quality alone (Q1).** Rejected. Quality without viability is a paper win; a candidate that wins quality but requires per-turn embedder swap is worse in practice than a quality-matched candidate that co-resides cleanly.
2. **Measure co-residency for all three candidates regardless of quality (V1).** Rejected. Wastes ~30 min of contention testing on candidates that lose on quality. The quality gate is cheap; run it first.
3. **Include unload/reload swap as a first-class measurement axis (S1).** Deferred. Startup swap cost is captured (Sub-decision 3) but does not become a first-class filter unless a candidate is not-viable under co-residency; then it falls to viable-with-swap. Escalating swap-cost to a primary axis is a future ADR if Phase 1 router shows swap penalty dominates.
4. **Test co-residency with both coder AND planner simultaneously (T1).** Rejected. User confirmed coder XOR planner in Phase 1 orchestration; testing an unreachable scenario adds no signal.
5. **Change the embedder role designation to per-scenario (P1).** Rejected as premature. The Phase 1 dispatcher decides scenarios, not the embedder. If a candidate is viable in only one scenario, it becomes not-viable overall — the dispatcher does not swap embedders per turn.

## Consequences

- **Runner extension (deferred):** ADR-0030b execution needs a `probe_embedder_coresidency()` peer to the existing `probe_embedder_full_multi_block()`. Draft after ADR-0030 completes; not a blocker for ADR-0030 completion.
- **Coder + planner startup scripts (required):** the vLLM coder start script and llama.cpp planner start script must be documented and idempotent by the time ADR-0030b executes. These already exist for Phase 0.3 (ADR-0025, ADR-0029 references).
- **ADR-0017 amend #3 partially superseded:** the CPU placement decision is superseded specifically for the `coder+planner+embedder` co-residency ground, which was mis-scoped. The CPU placement remains valid for any future scenario where the embedder must not consume VRAM (e.g., if a Phase 2 role needs its own GPU footprint). File an ADR-0017 amend #4 when ADR-0031 confirms the ADR-0030 winner, formally moving embedder placement to GPU in the router config.
- **Post-hoc-edit-locked artifacts unchanged.** No changes to queries, rubric, gold labels, or corpus manifest.

## Lock-in phase

Proposed at time of ADR-0030 SCOPE-RESTORATION amendment (2026-08-11 14:55 EDT). Ratified when its own execution artifacts are committed (viability CSVs, contention log samples). Consumed by ADR-0031 verdict.

## References

- `adrs/ADR-0030-phase-0-4-embedder-full-tier-re-eval.md` — pairs with this ADR for the quality+viability decision
- `adrs/ADR-0017-production-role-selection-pre-medium.md` amend #3 — CPU placement decision partially superseded (grounds only)
- `adrs/ADR-0025-planner-migration-probe-verdict-confirm-adr-0023.md` — planner role, referenced for scenario B
- `adrs/ADR-0029-phase-0-3-gate-3-coder-verdict-confirm-awq.md` — coder role, referenced for scenario A
- `PORTING_LEDGER.md` — llama.cpp CUDA build (build-cuda for SM_120a Blackwell, added this session)
