# Phase 3 Verification Row-2 Smoke — Planner Routing

Verifies `CoderPlannerRouter` dispatches to the planner endpoint (:8082 llama.cpp) when the caller supplies `LLMCallContext.metadata["role"]="planner"` (Path A per ADR-0033 amend #4).

## Purpose

End-to-end verification that:
1. `LLMCallContext(metadata={"role": "planner"})` propagates through
2. `CoderPlannerRouter.completion()` calls `select_llm(messages, call_context)`
3. `select_llm` returns `"planner"` on the metadata role
4. The completion is delegated to the planner LLM (:8082 llama.cpp), NOT the coder LLM (:8100 vLLM)

## Prompt (verbatim, hand off to router)

> Briefly plan the steps you would take to write a Python function that reads a JSONL file line by line and yields each parsed record. One paragraph. Do not write code.

## Pass criteria

- `CoderPlannerRouter.select_llm(messages, call_context)` returns `"planner"`.
- The completion is issued to the planner endpoint (verified by intercepting `.active_llm` after the call).
- Response is non-empty text.
- No exceptions raised.
- Total wall time under 30 seconds on Colossus.

## Fail criteria

- `select_llm` returns `"coder"` (metadata not forwarded).
- Completion routed to :8100 (coder) instead of :8082 (planner).
- HTTP 5xx from either endpoint.
- Empty response.

## Prereqs

1. Coder :8100 running (from row-1: `scripts/serve-coder.sh` still up).
2. Planner :8082 running (`scripts/serve-planner.sh`).
3. `.venv/` active.

Note: row-2 does NOT need a full `Conversation`; it exercises the router directly to isolate the routing question from the agent loop.
