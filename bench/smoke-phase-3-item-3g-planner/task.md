# Phase 3 · Item 3.g (planner half) — Tool-calling smoke against planner :8082

## Purpose

Verify that the production **planner endpoint** (`qwen3_6-27b-q6k-gguf` on llama.cpp, port 8082, launched with `--jinja`) can issue **native OpenAI tool_calls** through the SDK's `LLM.completion(..., tools=[...])` surface. Row-1 proved this for the coder (:8100 vLLM). Row-2 proved planner *routing* and non-tool completion. This item closes the tool-calling gap for the planner endpoint.

Scope-limited by design:

- Direct `LLM.completion(...)` call, **no `Conversation`**. This isolates the endpoint's tool-calling capability from the agent loop, the router, and DockerWorkspace.
- Uses a shipped `Action` subclass (`TerminalAction`) wrapped in a `ToolDefinition` — no hand-built JSON schema. If the SDK's own definition doesn't yield a tool call from the planner, that's the finding.
- **No execution** of the tool call. We are verifying that the model *decides to call* the tool and that its arguments parse — not that any command actually runs.

## Prompt (verbatim)

> Run the shell command `echo hello-planner-3g` to prove you have a terminal available. Call the `terminal` tool with `command="echo hello-planner-3g"` and nothing else. Do not answer in prose.

## Pass criteria

- `LLM.completion(messages=[Message(...)], tools=[terminal_td])` returns without exception.
- `response.message.tool_calls` is a non-empty list.
- At least one tool call has `.name == "terminal"` (or `.function.name == "terminal"` — whichever shape the SDK exposes).
- The tool call's arguments parse as JSON.
- The parsed arguments contain a `command` key whose value contains the string `hello-planner-3g`.
- Wall time under 60 s (planner is slower than coder; 30 s is too tight).

## Fail criteria

- `.tool_calls` is `None` or empty (model answered in prose instead of calling the tool).
- Arguments do not parse as JSON.
- Argument `command` missing or doesn't contain `hello-planner-3g`.
- Any exception.
- Wall time ≥ 60 s.

## Prereqs

- Planner :8082 running (`scripts/serve-planner.sh` launched with `--jinja`).
- Coder :8100 **not** required (and per ADR-0017 XOR co-residency, should not be up at the same time as planner).
- `.venv/` at repo root.

## What this does NOT verify

- Embedder tool-calling: the embedder does not expose a chat/completions endpoint that supports tools; embedder verification is a separate check (embedding round-trip, not tool-calling).
- End-to-end agent loop against the planner: that's 3.i (joint role-switch) and, separately, 3.j (RouterLLM under RemoteConversation).
