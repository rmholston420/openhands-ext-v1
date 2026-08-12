# ADR-0035 — Container-side ADR-0034 patch via overlay agent-server image (Phase 3.j RouterLLM survival across container boundary)

> **STATUS AMENDMENT (2026-08-11 22:40 EDT):** Superseded by ADR-0036. The overlay approach is infeasible because the published `ghcr.io/openhands/agent-server:*-python` tags are built with `TARGET: binary` (PyInstaller ELF, frozen `openhands.sdk` bytecode; no `/agent-server/.venv/`; no importable `openhands.sdk` in any site-packages). No `pip`/`uv pip`/`LD_PRELOAD`/`PYTHONPATH` overlay can replace bytecode frozen in the ELF. See ADR-0036 for the container-inventory evidence, the four options considered (A/B/C/D), and the Option D decision. Original decision text below is preserved verbatim.

**Status:** Superseded by ADR-0036
**Lock-in phase:** Phase 3.j
**Supersedes:** —
**Related:** ADR-0002 (DockerWorkspace policy), ADR-0003 (repo/colossus mirror discipline; `vendor/` is category-2 regenerable), ADR-0034 (client-side SDK patch), ADR-0036 (supersession)

## Context

ADR-0034 vendors `openhands-sdk` at pin `ca46719d5e9a0b0af79f7de2da37067a5b94563c` (v1.41.0) and applies a `DiscriminatedUnionMixin` patch on `LLM` so that `Agent.llm: LLM` deserialization dispatches to the concrete subclass (`CoderPlannerRouter`) instead of flattening to base `LLM` and losing `llms_for_routing`.

The 3.j smoke run at `~/.forge-oh/bench_smoke_phase_3_item_3j/20260811_221115_run/verdict.json` empirically split the boundary:

- **Client-side round-trip PASSED.** In-harness `LLM.model_validate(agent.model_dump(...)["llm"])` reconstructed `CoderPlannerRouter` with `llms_for_routing = {"coder", "planner"}` and both nested `base_url`/`model` values intact.
- **Container-side deserialization STILL FAILED.** `RemoteConversation.run()` raised `LLMAuthenticationError: OpenAIException — Incorrect API key provided: local. You can find your API key at https://platform.openai.com/account/api-keys.` The container-side agent flattened the router back to base `LLM`, dropped `llms_for_routing`, dropped the vLLM `base_url=http://127.0.0.1:8100/v1`, and litellm defaulted to `api.openai.com`.

Root cause: the `agent-server` container image (`ghcr.io/openhands/agent-server:latest-python` at the pin) ships upstream unpatched `openhands-sdk` in its self-contained `/agent-server/.venv`. Our vendor-tree patch lives only in the host repo's `.venv`. The RemoteConversation model_dump/model_validate round-trip crosses the container boundary; both endpoints must run the patched SDK for the discriminated-union dispatch to survive.

## Decision

Build a **thin overlay image** locally on Colossus that starts from `ghcr.io/openhands/agent-server:latest-python` at the ADR-0034 pin and force-reinstalls our patched vendor SDK on top of the container's pre-built venv. The 3.j smoke (and any future phase that hits the RemoteConversation boundary while using a `RouterLLM` subclass) sets `DockerWorkspace(server_image=<overlay-tag>)` instead of the upstream tag.

Concretely:

1. New file `docker/agent-server-patched/Dockerfile`:

   ```dockerfile
   # syntax=docker/dockerfile:1.7
   ARG BASE_IMAGE=ghcr.io/openhands/agent-server:latest-python
   FROM ${BASE_IMAGE}
   USER root
   # Overlay patched openhands-sdk on top of the pre-built container venv.
   # Vendor tree is category-2 regenerable (ADR-0003) — regenerated via
   # scripts/vendor-openhands-sdk.sh before every image build.
   COPY --chown=openhands:openhands vendor/openhands-sdk/openhands-sdk /agent-server/openhands-sdk-patched
   RUN /agent-server/.venv/bin/pip install --no-deps --force-reinstall --disable-pip-version-check \
       /agent-server/openhands-sdk-patched \
    && /agent-server/.venv/bin/python -c "from openhands.sdk.utils.models import DiscriminatedUnionMixin; from openhands.sdk.llm.llm import LLM; assert DiscriminatedUnionMixin in LLM.__mro__, 'ADR-0034 patch missing in container'" \
    && echo "ADR-0034 patch verified in container SDK"
   USER openhands
   ```

2. New file `scripts/build-patched-agent-server-image.sh`:

   Content-addressed tag derived from `sha256(patch_file)[:12]`, e.g.
   `openhands-ext-v1/agent-server-patched:<sha-12>`. Idempotent: skips
   the build if the tag already exists locally. Emits the resolved tag
   on stdout so `run.sh` can capture it.

3. The 3.j smoke `bench/smoke-phase-3-item-3j/run.sh` calls the build
   script and passes the resolved tag as `server_image` to
   `DockerWorkspace`.

4. `PORTING_LEDGER.md` records the base image, the patch anchor, and the build script as an OSS overlay (not a re-port of the SDK — the SDK port is already logged for ADR-0034).

### Alternatives considered

- **Volume-mount the patched vendor tree over the container's site-packages.** Fragile: depends on the container's exact venv layout (`/agent-server/.venv/lib/python3.13/site-packages/openhands/sdk`), silently breaks on any upstream image reorganization, and violates the project's "never assume" discipline.
- **Use `DockerDevWorkspace`.** Requires vendoring the entire agent-server, openhands-tools, and openhands-workspace source trees plus the pyinstaller/uv build pipeline just to solve a 35-line patch. Heavy vendor footprint, larger surface for future upstream drift.

## Rationale

- **Minimal, reproducible.** The overlay is a two-instruction Dockerfile plus one build script; the base image layers are cached, so incremental rebuilds are cheap.
- **Content-addressable.** The tag is derived from the patch hash. Any change to `patches/openhands-sdk-llm-discriminated-union.patch` produces a new tag, so stale caches cannot silently serve unpatched behavior.
- **Self-verifying.** The Dockerfile's final `RUN` line imports `LLM` and asserts `DiscriminatedUnionMixin in LLM.__mro__`. A missing or broken patch fails the build, not runtime.
- **ADR-0003 aligned.** `vendor/` is category-2 regenerable; the image is category-2 regenerable in the same way — regenerable-by-script, not committed.
- **ADR-0017 unaffected.** Overlay adds no VRAM footprint; the container still runs the same agent-server binary.
- **Local-first, single-user.** Built and used on Colossus. No registry push. No cloud plane.

## Consequences

New / changed:

- `docker/agent-server-patched/Dockerfile` (new; two instructions plus verification)
- `scripts/build-patched-agent-server-image.sh` (new; content-addressed tag, idempotent)
- `bench/smoke-phase-3-item-3j/run.sh` (call build script, use resolved tag)
- `PORTING_LEDGER.md` (append overlay-image entry)
- `BUILD_LOG.md` (append entry)
- `DEBUG_LOG.md` (append entry: symptom = `Incorrect API key: local`, root cause = container-side unpatched SDK)
- `adrs/README.md` (add row 0035)

Runtime cost: first build ≈ 30-60 s once base image is pulled; incremental rebuilds ≈ 5-10 s.

Disk cost: one additional image layer (~20 MB, single Python package overlay).

The overlay tag is **required** for any current or future benchmark that uses `RemoteConversation` with a `RouterLLM` subclass or any `DiscriminatedUnion`-backed nested LLM. Any bench that reverts to `server_image=ghcr.io/openhands/agent-server:latest-python` will re-exhibit the flattening bug and must be flagged in review.

## Lock-in phase

Phase 3.j. This ADR is a direct consequence of the 3.j smoke's container-side failure and locks in with 3.j sign-off.

## References

- `patches/openhands-sdk-llm-discriminated-union.patch`
- `scripts/vendor-openhands-sdk.sh`
- `adrs/ADR-0002-*.md` (DockerWorkspace-only workspace policy)
- `adrs/ADR-0003-*.md` (repo/colossus mirror discipline, category-2 regenerable)
- `adrs/ADR-0034-llm-discriminated-union-vendored-sdk-patch.md`
- 3.j smoke verdict evidence: `~/.forge-oh/bench_smoke_phase_3_item_3j/20260811_221115_run/verdict.json`
- Upstream Dockerfile at pin: `openhands-agent-server/openhands/agent_server/docker/Dockerfile` @ `ca46719d5e9a0b0af79f7de2da37067a5b94563c`
