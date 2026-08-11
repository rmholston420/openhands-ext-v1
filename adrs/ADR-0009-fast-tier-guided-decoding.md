# ADR-0009 — Fast-tier planner uses guided decoding (response_format=json_schema)

**Status:** Ratified
**Lock-in phase:** Phase 0.1 · Fast-tier task-set contract
**Supersedes:** —
**Related:** ADR-0008 (Fast-tier thinking disabled)

## Context

After ADR-0008 disabled thinking mode on `qwen3-30b-a3b-thinking-2507-awq`, a fresh planner-fast smoke (`smoke-fast-planner-qwen3-30b-a3b-thinking-2507-awq-vllm-gpu-20260811T064708Z`) still verdict=fail R2 on all 3 tasks:

- **Task 01** (endpoint): model emitted freeform planning prose (`We are adding a new GET /health endpoint. Steps: 1. …`) then a partial pseudo-JSON block; no closing `}` before 4096-token budget → `schema violation: 'steps' is a required property`.
- **Task 02** (migration): same failure mode; free prose narrating the plan for 2000+ chars, no JSON at all → same schema violation.
- **Task 03** (refactor): same; `finish_reason=length` inside the prose block, still no JSON.

Sidecar `.probe.json` confirms `has <think>: False` in all three, so ADR-0008 is doing its job. The remaining failure is a **prompt-adherence lottery**: the model understands the tasks correctly but produces English narration instead of the requested JSON shape, and no amount of "Do not include any prose outside the JSON object" in the prompt reliably suppresses that behavior on a 30B non-thinking Qwen.

vLLM 0.27 exposes OpenAI-compatible guided decoding via `response_format={"type":"json_schema","json_schema":{...,"strict":true}}` (backed by xgrammar / outlines). The task set already carries a fully-specified `output_schema`. Wiring guided decoding into the planner probe is a one-line change that makes malformed JSON structurally impossible; only content-level failures (bad `deps`, too few steps) can remain.

## Decision

Fast-tier planner probe MUST pass a strict `response_format=json_schema` request to vLLM, using the task set's own `output_schema` verbatim, in addition to the ADR-0008 `chat_template_kwargs`.

- The field lives in the probe, not the task set — every Fast-tier planner task set already has an `output_schema` (schema v1.0.0), so no per-task-set change is required.
- `strict: true` is mandatory; without it vLLM permits schema-extended output.
- Sidecar `notes` records `response_format=json_schema` for provenance.

## Rationale

- **Deterministic elimination of R2 malformed-JSON failures.** Grammar-constrained decoding can only produce schema-conforming JSON. This is the correct guarantee for a "structural JSON" task tier.
- **No task-set churn.** The `output_schema` field is already the source of truth; guided decoding uses it directly.
- **No sampler churn.** ADR-0008 stays in force. Guided decoding composes with `enable_thinking=false` and the existing planner sampling preset (`temp=0.6, top_p=0.95`).
- **Fast-tier scope.** This tier is explicitly a structural-JSON gate. It is NOT the tier where we want the model reasoning about anything — reasoning quality is graded in Slow tier under different rubrics.
- **vLLM backend readiness.** xgrammar has been the default vLLM structured-output backend since 0.6.5+; 0.27 supports the OpenAI json_schema envelope directly. No launcher flags needed for basic use.

## Alternatives rejected

1. **Prompt-only tightening ("Output ONLY JSON. No prose. Start with `{`.").** Rejected: model already ignored the existing "Do not include any prose outside the JSON object" instruction; adding more of the same is a lottery.
2. **Post-hoc JSON extraction (grep first `{...}` block).** Rejected: probe already does `_extract_json_object`; the model didn't produce a balanced JSON object at all on tasks 02/03, so extraction has nothing to salvage.
3. **Bump `budget_tokens` from 4096 to 8192.** Rejected: masks the failure by giving prose more room; still leaves prose in the output; still non-deterministic; still burns tokens on narration; ADR-0008 rationale applies verbatim.
4. **Switch to a smaller / more instruction-adherent model.** Rejected: pool selection is orthogonal; guided decoding fixes ALL candidates in this tier, present and future, and does so without excluding thinking-tagged models we already vetted.
5. **Two-turn refinement (first turn free, second turn "reformat as JSON").** Rejected: doubles latency and cost, complicates the probe, still non-deterministic on turn 2.

## Consequences

- `bench/runner/probes.py::probe_planner`: adds `response_format` construction and payload injection. Sidecar `notes` gains `response_format=json_schema` marker (space-joined with any existing `chat_template_kwargs=...` note).
- `bench/tasks/planner-fast.json`: unchanged; the `$comment` remains valid and now points to both ADR-0008 and (implicitly) the probe-level guarantee.
- Runner behavior: task-outcome verdicts can no longer fail via `schema violation: '<key>' is a required property` unless the model produces zero output tokens (transport / OOM). Remaining failure modes: `truncated at max_tokens` (structural JSON hit the budget), `too few steps`, `dependency graph is not a DAG`, `desc minLength` violations.
- Coder probe: unchanged for now. Coder-fast uses tool-calling, not JSON-schema output; guided decoding for coder tools is a future ADR if needed.
- vLLM launcher: no flag changes required. `--enable-auto-tool-choice` remains coder-only.
- DEBUG_LOG closes the 2026-08-11 02:45 EDT R2 diagnosis with ADR-0009 as the terminal fix.

## Lock-in phase

Phase 0.1. Fast-tier task-set contract v1.0.0 is unchanged; the probe-side contract gains a mandatory `response_format` when `output_schema` is present.

## References

- `bench/runner/probes.py` (probe_planner)
- `bench/tasks/planner-fast.json` (output_schema v1.0.0)
- `adrs/ADR-0008-fast-tier-thinking-disabled.md`
- vLLM 0.27 OpenAI structured outputs: `docs/features/structured_outputs.md` (upstream)
- Evidence run: `bench/results/smoke-fast-planner-qwen3-30b-a3b-thinking-2507-awq-vllm-gpu-20260811T064708Z.probe.json`
