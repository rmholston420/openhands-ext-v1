# ADR-0033 — Phase 2.4 config surface: Python module, not TOML

**Status:** Ratified
**Lock-in phase:** Phase 2.4 (Tiered multi-LLM routing) · Phase 3 (verification)
**Supersedes:** —

> **STATUS AMENDMENT (2026-08-11 18:01 EDT):** Amendment #4 (below, 17:52 EDT) selected Path A on the assumption that `LLMCallContext` carried a `metadata: dict` field the SDK failed to thread into `select_llm`. Direct inspection of `openhands.sdk.llm.llm.LLMCallContext` (SDK 1.41, line 189) shows it is a **frozen dataclass with only two fields**: `prompt_cache_key: str | None` and `session_id: str | None`. **No `metadata` field.** Option 6c (metadata-based role routing) is therefore not implementable in SDK 1.41 without forking the SDK. Formally switching to **Path B** (option 6b, message-content heuristic): `fallback_message_heuristic=True` on `CoderPlannerRouter` inspects the last user message for a `[role:planner]` marker. Applied to `config/agent.py::build_router` (enabled by default) and `config/router.py::CoderPlannerRouter.select_llm` (fixed to handle both `str` and `list[TextContent]` content shapes — SDK 1.41 uses the list shape). Path A's `completion()` override remains in place as forward-compatibility: if the SDK later adds `metadata` to `LLMCallContext`, the override starts routing on it and Path B becomes dormant automatically. Contingency ordering is inverted from amend #4: metadata (if present) wins; marker heuristic is the fallback. Row-2 smoke rewritten to test both the marker route (positive) and a no-marker control (negative). Trade-off accepted: routing signal lives in prompt content — acceptable because (a) markers appear only in the leading system-injected or delegate-injected framing, not model-authored content, (b) the marker is stable and greppable, (c) removal is one-line when the SDK adds `metadata`.

> **STATUS AMENDMENT (2026-08-11 17:52 EDT):** Phase 3 row-2 (planner routing) requires the SDK-1.41 gap workaround now, not later. SDK 1.41's `RouterLLM.completion()` receives `call_context` (`base.py:63`) and forwards it to the selected LLM (`base.py:93`), but calls `self.select_llm(messages)` with no context (`base.py:82`). Contingency options in the original decision: **Path A** override `completion()` to call `select_llm(messages, call_context)`, or **Path B** flip `fallback_message_heuristic=True` and inject `[role:planner]` markers in prompts. Chose **Path A** — keeps routing behind the class boundary (ADR-0007 spirit: no coupling leakage into prompt content), localizes the SDK workaround, and becomes a trivial no-op removal if the SDK forwards `call_context` natively in a future version. Applied to `config/router.py::CoderPlannerRouter.completion` — replicates the 8-line base body but calls `self.select_llm(messages, call_context)`. Row-2 smoke at `bench/smoke-phase-3-row-2/` exercises the router directly (no `Conversation`) to isolate the routing question from the agent loop.

> **STATUS AMENDMENT (2026-08-11 17:47 EDT):** Amendment #2 (below, 17:25 EDT) was based on an incorrect reading of `LLMSummarizingCondenser`. Direct source inspection of `openhands.sdk.context.condenser.llm_summarizing_condenser.py:117-118` shows `max_tokens` is the CONDENSATION TRIGGER threshold, not a summary-output cap: `if total_tokens > self.max_tokens: reasons.add(Reason.TOKENS)`. Setting `max_tokens=1024` caused the Phase 3 row-1 smoke to condense on the first turn (system prompt alone is ~5495 tokens), destroying the tool observation and forcing the agent to fabricate a summary. Corrected: (a) `LLMSummarizingCondenser.max_tokens=30000` — near coder context ceiling, condensation now fires only as a safety net; (b) spec §2.4's "1024" intent honored as `LLM.max_output_tokens=1024` on the condenser LLM, capping the length of the summary TEXT the condenser produces. This is the correct semantic home for "bound the summary length." Fix applied to `config/agent.py::build_condenser`; DEBUG_LOG entry appended.

> **STATUS AMENDMENT (2026-08-11 17:25 EDT):** `build_agent()` end-to-end wiring failed on Colossus with `LLMContextWindowTooSmallError` at `build_condenser` because spec §2.4's `max_input_tokens=1024` on `[llm.condenser]` was mechanically ported to the `LLM` constructor and SDK 1.41 enforces `MIN_CONTEXT_WINDOW_TOKENS=16384`. Root cause: the spec's `max_input_tokens=1024` was mis-placed — the condenser must READ long histories (that's its job), so shrinking its input window to 1024 is semantically wrong regardless of the SDK floor. The spec's actual intent (bound the summary OUTPUT length) is honored via `LLMSummarizingCondenser.max_tokens=1024`, confirmed by direct inspection of `openhands.sdk.context.condenser.llm_summarizing_condenser.LLMSummarizingCondenser` fields (`max_size: int = 240`, `max_tokens: int | None = None`, `keep_first: int = 2`). Fix applied to `config/agent.py` `build_condenser()`. Spec §2.4 TOML block retained as-is (intent-only, per this ADR's core decision).

> **STATUS AMENDMENT (2026-08-11 17:20 EDT):** During Phase 2.4 authoring, investigation on Colossus established that the Phase 0.x bench harness (`bench/results/*.json`, `bench/results/verdicts/*.json`) does **not** record per-response output-token counts — no `output_tokens`, `completion_tokens`, or `response_tokens` field is present in any Phase 0.x artifact. Spec §2.4's "measured-in-full-tier, not assumed" mandate was not honored by the harness that produced ADR-0025 and ADR-0029. The extract script planned in the original decision (`scripts/extract-max-output-tokens.sh`) is therefore replaced by `scripts/populate-max-output-tokens.sh`, which populates `config/max-output-tokens.json` with **spec-sheet ceiling values** (8192 for both roles) and provenance flavor `SPEC_SHEET`. Phase 3 verification produces the first empirical observation of actual response lengths. If observed peak approaches or exceeds 8192 in normal use, file ADR-0035 to bump both values and re-run (reversal path: edit two ints in `config/max-output-tokens.json`, no code change). This amendment does not change the core decision (Python config surface, option 6c, option 7a); it only corrects the mechanism for populating one field.

## Context

Spec `docs/specs/integration-execution-plan-v16.md` §2.4 (L328-357) specifies the Phase 2.4 config surface as a TOML file with sections `[llm]`, `[llm.planner]`, `[llm.condenser]`, `[llm.embedding]`. The spec was authored before the openhands-sdk 1.41.0 config surface was inspected directly.

Introspection of the pinned SDK (`openhands-sdk==1.41.0`, VERSIONS.lock 2026-08-06) on Colossus 2026-08-11 16:56 EDT established:

1. **No global TOML config loader** exists in `openhands.sdk`. No `from_toml`, `load_config`, or `BaseSettings` subclass loads a `config.toml`/`config/agent.toml` file at agent construction time.
2. **`LLM` is a Pydantic model** constructed directly in Python: `LLM(model="openai/...", base_url="http://...", api_key=SecretStr("EMPTY"), usage_id="...")`.
3. **Multi-LLM routing is a first-class SDK primitive** via `openhands.sdk.llm.router.base.RouterLLM(LLM)`, which itself inherits from `LLM`. Subclasses implement `select_llm(messages) -> str` and populate `llms_for_routing: dict[str, LLM]`. Shipped implementations: `MultimodalRouter`, `RandomRouter` (`openhands/sdk/llm/router/impl/`).
4. **`LLMCallContext`** (referenced at `openhands/sdk/llm/router/base.py:18`, `TYPE_CHECKING`-guarded) is the SDK's per-call metadata channel — the dispatch signal for `select_llm` when message content alone is insufficient.
5. **Condenser wiring is Python-first**: `LLMSummarizingCondenser(llm=<any LLM>)`, passed as `Agent(llm=..., condenser=...)`. The SDK emits its own wiring examples inline in error messages (`agent.py` L1435-1440, `local_conversation.py` L2810-2814).
6. **Delegate tool exists** at `openhands.tools.delegate` (`DelegateAction`, `DelegateObservation`, `DelegateExecutor`). Spec §2.5's "DelegateTool" concept maps to this module.
7. **TaskToolSet exists** at `openhands.tools.task.definition:198` (`TaskToolSet(ToolDefinition[TaskAction, TaskObservation])`). Confirms spec §2.5.

Populating a TOML file that no SDK loader reads would create dead configuration. The spec's TOML block encodes the correct intent (four roles wired against Phase 0.3 winners with measured `max_output_tokens`), but the mechanism must be amended to match SDK 1.41.

## Decision

**The Phase 2.4 canonical config surface for OpenHands-Ext v1 is a Python module at `config/agent.py`** that:

1. Constructs three `LLM` instances against the Phase 0.3 winning endpoints:
    - `coder` — `openai/qwen3-coder-30b-a3b-instruct-awq-4bit` at `http://127.0.0.1:8100/v1` (vLLM, ADR-0029)
    - `planner` — `openai/qwen3_6-27b-q6k` at `http://127.0.0.1:8082/v1` (llama.cpp GPU, ADR-0025)
    - `embedder` — `qwen3-embedding-4B-Q8_0` at `http://127.0.0.1:8090/v1` (llama.cpp GPU cold, ADR-0031)
2. Wires **`CoderPlannerRouter(RouterLLM)`** with `llms_for_routing={"coder": coder, "planner": planner}` and `select_llm(messages, call_context)` dispatching on `LLMCallContext` metadata (route key: `role` in `call_context.metadata` → `"planner"` if present else `"coder"` default).
3. Wires **`LLMSummarizingCondenser(llm=coder)`** — the coder endpoint doubles as the condenser (ADR-0033-decision-7a; no separate condenser service). `temperature=0.1`, `max_input_tokens=1024` per spec §2.4.
4. Exposes a **`build_agent()`** factory returning a fully-wired `Agent(llm=router, condenser=condenser, tools=[...])` for downstream use (Phase 3 verification, DockerWorkspace runs, agent-canvas integration).
5. `max_output_tokens` values are **populated from measured Phase 0.3 bench JSON** (`~/.forge-oh/bench_coder_full_multi_turn/*_run/*.json` for coder, `~/.forge-oh/bench_planner_medium_migration_probe/*_run/*.json` for planner), not assumed. Extraction script `scripts/extract-max-output-tokens.sh` records the measurement provenance.

`config/agent.toml` will **not** be authored. The spec §2.4 TOML block is retained as documentation of the config's semantic intent (four roles, measured limits) but is no longer the deliverable.

## Rationale

**Why Python module over TOML:**
- SDK 1.41 has no TOML loader for LLM configs. Authoring TOML that nothing reads produces phantom config.
- Pydantic construction is the canonical, SDK-blessed pattern; SDK error messages themselves emit Python snippets as the fix.
- Python allows the `CoderPlannerRouter` subclass + `select_llm` method to live alongside the LLM instances they route between. TOML cannot express the routing logic; a Python entrypoint would be required regardless.

**Why option 6c (LLMCallContext metadata) over 6a (separate Agents) or 6b (message heuristics):**
- **6a (separate Agents)** abandons spec §2.4's unified routing framing entirely. Would require a supervisor layer above two Agents, duplicating work SDK's `RouterLLM` already handles.
- **6b (message heuristics)** — analogous to `MultimodalRouter` scanning for images — is brittle. Coder vs planner is not a content-shape distinction; it's a task-role distinction the caller knows explicitly.
- **6c (LLMCallContext metadata)** honors §2.4's routing model, uses an SDK-provided channel (`LLMCallContext`), keeps dispatch logic explicit and testable, and requires zero content parsing. Callers set `call_context.metadata["role"] = "planner"` when dispatching planner work (via `DelegateTool` or directly); default route is coder.

**Why option 7a (coder as condenser) over 7b (dedicated small model):**
- No Phase 0.x benchmark exists for a condenser role. Introducing a 4th service pre-benchmark violates "quality first" (unmeasured) and "single-user local-first" (extra service overhead).
- Coder is already competent at summarization (qwen3-coder is a general instruct-tuned model, not summarization-averse).
- Zero additional VRAM contention: the coder is already resident when the coder is running; the condenser call reuses the same endpoint. Under the coder-XOR-planner co-residency contract (ADR-0017 amend), when the planner is resident, the condenser call routes to the planner via the router — still zero extra services.
- Reversal path is cheap: swap `LLMSummarizingCondenser(llm=coder)` → `LLMSummarizingCondenser(llm=dedicated)` in `config/agent.py`. Deferred to post-Phase-3 if evidence emerges that coder-as-condenser degrades any measured criterion.

**Alternatives considered and rejected:**
- **Preserve spec's TOML surface, author custom loader** — reproduces work SDK deliberately omits, adds a schema-drift attack surface, and buys nothing over direct Python construction.
- **Wait for a hypothetical future SDK version to add TOML support** — indefinite delay; SDK 1.41 is the pinned baseline; scope creep.
- **Populate TOML for documentation only, alongside Python** — dual sources of truth invite drift. The ADR itself and inline docstrings in `config/agent.py` document intent adequately.

## Consequences

**Files created:**
- `config/agent.py` — canonical Python config module (this ADR's primary deliverable).
- `config/router.py` — `CoderPlannerRouter(RouterLLM)` subclass with `select_llm(messages, call_context)`.
- `scripts/populate-max-output-tokens.sh` — populates `config/max-output-tokens.json` with spec-sheet ceiling values (8192 for both roles) and provenance flavor `SPEC_SHEET`. See status amendment above for the empirical-measurement gap that made this necessary. Values are overridable via `CODER_MAX_OUTPUT_TOKENS` / `PLANNER_MAX_OUTPUT_TOKENS` env vars.
- `config/max-output-tokens.json` — provenance record with per-role `value`, `source`, `provenance` flavor (`SPEC_SHEET` or `EMPIRICAL_PHASE_3`), `populated_at`, and `empirical_override_pending` pointer to ADR-0035 (deferred, fires only if Phase 3 or later observes response length approaching the ceiling).
- `bench/smoke-phase-3/task.md` — minimal trivial task (Phase 3 verification, spec L378-383 first row).
- `bench/smoke-phase-3/run.sh` — smoke runner: brings up coder endpoint, runs task, asserts event stream + FinishAction.

**Files amended:**
- `docs/specs/integration-execution-plan-v16.md` §2.4 — footnote linking to this ADR; the TOML block retained as intent-documentation with a note that the canonical surface is `config/agent.py`.
- `config/README.md` — updated to describe the Python config surface (removes the "empty by design" language).
- `adrs/README.md` — index row for ADR-0033.

**Hook allow-list:**
- `hooks/pre-commit/no-localworkspace.sh` — the `config/` directory becomes hot. No allow-list change needed (config files won't reference LocalWorkspace).

**Phase 3 verification matrix (spec L378-386):**
- Row 1: trivial task under `DockerWorkspace` with `agent = build_agent()` from `config/agent.py` → event stream + confirmation UI + tool-calling functional.
- Row 2: role-switch test — dispatch a planner task via `DelegateTool` with `call_context.metadata["role"]="planner"` → `CoderPlannerRouter.select_llm` selects planner; supervisor swap logic (existing in `scripts/serve-planner.sh` + `scripts/stop-large-model.sh`) executes coder→planner GPU handoff.

**Downstream ADRs:**
- Phase 3 verdict lands as **ADR-0034** (Ratified once both matrix rows pass).
- If coder-as-condenser shows evidence of degradation during Phase 3 or later, file **ADR-0035** to swap in a dedicated condenser.

**Contingencies:**
- If Phase 3 discovers the SDK routes condenser calls through a code path that bypasses the router (i.e., condenser LLM is invoked directly, not via `Agent.llm`), the `LLMSummarizingCondenser(llm=coder)` binding is still correct — the condenser holds its own LLM reference. No amendment needed unless the SDK's condenser invocation surfaces a limitation.
- If `LLMCallContext` metadata does not propagate from `DelegateTool` invocation down to `RouterLLM.completion` in SDK 1.41 (i.e., the metadata channel is not populated by the delegator), fall back to option 6b (message-content heuristic on the last user message: presence of `[role:planner]` marker) as a stopgap and file an amendment. This is testable early in Phase 3.

## Lock-in phase

Phase 2.4 (config surface) locks in on first commit of `config/agent.py`. Phase 3 (verification matrix) confirms the wiring is end-to-end functional.

## References

- Spec `docs/specs/integration-execution-plan-v16.md` §2.4 (L328-357), §2.5 (L361-363), §Phase 3 (L367-386)
- SDK 1.41.0 introspection: `openhands/sdk/llm/router/base.py`, `openhands/sdk/llm/router/impl/multimodal.py`, `openhands/sdk/context/condenser` (via `local_conversation.py` L13), `openhands/tools/delegate/`, `openhands/tools/task/definition.py:198`
- VERSIONS.lock — `openhands-sdk 1.41.0`
- ADR-0017 (production role selection · co-residency Option 2 · coder XOR planner)
- ADR-0023, ADR-0025 (planner winner = qwen3_6-27b-q6k)
- ADR-0027, ADR-0029 (coder winner = qwen3-coder-30b-a3b-instruct-awq-4bit)
- ADR-0031 (embedder retention = qwen3-embedding-4B-Q8_0)
- ADR-0032 (Phase 1 spec-scope closure; 1.2 code-explorer deferred to Phase 2.4/3 tool registry)
