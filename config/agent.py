"""config/agent.py — Canonical OpenHands-Ext v1 runtime configuration.

Per ADR-0033 (Phase 2.4 config surface: Python module, not TOML), this
module is the single source of truth for the tiered multi-LLM wiring
against Phase 0.3 winners.

Roles (all endpoints on 127.0.0.1, single-user local-first):

    coder     — qwen3-coder-30b-a3b-instruct-awq-4bit   vLLM :8100
                                                        (ADR-0029)
    planner   — qwen3_6-27b-q6k                         llama.cpp :8082
                                                        (ADR-0023, ADR-0025)
    embedder  — qwen3-embedding-4B-Q8_0                 llama.cpp :8090
                                                        (ADR-0031, retention)
    condenser — coder endpoint reused (ADR-0033-7a)     — no extra service

Co-residency contract (ADR-0017 amend):
    coder XOR planner + embedder   (coder and planner never co-run)

max_output_tokens values are loaded from config/max-output-tokens.json,
populated by scripts/populate-max-output-tokens.sh (spec-sheet ceiling per
ADR-0033 status amendment 2026-08-11 17:20 EDT; empirical override deferred
to ADR-0035 if Phase 3+ observes response length approaching the ceiling).

Usage:

    from config.agent import build_agent
    agent = build_agent()  # code-explorer subagent + task tool are wired by default

    # Delegating a planner subtask (Path B per ADR-0033 amend #5):
    # Prepend a [role:planner] marker to the leading user message; the
    # router's fallback_message_heuristic dispatches to the planner LLM.
    # Path A (metadata routing) is retained as forward-compat but inert
    # in SDK 1.41 because LLMCallContext has no `metadata` field.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from openhands.sdk import LLM, Agent
from openhands.sdk.context.condenser import LLMSummarizingCondenser

from config.router import CoderPlannerRouter


# ---------------------------------------------------------------------------
# Endpoints (ADR-0017 amend, ADR-0023/0025, ADR-0029, ADR-0031)
# ---------------------------------------------------------------------------

CODER_MODEL = "openai/qwen3-coder-30b-a3b-instruct-awq-4bit"
CODER_BASE_URL = "http://127.0.0.1:8100/v1"

PLANNER_MODEL = "openai/qwen3_6-27b-q6k"
PLANNER_BASE_URL = "http://127.0.0.1:8082/v1"

EMBEDDER_MODEL = "qwen3-embedding-4B-Q8_0"
EMBEDDER_BASE_URL = "http://127.0.0.1:8090/v1"

# Local endpoints don't authenticate; litellm still requires a non-empty key.
_LOCAL_API_KEY = SecretStr("EMPTY")

# Retry / timeout policy (matches spec §2.4 TOML values)
_NUM_RETRIES = 3
_RETRY_MIN_WAIT = 10
_RETRY_MAX_WAIT = 60


# ---------------------------------------------------------------------------
# Measured max_output_tokens (populated by scripts/extract-max-output-tokens.sh)
# ---------------------------------------------------------------------------

_MAX_OUT_PATH = Path(__file__).parent / "max-output-tokens.json"


def _load_max_output_tokens() -> dict[str, int]:
    """Return {"coder": int, "planner": int} from the provenance file.

    Fails loud if the file is missing. Run scripts/populate-max-output-tokens.sh
    first. The provenance file records `provenance` flavor (SPEC_SHEET or
    EMPIRICAL_PHASE_3) per ADR-0033.
    """
    if not _MAX_OUT_PATH.exists():
        raise FileNotFoundError(
            f"config/max-output-tokens.json not found at {_MAX_OUT_PATH}. "
            "Run scripts/populate-max-output-tokens.sh to populate it "
            "before importing this module."
        )
    data = json.loads(_MAX_OUT_PATH.read_text())
    out: dict[str, int] = {}
    for role in ("coder", "planner"):
        if role not in data:
            raise KeyError(
                f"config/max-output-tokens.json missing role '{role}'. "
                "Re-run scripts/extract-max-output-tokens.sh."
            )
        entry = data[role]
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError(
                f"config/max-output-tokens.json[{role!r}] malformed: "
                f"expected {{'value': int, 'source': str, 'measured_at': str}}."
            )
        out[role] = int(entry["value"])
    return out


# ---------------------------------------------------------------------------
# LLM factories
# ---------------------------------------------------------------------------


def build_coder_llm(max_output_tokens: int) -> LLM:
    """Coder LLM — vLLM :8100 (ADR-0029)."""
    return LLM(
        model=CODER_MODEL,
        base_url=CODER_BASE_URL,
        api_key=_LOCAL_API_KEY,
        num_retries=_NUM_RETRIES,
        retry_min_wait=_RETRY_MIN_WAIT,
        retry_max_wait=_RETRY_MAX_WAIT,
        max_output_tokens=max_output_tokens,
        usage_id="coder",
    )


def build_planner_llm(max_output_tokens: int) -> LLM:
    """Planner LLM — llama.cpp :8082 (ADR-0023, ADR-0025).

    Thinking disabled by default per ADR-0008. If a caller needs thinking
    on, pass the appropriate provider-specific flag via LLMCallContext.
    """
    return LLM(
        model=PLANNER_MODEL,
        base_url=PLANNER_BASE_URL,
        api_key=_LOCAL_API_KEY,
        num_retries=_NUM_RETRIES,
        retry_min_wait=_RETRY_MIN_WAIT,
        retry_max_wait=_RETRY_MAX_WAIT,
        max_output_tokens=max_output_tokens,
        usage_id="planner",
    )


def build_embedder_llm() -> LLM:
    """Embedder LLM — llama.cpp :8090 (ADR-0031).

    No max_output_tokens (embedding models return vectors, not tokens).
    """
    return LLM(
        model=EMBEDDER_MODEL,
        base_url=EMBEDDER_BASE_URL,
        api_key=_LOCAL_API_KEY,
        num_retries=_NUM_RETRIES,
        retry_min_wait=_RETRY_MIN_WAIT,
        retry_max_wait=_RETRY_MAX_WAIT,
        usage_id="embedder",
    )


# ---------------------------------------------------------------------------
# Router + Condenser wiring
# ---------------------------------------------------------------------------


def build_router(coder: LLM, planner: LLM) -> CoderPlannerRouter:
    """CoderPlannerRouter with Path B message-marker routing (ADR-0033 amend #5).

    SDK 1.41's ``LLMCallContext`` is a frozen dataclass exposing only
    ``prompt_cache_key`` and ``session_id`` — no ``metadata`` field. Option 6c
    (metadata-based routing) is not implementable without forking the SDK.
    Amend #5 (2026-08-11 18:01 EDT) formally selects Path B (option 6b):
    ``fallback_message_heuristic=True`` inspects the last user message for a
    ``[role:planner]`` marker. Path A's ``completion()`` override remains in
    place as forward-compatibility — no-op today, active if the SDK later
    exposes ``metadata`` on ``LLMCallContext``.
    """
    return CoderPlannerRouter(
        model="openai/coder-planner-router",  # placeholder; router intercepts
        api_key=_LOCAL_API_KEY,
        usage_id="coder_planner_router",
        llms_for_routing={
            CoderPlannerRouter.CODER_KEY: coder,
            CoderPlannerRouter.PLANNER_KEY: planner,
        },
        fallback_message_heuristic=True,
    )


def build_condenser(coder: LLM) -> LLMSummarizingCondenser:
    """Condenser reuses the coder endpoint (ADR-0033-7a).

    Spec §2.4 verbatim: temperature=0.1, max_input_tokens=1024. Re-interpreted
    per SDK 1.41 inspection (2026-08-11 17:20 EDT and 17:45 EDT):

      * `max_input_tokens=1024` on the `LLM` is REJECTED by SDK 1.41
        (MIN_CONTEXT_WINDOW_TOKENS=16384). Spec was authored pre-inspection.
      * `temperature=0.1` applied at the LLM level (correct home).
      * `LLMSummarizingCondenser.max_tokens` is the TRIGGER threshold
        (`llm_summarizing_condenser.py:117` — "if total_tokens > max_tokens:
        condense"), NOT a summary-output cap. Setting it to 1024 caused
        first-turn condensation (system prompt alone is ~5495 tokens),
        destroying context and forcing the agent to replan from a fabricated
        summary. See DEBUG_LOG 2026-08-11 17:45 EDT.
      * Spec's "1024" is honored per ADR-0033 amend #3 (2026-08-11 17:47 EDT)
        as the condenser LLM's `max_output_tokens=1024`, capping the *summary
        text* the condenser produces. The trigger threshold is set to 30000
        tokens — practically all of the coder context — so condensation only
        fires as a safety net near context exhaustion.

    The condenser holds its own LLM reference; if Phase 3 shows degradation,
    swap the LLM argument to a dedicated model without touching call sites.
    See ADR-0033 STATUS AMENDMENTS.
    """
    # A dedicated LLM instance for the condenser role, keyed off the coder
    # endpoint but with condenser-specific sampling.
    # max_output_tokens=1024 caps the SUMMARY OUTPUT length (spec §2.4 intent).
    condenser_llm = LLM(
        model=CODER_MODEL,
        base_url=CODER_BASE_URL,
        api_key=_LOCAL_API_KEY,
        num_retries=_NUM_RETRIES,
        retry_min_wait=_RETRY_MIN_WAIT,
        retry_max_wait=_RETRY_MAX_WAIT,
        temperature=0.1,
        max_output_tokens=1024,
        usage_id="condenser",
    )
    # max_tokens=30000: trigger threshold (SDK checks `total_tokens > max_tokens`).
    # Set near coder context ceiling so condensation is a safety net, not first-turn.
    # max_size=240 (SDK default) and keep_first=2 (SDK default) unchanged.
    return LLMSummarizingCondenser(llm=condenser_llm, max_tokens=30000)


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


def build_agent(
    tools: list[Any] | None = None,
    enable_browser: bool = False,
    enable_sub_agents: bool = True,
    enable_code_explorer: bool = True,
) -> Agent:
    """Build a fully-wired OpenHands-Ext v1 Agent.

    Default tool set (ADR-0032 lock-in for Phase 2.4/3):

      * TerminalTool + FileEditorTool + TaskTrackerTool  (standard SDK)
      * TaskToolSet (aka DelegateTool)                   (enables
        `code-explorer` and any other registered subagent)
      * BrowserToolSet                                   (opt-in only;
        heavy dependency, single-user local doesn't need it by default)

    Args:
        tools: Optional caller-supplied tool list. If provided, it fully
            REPLACES the default tool set — caller owns wiring completely.
        enable_browser: Include `BrowserToolSet`. Off by default (spec
            §2.4 doesn't require it; opt in per-task if needed).
        enable_sub_agents: Include `TaskToolSet` so the agent can delegate
            to registered subagents (e.g. `code-explorer`). On by default.
        enable_code_explorer: Register the built-in `code-explorer`
            subagent (from `openhands.tools.preset.subagents/code_explorer.md`)
            before returning. On by default. Satisfies Phase 2.4 DoD
            item "register code-explorer in the runtime tool registry"
            (ADR-0032 deferral).

    Returns:
        Agent(llm=router, condenser=condenser, tools=<default or caller-supplied>)
    """
    mot = _load_max_output_tokens()
    coder = build_coder_llm(mot["coder"])
    planner = build_planner_llm(mot["planner"])
    router = build_router(coder, planner)
    condenser = build_condenser(coder)

    # Register the code-explorer subagent (idempotent via
    # register_agent_if_absent inside register_builtins_agents).
    if enable_code_explorer:
        from openhands.tools.preset.default import register_builtins_agents

        register_builtins_agents(enable_browser=enable_browser)

    # Default tool set unless caller fully overrides.
    if tools is None:
        from openhands.tools import get_default_tools

        tools = get_default_tools(
            enable_browser=enable_browser,
            enable_sub_agents=enable_sub_agents,
        )

    return Agent(
        llm=router,
        condenser=condenser,
        tools=tools,
    )


__all__ = [
    "CODER_MODEL",
    "CODER_BASE_URL",
    "PLANNER_MODEL",
    "PLANNER_BASE_URL",
    "EMBEDDER_MODEL",
    "EMBEDDER_BASE_URL",
    "build_coder_llm",
    "build_planner_llm",
    "build_embedder_llm",
    "build_router",
    "build_condenser",
    "build_agent",
]
