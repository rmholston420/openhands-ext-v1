# ADR-0008 — Fast tier disables thinking mode for planner (and opt-in for coder)

**Status:** Ratified
**Lock-in phase:** Phase 0.1
**Supersedes:** —

## Context

Phase 0.1 first real smoke run on Colossus (`smoke-fast-planner-qwen3-30b-a3b-thinking-2507-awq-vllm-gpu-20260811T064211Z.json` + sidecar) revealed that `qwen3-30b-a3b-thinking-2507-awq` fails every planner-fast task under `budget_tokens=4096` — not because it cannot solve the tasks, but because its `<think>` prose consumes the budget:

- **Task 01 (endpoint):** thinking completed, JSON emitted, but the last `desc` truncated mid-sentence at max_tokens → only 2 valid steps parsed → schema requires `minItems: 3` → R2 rejection with reason `"is too short"`.
- **Task 02 (migration):** budget exhausted *inside* `<think>` block; no `</think>` closer; no JSON emitted → R2 rejection `'steps' is a required property`.
- **Task 03 (refactor):** `finish_reason=length` inside thinking; no JSON → R2 `truncated at max_tokens`.

The Fast tier's stated purpose in ADR-0007 is deterministic, low-cost elimination against structural criteria (valid JSON, matches schema, DAG). It is not a reasoning-quality benchmark. Chain-of-thought is strictly counterproductive here: it adds latency, consumes budget, and (as observed) can produce zero output on models that fail to close `<think>` in time.

The observed model has a documented non-thinking mode reachable via the Qwen chat template kwarg `enable_thinking=false`, which vLLM 0.27.0 accepts as `chat_template_kwargs` in `/v1/chat/completions` payloads.

## Decision

The Fast tier disables thinking mode via a **task-set-level** field `chat_template_kwargs`, forwarded verbatim into the OpenAI-compatible payload by both planner and coder probes:

- **`planner-fast.json` sets `"chat_template_kwargs": {"enable_thinking": false}`** as a hard default.
- **Coder-fast task sets may opt in** (default off) if benchmarking shows the same starvation pattern for tool-calling. Coder role often benefits from CoT for tool selection; the flag stays opt-in until evidence justifies flipping it.
- **Non-thinking models ignore the field** — this is a template no-op for them.
- **Deep and Long tiers do not inherit this policy.** Those tiers' whole point is quality-under-reasoning; they enable thinking by default (or via their own task-set kwargs).

The policy lives on the **task set**, not the candidate. Rationale: the tier's evaluation shape dictates whether CoT is appropriate; the candidate's `thinking` tag is descriptive, not policy.

## Rationale

Alternatives considered:

1. **Bump `budget_tokens` for thinking models.** Rejected: (a) 8k would work today but breaks the moment task complexity rises; (b) reasoning tokens count in latency and tok/s, corrupting the Fast tier's timing signal; (c) still doesn't help models that emit unbounded thinking.
2. **Add per-candidate `thinking_mode` field.** Rejected as heavier than warranted. Fast-tier policy is uniform across candidates; task-set-level is the correct locus. If future tiers need per-candidate variance, we can layer it on without changing this ADR.
3. **Ban thinking-tagged models from Fast tier entirely.** Rejected: thinking models with thinking *disabled* are legitimate Fast-tier candidates (Qwen's non-thinking path is well-tested). Excluding them cuts the candidate pool for no methodological gain.
4. **Prompt-level suppression (e.g. `/no_think` marker in the prompt).** Rejected: model-specific, brittle across the Qwen/DeepSeek/other families we plan to bench. `chat_template_kwargs` is the vendor-supported surface.

## Consequences

- `bench/tasks/planner-fast.json` gains `"chat_template_kwargs": {"enable_thinking": false}`.
- `bench/runner/probes.py`:
    - `probe_planner` reads `task_set.get("chat_template_kwargs")` and, if present, forwards it into every `/v1/chat/completions` payload; records it in `ProbeResult.notes`.
    - `probe_coder` honors the same field (opt-in via task-set; default off).
- `bench/runner/probes.py::TaskResult` sidecar already captures `raw_content`; observers can confirm the absence of `<think>` blocks in re-run outputs to verify the fix landed.
- BUILD_LOG entry logs the change; DEBUG_LOG entry closes the R2 diagnosis with this ADR as the fix reference and supersedes the diagnostic-gap entry from 2026-08-11 02:38 EDT for the *policy* portion (the sidecar remains part of the run contract regardless).
- ADR-0007 is unchanged — this ADR extends its methodology without contradicting it. The `budget_tokens=4096` bound in ADR-0007 §Fast-tier probes was implicitly assuming non-thinking output; ADR-0008 makes that assumption explicit.
- No effect on Depth or Long tiers; when they exist, their task sets omit the kwarg (or set `enable_thinking: true` explicitly for symmetry).
- vLLM launch flags unchanged. `--reasoning-parser qwen3` is not required when thinking is disabled per-request via chat template kwargs.

## Lock-in phase

Phase 0.1 (Fast-tier task-set authoring is a Phase 0.1 deliverable).

## References

- ADR-0007 (Fast-tier task methodology): tier purpose, budget, rubric.
- `bench/results/smoke-fast-planner-qwen3-30b-a3b-thinking-2507-awq-vllm-gpu-20260811T064211Z.json` + `.probe.json`: evidence of thinking-mode budget starvation.
- BUILD_LOG entry `2026-08-11 02:45 EDT — Fast tier disables thinking mode (ADR-0008)`.
- DEBUG_LOG entry `2026-08-11 02:38 EDT — Runner discards raw probe outputs; R2 failures undiagnosable post-hoc` (the diagnosis this ADR resolves).
- Qwen chat template: `enable_thinking` kwarg — Qwen3 model card, qwen.readthedocs.io.
