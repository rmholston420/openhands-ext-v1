# Phase 3 Sign-Off Item 3.h-1 Smoke — DelegateTool Wiring

Verifies the SDK's delegation mechanism end-to-end: a supervisor Agent
built by `build_agent()` uses `TaskToolSet` to delegate a read-only
investigation subtask to the `code-explorer` subagent, and consumes
the returned `TaskObservation`.

## Rationale

Item 3.h in the Phase 3 sign-off checklist originally read
"coder→planner via DelegateTool (supervisor swap)". Inspection of
SDK 1.41 (`openhands.tools.task.manager:367`) showed that the
subagent's LLM is a `model_copy` of the parent LLM by default (`model:
inherit` preset). DelegateTool does not swap endpoints — it swaps the
agent scope (tools, system prompt, budget). Endpoint routing is the
router's job (Path B message-marker, ADR-0033 amend #5).

Consequently 3.h is split:

- **3.h-1** (this smoke): delegation mechanism itself. Executable with
  only coder up. Subagent inherits coder LLM.
- **3.h-2** (deferred): true cross-endpoint hand-off (coder supervisor
  ↔ planner subagent). Blocked by ADR-0017 XOR co-residency (VRAM
  budget); documented gap.

3.h-1 also rolls up the live-delegation coverage deferred from 3.a
("code-explorer investigation returns file paths + line numbers").

## Prereqs

- Coder up on `http://127.0.0.1:8100/v1` (verified via `/v1/models`).
- Planner may be down (subagent inherits coder LLM).
- Embedder need not be up.

## Pass criteria

- `build_agent()` returns an Agent whose tools include `task_tool_set`.
- At least one `TaskAction` (or its message-level equivalent) appears
  in the supervisor's event stream.
- The subagent runs (at least one event whose provenance is the
  subagent, e.g. an ActionEvent with `source == "agent"` inside a
  delegated scope, or a nested Conversation state).
- A `TaskObservation` (or its rendered content) returns to the
  supervisor with non-empty text.
- The subagent's returned text contains at least one filename that
  actually exists in the checkout, or at least one line-number-style
  citation (`^\d+:` or `:\d+` reference). This is the ADR-0032
  substantive check: the read-only investigation produced grounded
  evidence.
- Wall time under 300 s.
- No exceptions raised out of `conversation.run()`.

## Fail criteria

- `build_agent()` raises or `task_tool_set` missing.
- `conversation.run()` raises.
- No delegation event in the stream (supervisor never invoked
  TaskToolSet).
- Subagent returned empty text or raised.
- Returned text contains no plausible file/line evidence.
- Wall exceeds 300 s.

## Task prompt

The supervisor is instructed to delegate an exploration subtask to
`code-explorer`. The prompt asks: "find where `TaskToolSet` is defined
in the OpenHands SDK on disk and return the file path with the line
number of the class definition." This is a real read-only
investigation with a verifiable answer
(`.venv/.../openhands/tools/task/definition.py:198` from the earlier
grep in this session).

## Confirmation policy

`confirmation_policy=NeverConfirm()` — this is a smoke, not
interactive; delegation should proceed without user prompts.
