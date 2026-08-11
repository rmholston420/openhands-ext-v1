# bench/ — Phase 0 Three-Tier Benchmark Campaign

Directory scaffold for the Phase 0 benchmark harness. Empty until Phase -1 completes on
Colossus and the pinned runtime versions are known.

| Directory | Contents |
|---|---|
| `fast/` | Phase 0.1 — ≤30 min triage/infeasibility tier |
| `medium/` | Phase 0.2 — ≤60 min comparative screening |
| `full/` | Phase 0.3 — <10 hr final ranking + combination test |
| `lib/` | Shared harness code (NVML sampler, ActionEvent/ObservationEvent parser, tier runner) |
| `schema/` | JSON schema for the 7-category run record (spec §0.0c) |
| `rubrics/` | Timestamped scoring rubrics — MUST be created and timestamped **before** the first scored output (spec §0.0a) |
| `results/` | Per-run JSON output; committed as evidence |

## Non-negotiable rules

1. **Timestamp every rubric before the first scored output.** No post-hoc edits (spec
   §0.0a).
2. **Never estimate a latency figure** — measure per call, report variance across 3+
   repeats (Perplexity Computer CI #5).
3. **Fast/Medium results never populate `config/`** — only Phase 0.3 winners do
   (spec §2.4, Perplexity Computer CI #2).
4. Every run emits the full 7-category JSON record including the exact `llama.cpp`
   build tag and `vLLM` release tag used (spec §0.0c, CI #4).
