# ADR-0013 — Registry exclusion: Qwen3.5-VL multimodal variants are not coder-pool candidates

**Status:** Ratified
**Lock-in phase:** Phase 0.1 · Fast tier
**Supersedes:** —

## Context

Coder-fast pool smoke 2026-08-11 03:29 EDT (`bench/candidates/coder-fast-vllm.json`
against `bench/rubrics/fast-elimination.json`) produced these R1 eliminations:

- `qwen3_6-27b-int4-autoround` — `torch.OutOfMemoryError` during vLLM KV cache
  profiling. Model weights loaded at 17.7 GiB, but total process footprint
  reached 30.20 GiB with only 539 MiB free at KV alloc time. Server exit 1.
- `qwen3_6-35b-a3b-awq` — `torch.OutOfMemoryError` during vLLM KV cache
  profiling. Model weights loaded at 22.23 GiB. Server exit 1.

Post-mortem via `models/qwen3_6-27b-int4-autoround/config.json` and
`models/qwen3_6-35b-a3b-awq/config.json` shows both configs carry a populated
`vision_config` (`depth: 27` vision-encoder layers, `hidden_act:
gelu_pytorch_tanh`, `image_token_id: 248056`, `video_token_id: 248057`,
`vision_start_token_id: 248053`, `vision_end_token_id: 248054`), and the
architecture strings `Qwen3_5ForConditionalGeneration` and
`Qwen3_5MoeForConditionalGeneration` are HF's `ForConditionalGeneration`
convention for vision-language models. vLLM logs during startup emitted
`[ERROR] min_frames is part of Qwen3VLVideoProcessorInitKwargs` and
`Qwen3VLVideoProcessorInitKwargs`-related warnings, further confirming the
vision-language path was entered.

For comparison, `qwen3-30b-a3b-thinking-2507-awq/config.json`:
`architectures: ['Qwen3MoeForCausalLM']`, `vision_config: absent` — pure text
model. Model loaded at 16.96 GiB, KV cache 9.61 GiB, 5/5 tasks passed.

Root cause of the R1s: both multimodal variants were pulled into the coder
pool based on slug naming, not model-card verification. Their vision tower
consumes ~10–12 GiB of VRAM that the coder-role probe cannot use (coder-fast
tasks are text-only tool-calling). At the 32 GiB SM_120 envelope this leaves
insufficient KV cache room for `--max-model-len 32768`.

This is not a runtime version regression (R4-candidate note in result JSON
was auto-appended but is not the cause), a tool-call parser bug, or a launcher
mechanism defect. It is a candidate-selection error at registry authoring
time.

## Decision

1. **Exclude Qwen3.5-VL (`Qwen3_5*ForConditionalGeneration`) variants from the
   coder pool.** They remain permissible entries for future roles (image
   captioning, doc understanding, visual grounding) once such roles exist in
   the router. Coder role is text-only tool-calling per ADR-0007; multimodal
   weights are dead-weight for it.
2. **Remove the two failing entries from `bench/candidates/registry.json`
   `roles.coder`:**
   - `qwen3_6-27b-int4-autoround`
   - `qwen3_6-35b-a3b-awq`
   These lines are deleted, not commented — the registry is the single source
   of truth for `pull-models.sh` and the tier runner. Their `models/<slug>/`
   directories are left on disk (17.69 + 23.71 GiB) for possible reuse under a
   future vision role; they are not re-pulled.
3. **Registry authoring rule going forward:** every new coder-pool candidate
   MUST have `architectures[0]` ending in `ForCausalLM` (not
   `ForConditionalGeneration`), OR its model card must explicitly document
   text-only inference paths with published KV budget on a 32 GiB device.
   Pool authors must verify by reading `config.json` before adding a slug,
   not by inferring from filenames.
4. **Do NOT amend the launcher mechanism (ADR-0010) or the tool-call parser
   (ADR-0011).** Both remain correct and empirically verified.

## Rationale

- **Alternative A (keep the multimodal entries, patch vLLM launch flags to
  skip vision tower).** vLLM 0.27 does not expose a `--skip-vision-tower`
  flag; the model class loads the tower unconditionally. Requires vendor
  patching of `Qwen3VL*` model files. Out of scope for fast tier.
- **Alternative B (keep them, lower `--gpu-memory-utilization` further).**
  Lowering below 0.9 does not free the vision-tower memory (already loaded
  before profiling); it only reduces the KV budget further. Wrong direction.
- **Alternative C (accept the R1s and keep the multimodal entries in the
  registry as PLANNED-but-known-fail).** Corrupts §0.0b pool math — an entry
  that is architecturally incapable of running the role should not count
  toward `min_pool`. Removing them is cleaner and forces registry authors
  to add real coder candidates.
- **Chosen (this ADR):** exclusion + registry-authoring rule + no launcher
  change.

## Consequences

- **Files touched:**
  - `bench/candidates/registry.json` — remove `qwen3_6-27b-int4-autoround`
    and `qwen3_6-35b-a3b-awq` from `roles.coder`. Their `roles.planner`
    membership is also removed (same architectural argument applies to
    planner: text-only tool-calling + JSON schema). Their `models/<slug>/`
    dirs stay on disk.
  - `adrs/README.md` — index row.
  - `BUILD_LOG.md` — append entry (pool run + this ADR + registry edit).
  - `DEBUG_LOG.md` — append entry (`torch.OutOfMemoryError` symptom keyed to
    "multimodal vision tower in coder pool").
- **Coder-fast pool state after this ADR:** 1 survivor
  (`qwen3-30b-a3b-thinking-2507-awq`) + 2 llama.cpp candidates
  (`qwen3_6-27b-q6k-gguf`, `qwen3_6-35b-a3b-q4kxl-gguf`). But those two GGUF
  candidates are **also multimodal-tainted at the source model** — GGUF
  quants of Qwen3.5-VL still carry vision weights. The GGUF path deferral
  from ADR-0012's session decision no longer removes the ambiguity — those
  two llama.cpp cells must be re-verified (or excluded) before being run.
  This is a separate decision, not resolved here.
- **Pool-size vs. §0.0b guard:** with only the 30B thinker surviving,
  `min_pool=3` is unmet. Full-tier coder gate cannot advance until the pool
  is repopulated with real text-only coder candidates.

## Lock-in phase

Phase 0.1 fast-tier coder-pool composition.

## References

- `bench/results/phase-0-fast-coder-qwen3_6-27b-int4-autoround-vllm-gpu-20260811T073011Z.json`
- `bench/results/phase-0-fast-coder-qwen3_6-35b-a3b-awq-vllm-gpu-20260811T073355Z.json`
- `bench/results/phase-0-fast-coder-qwen3-30b-a3b-thinking-2507-awq-vllm-gpu-20260811T072930Z.json`
- `models/qwen3_6-27b-int4-autoround/config.json` (vision_config present)
- `models/qwen3_6-35b-a3b-awq/config.json` (vision_config present)
- `bench/results/server-logs/coder_qwen3_6-27b-int4-autoround_vllm_gpu-*.log`
- ADR-0007 (fast-tier task methodology), ADR-0010, ADR-0011, ADR-0012.
