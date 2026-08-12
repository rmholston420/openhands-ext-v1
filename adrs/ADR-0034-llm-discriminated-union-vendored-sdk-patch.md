# ADR-0034 — Vendor openhands-sdk to patch `LLM` for `DiscriminatedUnion` serialization (Phase 3.j RouterLLM survival under RemoteConversation)

**Status:** Proposed
**Lock-in phase:** Phase 3.j (RouterLLM verification under RemoteConversation) · Phase 2.4 (config surface, ADR-0033 completion)
**Supersedes:** —

> **STATUS AMENDMENT (2026-08-11 22:05 EDT):** Contract test surfaced the concern flagged in the previous amendment. Base `LLM` is concrete (no `ABC` in bases, no `@abstractmethod`), so `DiscriminatedUnionMixin._validate_subtype` never reaches its subclass-dispatch branch — it hits `assert kind is None or kind == cls.__name__` and fails when validating a dumped `CoderPlannerRouter` payload against the base `LLM` annotation. Making `LLM` abstract would break `LLM(...)` instantiation everywhere in existing code (`resolve_kind("LLM")` searches subclasses only). **Resolution:** the patch now also overrides `_validate_subtype` inside the `LLM` class itself (same-name method on a subclass replaces the mixin's — verified empirically). The override dispatches to `cls.resolve_kind(kind)` when the discriminator names a subclass, and strips the computed `kind` field before delegating to the pydantic handler when it matches or is absent. Patch grows from ~2 lines to ~35 lines (still surgical, still on `openhands-sdk/openhands/sdk/llm/llm.py` only). See BUILD_LOG 2026-08-11 22:05 EDT and updated patch at `patches/openhands-sdk-llm-discriminated-union.patch`. Simulation of the override against a pure-Python model of `DiscriminatedUnionMixin` passes all three round-trip cases (base LLM, router via base annotation, router via own class). ADR remains Proposed until the Colossus contract test passes end-to-end.

> **STATUS AMENDMENT (2026-08-11 21:40 EDT):** Alternatives section expanded from three rejected options to a fuller nine-option analysis. Original three options remain rejected for the same reasons; the six additions document alternatives evaluated during a deeper research pass before implementation. Evidence gathered: direct inspection of upstream `RemoteConversation.__init__` payload construction (`openhands-sdk/openhands/sdk/conversation/impl/remote_conversation.py:832` — dumps `agent.model_dump(mode="json", context={"expose_secrets": True})` and POSTs to server); upstream v1.42.0 tag inspection (LLM class line unchanged from v1.41.0 — bug is not fixed in the next release); upstream issue/PR search — no open PR addresses this; closed PRs #1801 (LLMSerializationContext) and #311 (schema-first persistence, remove DU) went in a different direction and were both unmerged. Decision unchanged: vendor + patch is still the correct path. Original decision text preserved below.

## Context

Phase 3 verification-matrix row 3.j requires that `CoderPlannerRouter(RouterLLM)` — the canonical routing surface established by ADR-0033 — survives serialization through `RemoteConversation`'s agent-server boundary. Direct instrumentation on Colossus 2026-08-11 21:24 EDT with SDK 1.41.0 established:

1. **`RouterLLM.llms_for_routing` is a proper Pydantic field** (`dict[str, LLM]`, default_factory=dict). It serializes correctly under `router.model_dump(mode="json")` — both nested `coder` and `planner` `LLM` payloads appear in the output with their `model` and `base_url` intact.

2. **`CoderPlannerRouter.model_validate(dumped)` round-trips correctly.** Rebuilt instance is `CoderPlannerRouter`, `llms_for_routing` has both keys, nested LLMs have correct `model`/`base_url`.

3. **`LLM.model_validate(dumped)` LOSES the subclass.** Because `Agent.llm: LLM` is annotated as base `LLM` (not a union, no discriminator), pydantic instantiates a base `LLM(model="router", base_url=None, ...)` and silently drops `llms_for_routing`, `router_name`, `active_llm` — the entire `RouterLLM` surface.

4. **This is what `RemoteConversation` does container-side.** `StartConversationRequest.agent: AgentBase` deserializes correctly (Agent is polymorphic — see below), but nested `Agent.llm: LLM` deserializes to base `LLM`, so any `RouterLLM` subclass is flattened before the agent ever runs. Requests then ship to litellm with `model="router"` and no `base_url`, hitting `api.openai.com`.

5. **`AgentBase` inherits `DiscriminatedUnionMixin`** (`openhands/sdk/utils/models.py`). The mixin injects a `kind` computed field (defaults to `__class__.__name__`) on dump and dispatches to the correct subclass on validate via `_validate_subtype`. This is why `Agent` survives the boundary but `LLM` does not.

6. **`LLM` and `RouterLLM` do NOT inherit `DiscriminatedUnionMixin`.** SDK 1.41 MROs (confirmed):
    - `LLM`: `[LLM, BaseModel, RetryMixin, NonNativeToolCallingMixin, object]`
    - `RouterLLM`: `[RouterLLM, LLM, BaseModel, RetryMixin, NonNativeToolCallingMixin, object]`
    - `AgentBase`: `[AgentBase, DiscriminatedUnionMixin, OpenHandsModel, BaseModel, ABC, object]`

7. **Upstream has no open issue or PR for this.** GitHub search (`OpenHands/software-agent-sdk`) for `"RouterLLM DiscriminatedUnion"`, `"RouterLLM RemoteConversation"`, `"llm.py DiscriminatedUnionMixin"` returns zero hits. `Tool`, `Event`, `Condenser`, `Workspace`, `Analyzer`, `Critic`, `Secret`, `Agent`, `MCPTool` all inherit `DiscriminatedUnionMixin`; **`LLM` is the only major SDK type that does not.** Absence appears to be an oversight, not a design decision.

8. **API keys are also lost.** `SecretStr` fields serialize to `"**********"` under `mode="json"`, so any `LLM` reconstructed container-side would have no credentials even if the subclass survived. Separate issue — will be addressed in a follow-up ADR after this fix lands.

The Phase 3.c smoke previously bypassed the router by mutating `agent.llm = build_coder_llm(...)` after Agent construction. That workaround is not compatible with the ADR-0033 routing design and cannot verify Phase 3.j.

## Decision

**Vendor openhands-sdk into `vendor/openhands-sdk/` and apply a minimal patch making `LLM` inherit `DiscriminatedUnionMixin`.**

Concretely:

1. **Vendor point-in-time**: pin openhands-sdk at the currently installed commit (v1.41.0, matching `VERSIONS.lock`). Vendored as `vendor/openhands-sdk/` (git subtree, not submodule — Kosmos discipline: no external state).

2. **Patch surface** (`openhands-sdk/openhands/sdk/llm/llm.py`):
    - Import: `from openhands.sdk.utils.models import DiscriminatedUnionMixin`
    - Change: `class LLM(BaseModel, RetryMixin, NonNativeToolCallingMixin):` → `class LLM(DiscriminatedUnionMixin, RetryMixin, NonNativeToolCallingMixin):`
    - `DiscriminatedUnionMixin` inherits from `OpenHandsModel(BaseModel)`, so `BaseModel` remains in the MRO.
    - **[Amended 2026-08-11 22:05 EDT]** Also override `_validate_subtype` inside `LLM` (using `@model_validator(mode="wrap")` on the same-name method — pydantic recognizes this as a class-level override of the mixin's inherited validator; verified empirically). The override dispatches to `cls.resolve_kind(kind)` when the discriminator names a strict subclass, and strips the computed `kind` field before falling through to the pydantic handler otherwise. This works around the mixin's assumption that the base is abstract (`_is_abstract(cls)`), which is false for `LLM` and cannot be made true without breaking direct `LLM(...)` construction across upstream and user code.

3. **Install vendored SDK in editable mode**: replace pip-installed `openhands-sdk==1.41.0` with `pip install -e vendor/openhands-sdk/openhands-sdk` in the ext repo venv. Update `pyproject.toml` and `VERSIONS.lock` to point at the vendored path (mark as `local:vendor/openhands-sdk/openhands-sdk` with the base commit SHA in a comment).

4. **`CoderPlannerRouter` and `RouterLLM` inherit the mixin transitively** through `LLM`. No changes to `config/router.py` required.

5. **`Agent.llm: LLM` becomes a discriminated field automatically** via `DiscriminatedUnionMixin.__get_pydantic_json_schema__` and `_validate_subtype`. Pydantic model rebuild is triggered by importing all `LLM` subclasses (including `CoderPlannerRouter`) before `Agent` is instantiated. Guaranteed at import order: `config/router.py` imports `CoderPlannerRouter` before `config/agent.py::build_agent()` is called.

6. **PORTING_LEDGER.md entry** recorded per `kosmos-port-workflow` skill discipline: source URL, commit SHA, SPDX license (MIT), modifications enumerated.

7. **Contract test** at `tests/vendor/test_llm_discriminated_union.py`: (a) construct `CoderPlannerRouter`, (b) `dump = agent.model_dump(mode="json")`, (c) `rebuilt = Agent.model_validate(dump)`, (d) assert `type(rebuilt.llm) is CoderPlannerRouter` and `list(rebuilt.llm.llms_for_routing.keys()) == ["coder", "planner"]`. Test lives outside `src/` because it exercises vendored code.

8. **Phase 3.j smoke** at `bench/smoke-phase-3-item-3j/`: builds `Agent(llm=CoderPlannerRouter(...))`, submits via `RemoteConversation`, asserts the request hits `http://127.0.0.1:8100/v1` (coder endpoint), not `api.openai.com`. Verified via router-log line `RouterLLM routing to coder...` in container logs + successful FinishAction event with real token counts.

9. **Contingency — vendored patch invalidated by future SDK update**: pin openhands-sdk at v1.41.0 for the remainder of Phase 3. When upgrading SDK, re-apply the patch, re-run 3.j smoke, append DEBUG_LOG entry, amend this ADR with new commit SHA. Do NOT auto-upgrade openhands-sdk in `VERSIONS.lock` without this loop.

10. **Upstreamability**: after 3.j passes, open PR at `OpenHands/software-agent-sdk` proposing the same change with the ADR-0034 rationale as the PR body. If accepted upstream, this ADR flips to `Superseded by upstream fix` and the vendor is removed at the next SDK bump.

## Rationale

**Why vendor over monkey-patch:**
- `LLM.__bases__` mutation at runtime does not reliably regenerate pydantic's CoreSchema. Pydantic models cache their validation/serialization schemas at class-creation time; injecting a mixin into `__bases__` after import is spooky and easy to have silently-inert failures.
- Kosmos discipline (project instructions): vendor before hand-build, log every port. This is the exact pattern.
- Vendored code is inspectable, versioned, and diffable. A monkey-patch is invisible in code review.

**Why vendor over site-packages patch:**
- Site-packages edits are lost on any `pip install --force-reinstall` or environment rebuild.
- Not visible in git history.
- Cannot be shared across environments.

**Why vendor over "skip 3.j, route client-side":**
- Client-side routing (select LLM before `Conversation.send_message`) violates spec §2.4's routing model — the router lives INSIDE the agent, not in front of it.
- `DelegateTool` cannot dispatch role-based calls if the router doesn't survive serialization — this blocks 3.h-2 (co-resident delegation) and 3.i (joint role-switch) as well.
- Postponing forces every future routing question to work around the same bug.

**Why `LLM` inherits `DiscriminatedUnionMixin` (not `RouterLLM` or `CoderPlannerRouter`):**
- The type annotation on `Agent.llm` is `LLM`. Only patching `RouterLLM` leaves the field annotation still resolving to base `LLM` at schema-generation time — the discriminator is never consulted because pydantic doesn't see a union.
- Patching `LLM` itself makes `LLM` the abstract discriminator base with concrete subclasses (`LLM`, `RouterLLM`, `CoderPlannerRouter`, and any future subclasses like `MultimodalRouter`, `RandomRouter`) as the union members. Pydantic's `_validate_subtype` picks the right one via `kind`.
- `DiscriminatedUnionMixin` handles both the abstract case (dispatches via `resolve_kind`) and the concrete case (validates `kind == cls.__name__` and passes through). Applying to `LLM` produces both behaviors correctly.

**Alternatives considered and rejected:**

The core constraint is that `RemoteConversation.__init__` (SDK 1.41 `openhands-sdk/openhands/sdk/conversation/impl/remote_conversation.py:832`) POSTs a JSON payload built via `agent.model_dump(mode="json", context={"expose_secrets": True})` to the agent-server. Server-side validation runs SDK code inside the container: `StartConversationRequest.agent: AgentBase` dispatches via `DiscriminatedUnionMixin` to the concrete Agent subclass (works — `agent_kind` mixin is in place); then `Agent.llm: LLM` validates the nested payload against base `LLM` — and this is where any `RouterLLM` subclass is flattened. **A viable fix must alter what happens when the SDK's own type-annotated `LLM` field is validated inside the container.** Ext-side subclassing, transport-layer overrides, and field-level `SerializeAsAny` all fail this constraint.

1. **Monkey-patch `LLM.__bases__` in `openhands_ext/__init__.py` (client-side runtime injection)** — Rejected. Pydantic v2 caches each model's CoreSchema at class-creation time; injecting a mixin into `__bases__` after import does not reliably regenerate that schema. Also invisible in code review and lost on any environment rebuild. Also only patches the client-side interpreter — the container has its own SDK install.

2. **Patch only `RouterLLM` (not base `LLM`) to inherit `DiscriminatedUnionMixin`** — Rejected. The container-side validator dispatched is the one attached to `Agent.llm`'s annotation type. That type is base `LLM`. Only patching a subclass leaves the annotated type's validator unchanged — pydantic never calls `RouterLLM.model_validate` for that field because it doesn't know a discriminator exists. The mixin must be on the annotation type.

3. **Ext-side `AgentWithRouterFix(Agent)` subclass with a custom `model_validator` on `llm`** — Rejected. Even if ext code builds an `AgentWithRouterFix` instance client-side, the JSON payload's `agent_kind` field determines what the container rebuilds. Ext-side subclasses are not registered inside the container's SDK, so the container falls back to base `Agent`. Base `Agent.llm: LLM` runs the SDK-1.41 validator with no discriminator. Client-side subclassing cannot influence container-side validation.

4. **Add an LLM-module-import mechanism to the SDK (analogous to `tool_module_qualnames`)** — Rejected. The SDK already exposes `StartConversationRequest.tool_module_qualnames` so clients can tell the server to import tool modules and register them. An analogous `llm_module_qualnames` for `RouterLLM` subclasses would work in principle — the container would import ext code and `DiscriminatedUnionMixin.__init_subclass__` would populate the subclass cache. But this requires adding a new field to `StartConversationRequest`, wiring server-side import logic in `conversation_service`, and ALSO still requires `LLM` to inherit the mixin so the discriminator exists in the first place. Strictly bigger surface than option 9 for no additional benefit; and it puts new API on the request protocol that we cannot upstream cleanly.

5. **`Annotated[LLM, SerializeAsAny()]` on Agent.llm** — Rejected. `SerializeAsAny` preserves runtime type on dump only; it does not affect deserialization. The dumped payload would include `RouterLLM` fields, but server-side `LLM.model_validate` still rebuilds a base `LLM` and drops them. Also requires modifying `Agent.llm` field annotation, i.e. still an SDK patch.

6. **Custom `model_dump`/`model_validate` override on `RouterLLM`** — Rejected. Same failure mode as option 2. Pydantic dispatches to the type on the field annotation. `LLM.model_validate` is what runs; `RouterLLM.model_validate` is never invoked for that field.

7. **Retype `Agent.llm` to `Annotated[Union[LLM, RouterLLM, CoderPlannerRouter], Discriminator("kind")]`** — Rejected. Requires editing `openhands/sdk/agent/agent.py` (a bigger patch than option 9), adding a `kind` field manually to each LLM class (or hard-coding the union), and enumerating all subclasses at annotation-write time. Doesn't scale to future LLM subclasses. Larger surface than a one-line mixin addition that gives the same discriminated-union semantics generically.

8. **Override `RemoteConversation` client-side to intercept the payload construction** — Rejected. This lives in `RemoteConversation.__init__:832` and would require our own `RemoteConversation` subclass. The transport layer would then need to re-tag the payload with a private discriminator, and the server would need matching logic to detect and rebuild — which it doesn't have. Leaks routing concerns into a transport layer, doesn't fix the general `LLM` polymorphism problem, and doesn't help `DelegateTool` when it eventually needs its own routing dispatch server-side.

9. **Skip `RemoteConversation` entirely, use `LocalConversation`** — Rejected. `LocalConversation` (`openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py:165`) runs the agent in-process on the client — no agent-server round-trip, so no serialization boundary. Would trivially work. BUT: ADR-0033 committed to the RemoteConversation architecture (via Canvas + agent-server, spec §2.4 requirement). Switching would invalidate Phase 2 and Phase 3.a-3.f (all already passed under agent-server), require redoing Canvas integration, and re-open the tool-execution/isolation model. Cost is far too high for the routing problem.

10. **Wait for upstream fix** — Rejected. GitHub search of `OpenHands/software-agent-sdk` for `RouterLLM`, `DiscriminatedUnion`, and `LLM.*polymorph` returns no open issue or PR addressing this. v1.42.0 (2026-08-04, latest release) has the LLM class line unchanged from v1.41.0 — bug not fixed. Closed PRs #1801 (LLMSerializationContext) and #311 (schema-first persistence, remove DU) went in different directions and were unmerged. Upstream direction is unclear and slow enough to block Phase 3 indefinitely.

**Selected: the Decision above (vendor openhands-sdk + 2-line patch to `LLM`)** because it is the minimum surface that satisfies the core constraint (`DiscriminatedUnionMixin` on the annotation type `LLM`) and is upstreamable as a clean PR after 3.j PASS. Options 4 and 7 would also satisfy the constraint but with strictly larger patches; options 1-3, 5-6, and 8 do not satisfy the constraint; options 9 and 10 are not on the critical-path timescale.

## Consequences

**Files created:**
- `vendor/openhands-sdk/` — vendored SDK source (git subtree at v1.41.0 commit).
- `adrs/ADR-0034-llm-discriminated-union-vendored-sdk-patch.md` — this file.
- `bench/smoke-phase-3-item-3j/README.md` — 3.j smoke README.
- `bench/smoke-phase-3-item-3j/run.sh` — 3.j smoke runner (Colossus).
- `bench/smoke-phase-3-item-3j/verify.py` — assertion harness (post-run).
- `tests/vendor/test_llm_discriminated_union.py` — round-trip contract test.

**Files modified:**
- `vendor/openhands-sdk/openhands-sdk/openhands/sdk/llm/llm.py` — `LLM` now inherits `DiscriminatedUnionMixin`.
- `pyproject.toml` — openhands-sdk dependency points at vendored editable install.
- `VERSIONS.lock` — annotate openhands-sdk row with `local:vendor/openhands-sdk/openhands-sdk (base: 1.41.0, commit: <SHA>)`.
- `PORTING_LEDGER.md` — new entry for openhands-sdk vendored patch.
- `docs/verification/verification-matrix.md` — 3.j row flips from ❌ to ✅ upon smoke PASS.
- `adrs/README.md` — new row for ADR-0034.
- `BUILD_LOG.md` — append entries for ADR draft, vendor pull, patch apply, smoke PASS (four separate entries, one per step).
- `DEBUG_LOG.md` — append root-cause diagnosis for the RouterLLM serialization loss (paired with the vendor + patch entry in BUILD_LOG).

**Procedures affected:**
- SDK upgrades: must re-apply the LLM discriminator patch and re-run 3.j smoke. Documented in this ADR's contingency (§9 above) and in `vendor/openhands-sdk/PATCHES.md` (per `kosmos-port-workflow` §4).
- Future LLM subclasses (e.g. a future `SubscriptionLLM`, `AzureLLM`): automatically discriminated. No further ADR needed unless the subclass introduces a new field the mixin can't handle.

**Downstream ADR impacts:**
- **ADR-0033** — Phase 2.4 config surface: unblocks the router path this ADR was authored around. No amendment needed; ADR-0033 already assumed the router would survive serialization.
- **ADR-0017** — Production role selection / co-residency: 3.h-2 (co-resident delegation) remains hardware-blocked (AWQ + Q6_K exceed 32 GiB), but 3.j landing means 3.i (joint role-switch, endpoint-swap) becomes achievable.
- **Deferred**: DockerWorkspace-based Forge-OH isolation ADR (unrelated to this fix; still deferred).

**Not affected:**
- `config/router.py::CoderPlannerRouter` — no code change.
- `config/agent.py::build_agent()` — no code change.
- Existing Phase 3.c/3.e/3.f/3.g smokes — orthogonal.

## Lock-in phase

Phase 3.j smoke PASS ratifies this ADR. Until then: `Proposed`.

## References

- `docs/specs/integration-execution-plan-v16.md` §2.4 (multi-LLM routing)
- `docs/verification/verification-matrix.md` row 3.j
- `adrs/ADR-0033-phase-2-4-config-surface-python-not-toml.md` (config-surface parent decision)
- `adrs/ADR-0017-production-role-selection-pre-medium.md` (co-residency contract; 3.h-2 hardware block)
- `openhands-sdk/openhands/sdk/utils/models.py` — `DiscriminatedUnionMixin` source
- `openhands-sdk/openhands/sdk/agent/base.py:1035` — `agent_kind` precedent
- Diagnosis session: current session (2026-08-11 21:24-21:31 EDT)
- Skill: `kosmos-port-workflow` (vendor + PORTING_LEDGER discipline)
- Skill: `kosmos-adr-authoring` (this ADR format)
