# ADR-0017 — Production role selection (pre-Medium-tier)

**Status:** Ratified
**Lock-in phase:** Phase 0.2 (Medium-tier authoring paused) → Phase 1 handoff
**Supersedes:** —

## Context

The user has paused Medium-tier benchmarking mid-authoring and asked for
immediate production role assignments — one coder, one planner, one
embedder — so downstream OpenHands work can proceed without waiting for
Medium-tier scored evidence.

Available evidence at decision time:
- Fast-tier candidate pools closed at the following sizes (per prior ADRs):
  - Coder-Fast: 4 cells (ADR-0014 reinstatement).
  - Planner-Fast: 2 llama.cpp cells (ADR-0015 confirmed thinker-2507-awq unfit for planner Medium).
  - Embedder-Fast: 6 cells (0.6B × 3 runtimes/devices + 4B × 3 runtimes/devices).
- Medium-tier scoring rubric locked at `bench/rubrics/medium-scored.json` (ADR-0016 hybrid).
- No Medium-tier scored results exist on disk yet.
- Pool-note "rescored" claims are compacted-summary state, not currently
  independently verifiable from result JSONs in `bench/results/`.

The user directive was: "make optimal choices" — a re-invocation of the
standing "make optimal choices" rule in the project instructions.

## Decision

Assign production roles as follows, effective immediately:

| Role | Model | Runtime | Device | Rationale anchor |
|---|---|---|---|---|
| **coder** | `qwen3-coder-30b-a3b-instruct-awq-4bit` | vLLM | GPU | ADR-0011 (parser `qwen3_coder`) + purpose-built coder-instruct |
| **planner** | `qwen3_6-35b-a3b-q4kxl-gguf` | llama.cpp | GPU | ADR-0015 (thinker-2507-awq eliminated) + MoE decoding advantage |
| **embedder** | `qwen3-embedding-4b-q8-gguf` | llama.cpp | GPU | 4B > 0.6B on MTEB; Q8_0 near-lossless on embedders; ~5 GiB VRAM |

**Co-residency policy: Option 2 — single-role-at-a-time for large models.**

- Only one of {coder, planner} may hold VRAM at any moment.
- Embedder is always resident (~5 GiB, fits alongside either large model).
- Switching between coder and planner requires stopping the current large
  model's server before starting the other. Cold-start cost is accepted as
  the price of not building a router prematurely.

## Rationale

### Coder pick
- **Purpose-built coder-instruct model** trained specifically for tool use.
  OpenHands agent loops are tool-call-dominated (edit / bash / read); a
  coder-instruct model beats a generalist thinker on tool-call discipline
  per Qwen's own model-card guidance.
- **ADR-0011 amendment 1** already mandates `qwen3_coder` tool-call parser
  for this model; the wiring is done.
- **VRAM headroom:** ~17 GiB weights + ~13 GiB KV budget at 32k ctx on a
  32 GiB 5090. Room for the resident 5 GiB embedder alongside.
- **Rejected alternatives:**
  - `qwen3-30b-a3b-thinking-2507-awq` (dual-role per ADR-0012): stronger
    reasoning but weaker tool discipline; kept as a Medium-tier candidate,
    not selected for production coder role today.
  - `qwen3_6-35b-a3b-q4kxl-gguf`: reserved for planner role in this ADR.
  - `qwen3_6-27b-q6k-gguf`: dense-27B is a smaller model class than the
    MoE-30B coder-instruct; no advantage at this VRAM budget.

### Planner pick
- **ADR-0015 (Ratified · Confirmed)** eliminates `thinker-2507-awq` from
  planner Medium tier. That leaves only the two llama.cpp survivors as
  admissible planner candidates.
- **35B/A3B MoE > dense 27B Q6_K** for planner role because:
  - More "planning surface" (35B total parameters) at the same VRAM cost.
  - MoE routing produces faster wall-time on long structured JSON output,
    which planner prompts emit.
  - Both fit at 32k ctx with Q8_0 KV cache.
- **Thinking mode:** disabled per ADR-0008 at Fast tier. Not re-enabled
  here; revisit only with Medium-tier scored evidence.
- **Rejected alternative:** `qwen3_6-27b-q6k-gguf` — same VRAM, smaller
  parameter count, no MoE speed advantage.

### Embedder pick
- **4B outranks 0.6B uniformly on MTEB** for Qwen3-Embedding family per
  published Qwen model-card benchmarks. Retrieval quality dominates.
- **Q8_0 quantization is near-lossless on embedders** per Qwen's own
  quantization guidance (embedders tolerate Q8 far better than they
  tolerate Q4 because the loss floor is at the pooling head, not decoder
  layers).
- **llama.cpp GPU** — 10-30× faster than CPU for the same model; ~5 GiB
  VRAM lets the embedder be always-resident alongside either large model.
- **Latency check:** at OpenHands document-chunk volumes (< 10k docs per
  session), 4B is < 500 ms per batch — trivial versus decode latency.
- **Rejected alternatives:**
  - `qwen3-embedding-4b-bf16` (vLLM): would need a vLLM instance, competing
    with the coder for VRAM and Docker orchestration. GGUF/llama.cpp is
    simpler and always-resident.
  - `qwen3-embedding-0_6b-*`: quality regression versus the 4B, with no
    meaningful latency benefit at Colossus scale.
  - Any CPU variant: 10-30× slower with no VRAM-freeing benefit
    (embedder fits in VRAM with any large model already).

### Co-residency policy (Option 2)
- **Single-role-at-a-time** avoids building a swap-router that we would
  later throw away or rewrite once Medium-tier verdicts change the
  candidate slate. Cold-start cost of a llama.cpp server (~15-30 s) or
  vLLM container (~30-60 s) is dwarfed by session-level thinking time.
- **Embedder always resident** — 5 GiB budget makes swap unnecessary.
- **Deferred (not this ADR):** an auto-router that lazy-loads the correct
  large model on demand. May become ADR-0018+ if Medium-tier evidence
  shows role-switching cost matters. Not authored today.

## Consequences

### Files / infrastructure to author (this session)

1. **`scripts/serve-coder.sh`** — vLLM Docker launcher for
   `qwen3-coder-30b-a3b-instruct-awq-4bit` on port 8000, with the correct
   parser flags per ADR-0011.
2. **`scripts/serve-planner.sh`** — llama.cpp server launcher for
   `qwen3_6-35b-a3b-q4kxl-gguf` on port 8080, thinking disabled.
3. **`scripts/serve-embedder.sh`** — llama.cpp server launcher for
   `qwen3-embedding-4b-q8-gguf` on port 8090 (always-on).
4. **`scripts/stop-large-model.sh`** — teardown helper (both coder and
   planner variants).
5. **`bench/candidates/production-selection.json`** — canonical file
   listing the three role assignments; downstream code reads this as
   ground truth, not the pool files.

### ADR / spec updates

- ADR index gets an ADR-0017 row.
- BUILD_LOG entry appended.
- SESSION_HANDOFF overwritten to reflect: benchmarking paused; production
  roles assigned; large-model swap policy is Option 2.

### Downstream code impact

- OpenHands router / MCP configuration should point at:
  - Coder → `http://localhost:8000/v1`
  - Planner → `http://localhost:8080/v1`
  - Embedder → `http://localhost:8090/v1`
- Model names in API calls must match the `--served-model-name` used in
  the serve scripts (canonical names in `production-selection.json`).

### Re-evaluation trigger

- When Medium-tier bench results land for any role, this ADR is
  **amended** (not superseded) with either "confirmed" or
  "revised to <new-cell> per <verdict-ADR>" and the corresponding serve
  script and `production-selection.json` are updated in one commit.

## Lock-in phase

Phase 0.2 (Medium-tier authoring paused). Amendments expected once
Medium-tier verdict ADRs (0018+) land.

## References

- ADR-0007 Fast-tier task methodology
- ADR-0008 Fast-tier thinking disabled
- ADR-0011 (+ amendments 1/2) Fast-tier coder tool-call parsers
- ADR-0012 Dual-role thinker registry
- ADR-0014 Coder-fast pool reinstatement
- ADR-0015 Planner-medium thinker probe (Ratified · Confirmed)
- ADR-0016 Medium-tier scoring rubric (hybrid)
- `bench/candidates/coder-fast-pool.json`
- `bench/candidates/planner-fast-pool.json`
- `bench/candidates/embedder-fast-pool.json`
