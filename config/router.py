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

from typing import TYPE_CHECKING, ClassVar

from openhands.sdk.llm.message import Message
from openhands.sdk.llm.router.base import RouterLLM
from openhands.sdk.logger import get_logger

if TYPE_CHECKING:
    from openhands.sdk.llm.llm import LLMCallContext


logger = get_logger(__name__)


class CoderPlannerRouter(RouterLLM):
    """Route coder vs planner via LLMCallContext.metadata['role']."""

    router_name: str = "coder_planner_router"

    CODER_KEY: ClassVar[str] = "coder"
    PLANNER_KEY: ClassVar[str] = "planner"
    ROLE_METADATA_KEY: ClassVar[str] = "role"

    # Phase 3 fallback flag: flipped to True if LLMCallContext.metadata
    # is not populated by DelegateTool dispatch. See ADR-0033 contingency.
    fallback_message_heuristic: bool = False

    def select_llm(
        self,
        messages: list[Message],
        call_context: "LLMCallContext | None" = None,
    ) -> str:
        """Select route from LLMCallContext.metadata['role'] (option 6c).

        Note: the RouterLLM base class's completion() signature does not
        pass call_context to select_llm by default in SDK 1.41; this
        subclass expects a Phase 3 patch or an override of completion()
        that forwards call_context. See ADR-0033 contingency notes.
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

        # Fallback path (option 6b): message-content heuristic
        if self.fallback_message_heuristic and messages:
            last_user = None
            for m in reversed(messages):
                if getattr(m, "role", None) == "user":
                    last_user = m
                    break
            if last_user is not None:
                content = getattr(last_user, "content", "") or ""
                if isinstance(content, str) and "[role:planner]" in content:
                    logger.info(
                        "CoderPlannerRouter: fallback heuristic matched → planner"
                    )
                    return self.PLANNER_KEY

        # Default: coder
        logger.info("CoderPlannerRouter: default → coder")
        return self.CODER_KEY
