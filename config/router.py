"""config/router.py — CoderPlannerRouter for OpenHands-Ext v1.

Canonical routing surface per ADR-0033. Dispatches between the coder role
(default) and planner role based on `LLMCallContext.metadata["role"]`.

Design contract (ADR-0033-decision-6c):
    call_context.metadata["role"] == "planner"  → route to planner LLM
    otherwise (including missing metadata)      → route to coder LLM

If SDK 1.41's DelegateTool does not populate LLMCallContext.metadata at
dispatch time (a Phase 3 verification finding), fall back to option 6b
(message-content heuristic on presence of `[role:planner]` marker in the
last user message). Fallback is intentionally guarded behind a class
attribute so Phase 3 can flip it without touching call sites.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

from openhands.sdk.llm.message import Message
from openhands.sdk.llm.router.base import RouterLLM
from openhands.sdk.llm.streaming import TokenCallbackType
from openhands.sdk.logger import get_logger
from openhands.sdk.tool.tool import ToolDefinition

if TYPE_CHECKING:
    from openhands.sdk.llm.llm import LLMCallContext
    from openhands.sdk.llm.llm_response import LLMResponse


logger = get_logger(__name__)


class CoderPlannerRouter(RouterLLM):
    """Route coder vs planner via LLMCallContext.metadata['role'].

    Path A workaround (ADR-0033 amend #4, 2026-08-11 17:52 EDT):

    SDK 1.41's `RouterLLM.completion()` receives `call_context` but does NOT
    forward it to `select_llm()` (`base.py:82` calls `self.select_llm(messages)`
    with no context). This subclass overrides `completion()` to route with
    both `messages` AND `call_context`, then delegates to the base LLM's
    `completion()` for the actual API call. When the SDK forwards
    `call_context` natively, this override becomes a no-op and can be removed.
    """

    router_name: str = "coder_planner_router"

    CODER_KEY: ClassVar[str] = "coder"
    PLANNER_KEY: ClassVar[str] = "planner"
    ROLE_METADATA_KEY: ClassVar[str] = "role"

    # Phase 3 fallback flag: flipped to True if LLMCallContext.metadata
    # is not populated by DelegateTool dispatch. See ADR-0033 contingency.
    fallback_message_heuristic: bool = False

    def completion(
        self,
        messages: list[Message],
        tools: Sequence[ToolDefinition] | None = None,
        add_security_risk_prediction: bool = False,
        on_token: TokenCallbackType | None = None,
        call_context: "LLMCallContext | None" = None,
        **kwargs,
    ) -> "LLMResponse":
        """Override base to pass `call_context` into `select_llm` (Path A).

        Replicates `RouterLLM.completion()` body but calls the subclass's
        `select_llm(messages, call_context)` instead of the base's
        `select_llm(messages)`. The trailing delegation to `active_llm` is
        identical to the base.
        """
        selected_model = self.select_llm(messages, call_context)
        self.active_llm = self.llms_for_routing[selected_model]
        logger.info(f"RouterLLM routing to {selected_model}...")
        return self.active_llm.completion(
            messages=messages,
            tools=tools,
            add_security_risk_prediction=add_security_risk_prediction,
            on_token=on_token,
            call_context=call_context,
            **kwargs,
        )

    def select_llm(
        self,
        messages: list[Message],
        call_context: "LLMCallContext | None" = None,
    ) -> str:
        """Select route from LLMCallContext.metadata['role'] (option 6c).

        Reached via this subclass's overridden `completion()`, which
        forwards `call_context` (Path A per ADR-0033 amend #4).
        """
        # Primary path: LLMCallContext metadata (option 6c)
        if call_context is not None:
            role = None
            metadata = getattr(call_context, "metadata", None)
            if isinstance(metadata, dict):
                role = metadata.get(self.ROLE_METADATA_KEY)
            if role == self.PLANNER_KEY:
                logger.info("CoderPlannerRouter: metadata role=planner → planner")
                return self.PLANNER_KEY
            if role == self.CODER_KEY:
                logger.info("CoderPlannerRouter: metadata role=coder → coder")
                return self.CODER_KEY

        # Fallback path (option 6b): message-content heuristic.
        # SDK 1.41 Message.content is list[TextContent | ImageContent | ...];
        # older shapes may be a bare str. Handle both.
        if self.fallback_message_heuristic and messages:
            last_user = None
            for m in reversed(messages):
                if getattr(m, "role", None) == "user":
                    last_user = m
                    break
            if last_user is not None:
                content = getattr(last_user, "content", "") or ""
                if isinstance(content, list):
                    text = "".join(
                        str(getattr(block, "text", "") or "") for block in content
                    )
                else:
                    text = str(content)
                if "[role:planner]" in text:
                    logger.info(
                        "CoderPlannerRouter: fallback heuristic matched → planner"
                    )
                    return self.PLANNER_KEY

        # Default: coder
        logger.info("CoderPlannerRouter: default → coder")
        return self.CODER_KEY
