# Phase 3 Verification Smoke Task

Minimal trivial task for spec §Phase 3 verification matrix row 1 (spec L378-383).

## Purpose

Verify end-to-end that:
1. `config/agent.build_agent()` constructs an Agent
2. The Agent's `llm` (a `CoderPlannerRouter`) reaches the coder endpoint at `127.0.0.1:8100/v1`
3. The Agent executes tool calls via `openhands-tools` (file I/O + shell)
4. The Agent emits a `FinishAction` on completion

## Prompt (verbatim, hand off to agent)

> Read the file `bench/smoke-phase-3/README-target.txt` and print its first non-empty line to stdout. Then finish with a one-sentence summary of what you did.

## Pass criteria

- Agent reads `bench/smoke-phase-3/README-target.txt` (via `openhands-tools` file editor or shell `head`).
- Agent prints the expected first line: `OpenHands-Ext v1 Phase 3 smoke target.`
- Agent emits a `FinishAction` with a summary message.
- Event stream contains at least one tool-call action and its observation.
- Total wall time under 60 seconds on Colossus with coder resident.

## Fail criteria

- Any HTTP 5xx from coder endpoint.
- Agent loops without FinishAction for 60s.
- Wrong file contents printed.
- No tool-call action in the event stream.
