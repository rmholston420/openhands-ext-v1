"""tests/sdk_patch/test_llm_discriminated_union.py

Contract test for the ADR-0034 vendored SDK patch.

The patch makes `LLM` inherit `DiscriminatedUnionMixin` so that
`LLM.model_validate(dumped_subclass)` reconstructs the correct concrete
subclass (e.g. `CoderPlannerRouter`) instead of flattening to base `LLM`
and dropping subclass-only fields like `llms_for_routing`.

This is the failure mode Phase 3.j hit: the container's `StartConversationRequest`
declares `agent: AgentBase`, dispatches to `Agent`, which then validates
`llm: LLM` — the base validator would drop `router_name`, `llms_for_routing`,
`active_llm`, and instantiate a plain `LLM`. With `DiscriminatedUnionMixin`,
the annotation-type validator dispatches on the serialized `kind` field to
the actual concrete subclass.

Test does the round-trip client-side so the failure is caught immediately
and doesn't require spinning up the container.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import SecretStr

from openhands.sdk.llm.llm import LLM
from openhands.sdk.utils.models import DiscriminatedUnionMixin

# The subclass we ship in `config/router.py`.
# Kept as a local import so `pytest --collect-only` doesn't require it
# to be reachable when only the LLM contract matters.
from config.router import CoderPlannerRouter


def _make_llm(service_id: str, model: str, base_url: str) -> LLM:
    """Build a minimal LLM instance without triggering network preflight."""
    return LLM(
        service_id=service_id,
        model=model,
        base_url=base_url,
        api_key=SecretStr("sk-test-not-used"),
    )


def _make_router() -> CoderPlannerRouter:
    """Build a CoderPlannerRouter with two concrete LLMs for routing."""
    coder = _make_llm(
        service_id="coder",
        model="hosted_vllm/qwen3-coder-30b-a3b-instruct-awq-4bit",
        base_url="http://127.0.0.1:8100/v1",
    )
    planner = _make_llm(
        service_id="planner",
        model="hosted_vllm/qwen3_6-27b-q6k",
        base_url="http://127.0.0.1:8082/v1",
    )
    return CoderPlannerRouter(
        service_id="router",
        # Router-level model is required by the LLM base — reuse coder's
        # so `active_llm` defaulting to None is safe.
        model="hosted_vllm/qwen3-coder-30b-a3b-instruct-awq-4bit",
        base_url="http://127.0.0.1:8100/v1",
        api_key=SecretStr("sk-test-not-used"),
        llms_for_routing={"coder": coder, "planner": planner},
    )


def test_llm_inherits_discriminated_union_mixin():
    """The patched LLM class must have DiscriminatedUnionMixin in its MRO."""
    assert DiscriminatedUnionMixin in LLM.__mro__, (
        f"ADR-0034 patch not applied: DiscriminatedUnionMixin missing from "
        f"LLM MRO. Got: {[c.__name__ for c in LLM.__mro__]}"
    )


def test_router_subclass_survives_llm_annotated_round_trip():
    """A CoderPlannerRouter dumped and re-validated as `LLM` must come back
    as `CoderPlannerRouter`, not base `LLM`.

    This is the core failure mode ADR-0034 fixes. Container-side, the
    `Agent.llm: LLM` annotation drives validation; without the mixin,
    Pydantic instantiates a base `LLM` and drops subclass fields.
    """
    original = _make_router()
    assert type(original).__name__ == "CoderPlannerRouter"
    assert original.llms_for_routing.keys() == {"coder", "planner"}

    dumped = original.model_dump(mode="json")

    # The container calls `LLM.model_validate(dumped)`. With the mixin,
    # the LLM validator dispatches on the discriminator field to the
    # concrete subclass. Without the mixin, this returns a base LLM.
    reconstructed = LLM.model_validate(dumped)

    assert type(reconstructed).__name__ == "CoderPlannerRouter", (
        f"Expected CoderPlannerRouter after LLM.model_validate, got "
        f"{type(reconstructed).__name__}. Patch is not effective — "
        f"discriminator dispatch failed."
    )
    assert isinstance(reconstructed, CoderPlannerRouter)

    # llms_for_routing must survive round-trip
    assert reconstructed.llms_for_routing.keys() == {"coder", "planner"}, (
        f"llms_for_routing lost after round-trip. "
        f"Got: {list(reconstructed.llms_for_routing.keys())}"
    )

    # Nested LLMs should be base LLM instances (not routers)
    for name, sub in reconstructed.llms_for_routing.items():
        assert isinstance(sub, LLM), f"llms_for_routing[{name!r}] is not an LLM: {type(sub)}"
        assert sub.service_id == name

    # router_name must survive
    assert reconstructed.router_name == "coder_planner_router"


def test_base_llm_still_round_trips_as_base_llm():
    """A plain LLM must not be misclassified as a router by discriminator dispatch."""
    original = _make_llm(
        service_id="plain",
        model="hosted_vllm/qwen3-coder-30b-a3b-instruct-awq-4bit",
        base_url="http://127.0.0.1:8100/v1",
    )
    dumped = original.model_dump(mode="json")
    reconstructed = LLM.model_validate(dumped)
    # Base LLM should come back as LLM, not any subclass
    assert type(reconstructed) is LLM, (
        f"Base LLM misclassified as {type(reconstructed).__name__}"
    )
    assert reconstructed.service_id == "plain"


if __name__ == "__main__":
    # Also runnable standalone: `python tests/vendor/test_llm_discriminated_union.py`
    pytest.main([__file__, "-v"])
