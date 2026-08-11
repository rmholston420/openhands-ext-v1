# ADR-0010 — Fast-tier vLLM per-role launch flags

**Status:** Ratified
**Lock-in phase:** Phase 0.1 · Fast tier
**Supersedes:** —

## Context

During Phase 0.1 coder-fast smoke gate execution (2026-08-11 03:03 EDT), every
`/v1/chat/completions` request against the `qwen3-30b-a3b-thinking-2507-awq`
coder cell returned **HTTP 400 Bad Request** before the model was invoked. The
server log shows the API validation layer rejecting the payload immediately:

```
[api_server] "POST /v1/chat/completions HTTP/1.1" 400 Bad Request  (x5)
```

Root cause: vLLM's OpenAI-compatible API server refuses `tool_choice="auto"`
requests unless launched with **both** `--enable-auto-tool-choice` and a
compatible `--tool-call-parser`. For the Qwen3-Thinking family it also
requires `--reasoning-parser qwen3` (vLLM 0.27 gates tool-choice + reasoning
interaction on the reasoning parser being registered). None of these flags
were on the `VLLMServer` launch cmd; the launcher used only
`--trust-remote-code`, `--served-model-name`, `--max-model-len`,
`--gpu-memory-utilization`, and `--host`/`--port`.

`LlamaCppServer` already carries a symmetric role-flag policy (ADR-0007 §3,
`LlamaCppServer.ROLE_FLAGS`); `VLLMServer` did not have one, so the tool-call
API was silently disabled on every coder cell.

Two options were considered:

- **A. Role-hardcoded flags in `VLLMServer.ROLE_FLAGS`** — mirrors
  `LlamaCppServer` shape; the launcher is responsible for making the runtime
  serve the API surface each role needs. Task-set files stay
  runtime-agnostic. Model+parser choice is a runtime-family decision, not
  per-task-set state.
- **B. Task-set-driven `vllm_extra_flags`** — flexible per task set; matches
  the ADR-0008 / ADR-0009 opt-in shape (`chat_template_kwargs`,
  `response_format`). Rejected: couples task-set files to vLLM parser names,
  duplicates the concern already covered by `LlamaCppServer.ROLE_FLAGS`, and
  moves runtime-plumbing knowledge outside `bench/runner/server.py`.

## Decision

`VLLMServer` gains a `role` parameter and a `ROLE_FLAGS: dict[str, list[str]]`
mapping, prepended to the launch cmd before caller-supplied `extra_flags`.
Fast-tier defaults for the Qwen3 family:

| Role     | Flags |
|---|---|
| `coder`    | `--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3` |
| `planner`  | `--reasoning-parser qwen3` |
| `embedder` | *(none)* |

Caller-supplied `extra_flags` are appended after `ROLE_FLAGS[role]` so a
caller can override on collision by re-specifying the same flag.

`main.py::_make_server` passes `role=role_str` into the `VLLMServer`
constructor. Unknown role raises `ValueError` at construction time so
misconfiguration surfaces at cell launch, not at request time.

## Rationale

- The 400 rejections observed on 2026-08-11 are entirely explained by the
  missing flags: vLLM's `serving_chat.py` rejects `tool_choice="auto"` +
  `tools=[...]` when no auto-tool-choice parser is registered.
- Qwen3-Thinking family: vLLM 0.27 requires `--reasoning-parser qwen3` to
  correctly consume `<think>...</think>` blocks server-side. Without it,
  finish reasons, tool-call extraction, and structured-output guided decoding
  interact incorrectly. Adding it to planner as well makes ADR-0008's
  `enable_thinking=false` and ADR-0009's `response_format=json_schema` land
  on a server that understands the reasoning-block contract even if a future
  task set flips thinking back on.
- Role-hardcoded in the launcher (Option A) matches `LlamaCppServer`'s
  existing pattern and keeps the port contract single-purpose: task-set
  files describe the *task*, not the *runtime plumbing*.

## Consequences

- `bench/runner/server.py`: `VLLMServer.__init__` gains a required `role`
  keyword; `ROLE_FLAGS` dict added; docstring updated.
- `bench/runner/main.py::_make_server`: passes `role=role_str` into
  `VLLMServer(...)`.
- Every Fast-tier vLLM cell now launches with role-appropriate parser flags.
  Coder cells can accept `tool_choice="auto"` payloads; planner cells strip
  `<think>` blocks server-side.
- Contract test coverage: no new port; contract for `VLLMServer` role-flag
  application belongs in a smoke check (the smoke gate itself validates end
  to end).
- `PORTING_LEDGER.md`: no change (no new vendored component).
- Downstream ADRs: ADR-0008 (`chat_template_kwargs.enable_thinking=false`)
  and ADR-0009 (`response_format=json_schema`) continue to hold; this ADR
  is the launch-flag counterpart on the server side. If coder-fast R2
  evidence later shows the thinking model still starves on tool-call
  emission at 4096 tokens, that decision (flipping coder task set opt-in
  for `enable_thinking=false`) is a separate ADR — it modifies the *task
  set*, not the *launcher*.

## Lock-in phase

Phase 0.1 · Fast tier.

## References

- `bench/runner/server.py::VLLMServer.ROLE_FLAGS`
- `bench/runner/main.py::_make_server`
- ADR-0007 (fast-tier task methodology; `LlamaCppServer.ROLE_FLAGS` pattern)
- ADR-0008 (fast-tier thinking-disabled task-set opt-in)
- ADR-0009 (fast-tier planner guided decoding)
- vLLM 0.27 docs: `serving_chat.py` tool-choice validation; `--tool-call-parser`,
  `--enable-auto-tool-choice`, `--reasoning-parser` flags.
- Observed 400 rejections:
  `bench/results/server-logs/coder_qwen3-30b-a3b-thinking-2507-awq_vllm_gpu-1786431751.log`
