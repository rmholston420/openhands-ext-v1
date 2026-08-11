# config/ — Production Configuration

Canonical Phase 2.4 config surface per **ADR-0033** (Python module, not TOML).

## Files

- **`agent.py`** — canonical runtime config. Builds three `LLM` instances against Phase 0.3 winners, wires `CoderPlannerRouter`, and returns a fully-configured `Agent` via `build_agent()`.
- **`router.py`** — `CoderPlannerRouter(RouterLLM)`. Dispatches via `LLMCallContext.metadata["role"]` (option 6c). Default route: coder.
- **`max-output-tokens.json`** — provenance-tracked ceiling values (currently `SPEC_SHEET` per ADR-0033 status amendment 2026-08-11 17:20 EDT; empirical override deferred to ADR-0035). Populated by `scripts/populate-max-output-tokens.sh`. Required before `config.agent` can be imported.

## Usage

```python
from config.agent import build_agent
agent = build_agent()

# Dispatch a planner subtask:
from openhands.sdk.llm.llm import LLMCallContext
ctx = LLMCallContext(metadata={"role": "planner"})
```

## Roles

| Role | Model | Runtime | Endpoint | ADR |
|---|---|---|---|---|
| coder | qwen3-coder-30b-a3b-instruct-awq-4bit | vLLM | 127.0.0.1:8100 | 0029 |
| planner | qwen3_6-27b-q6k | llama.cpp | 127.0.0.1:8082 | 0023, 0025 |
| embedder | qwen3-embedding-4B-Q8_0 | llama.cpp | 127.0.0.1:8090 | 0031 |
| condenser | (reuses coder endpoint) | — | — | 0033-7a |

Co-residency: **coder XOR planner + embedder** (ADR-0017 amend).

## Why not TOML?

openhands-sdk 1.41 has no TOML config loader. See ADR-0033 for the full introspection record. Spec §2.4's TOML block documents *intent*; this directory is the *mechanism*.
