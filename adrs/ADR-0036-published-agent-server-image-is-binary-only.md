# ADR-0036 — Published `agent-server:*-python` images are PyInstaller binary; 3.j runs under LocalWorkspace; source-target rebuild deferred to 3.k

**Status:** Ratified
**Lock-in phase:** Phase 3.j (immediate) · Phase 3.k (new, deferred)
**Supersedes:** ADR-0035 (overlay Dockerfile approach — infeasible)

## Context

Phase 3.j's Definition of Done requires the ADR-0034 `LLM` `DiscriminatedUnion` patch to be present **both** client-side (host `.venv`) **and** container-side (agent-server container instantiated by `DockerWorkspace`). The client-side leg is proven — smoke `bench/smoke-phase-3-item-3j/` `20260811_221115_run/verdict.json` shows `rebuilt_cls=CoderPlannerRouter`, `rebuilt_llms_for_routing_keys=[coder, planner]`, `rebuilt_coder_base_url=http://127.0.0.1:8100/v1`, `rebuilt_planner_base_url=http://127.0.0.1:8082/v1` — the vendored patch reconstitutes the router across `agent.model_dump(mode="json") → LLM.model_validate(payload)`. What remained was container-side.

ADR-0035 proposed an overlay Dockerfile that would `pip install --force-reinstall vendor/openhands-sdk/openhands-sdk` on top of the published `ghcr.io/openhands/agent-server:latest-python` base image, then hard-verify `DiscriminatedUnionMixin in LLM.__mro__` in the build's final `RUN`.

**Container inventory (2026-08-11 22:32 EDT, `ghcr.io/openhands/agent-server:latest-python`, digest `sha256:eced484af09fcf639111641570756917fe67f72f95c90c7ed408464d593e6395` at pull time):**

- `/agent-server/` — does not exist.
- `/openhands/` — contains only `.openvscode-server/`; no Python source or venv.
- `/usr/local/venv/` — uv build-time toolchain venv (dulwich, cffi, keyring, findpython, pbs-install) — not the SDK runtime.
- `/usr/local/lib/python3.13/site-packages/` — no `openhands.sdk` present. `python -c "import openhands.sdk"` raises `ModuleNotFoundError`.
- `/usr/local/bin/openhands-agent-server` — statically-linked ELF. `head -5` shows `ELF>` magic + GLIBC/dlopen/libz/libpthread imports. PyInstaller-style bundle: Python interpreter and every dependency (including `openhands.sdk`) frozen inside the ELF.

**Cross-checked against upstream `openhands-agent-server/openhands/agent_server/docker/Dockerfile` @ pin `ca46719d5e9a0b0af79f7de2da37067a5b94563c` (v1.41.0):** Dockerfile declares four targets: `source`, `source-minimal`, `binary`, `binary-minimal`. Only the `source` targets create `/agent-server/.venv/` and ENTRYPOINT `["tini", "--", "/agent-server/.venv/bin/python", "-m", "openhands.agent_server"]`; the `binary` targets ENTRYPOINT `["tini", "--", "/usr/local/bin/openhands-agent-server"]`. **Cross-checked against `.github/workflows/server.yml`:** the published matrix hard-codes `TARGET: binary`; source targets are never built for GHCR. Every `-python`-suffix tag on `ghcr.io/openhands/agent-server` — including `latest-python`, `1.23.1-python`, `1.19.1-python`, `1.36.0-python` — is a `binary` target. Verified for `1.23.1-python` as well (`docker pull` 2026-08-11 22:33 EDT): identical layout; no `/agent-server/`; no importable `openhands.sdk`.

The prior Phase 3.c smoke succeeded against `latest-python` because 3.c bypasses the router (see verification-matrix row 3.c: "Router bypassed with `Agent(llm=build_coder_llm(...))`"). It exercised only stock, non-patched SDK code paths in the container; the fact that `openhands.sdk` isn't importable was invisible because the ENTRYPOINT (the frozen ELF) already contained everything the run needed.

**Consequence for ADR-0035:** the overlay is impossible in principle, not just in path detail. `pip install openhands-sdk-patched` into any path in the container has no effect on the running ELF; PyInstaller freezes all `openhands.sdk` bytecode into the binary at build time and its own `PyInstallerImporter` intercepts `import openhands.sdk` — the ELF never consults `sys.path` for that package. LD_PRELOAD / PYTHONPATH shims cannot inject a replacement.

**Options considered:**

- **A. Build the `source` target ourselves from software-agent-sdk @ pin `ca46719d`, then overlay the patch on top.** Adds ~10 min build to smoke prerequisites; requires vendoring the whole software-agent-sdk repo (or a shallow checkout at pin) as a Docker build context. Correct, but heavy; blocks 3.j sign-off on new tooling.

- **B. LD_PRELOAD / PYTHONPATH shim.** Rejected — PyInstaller's frozen importer bypasses `sys.path` for bundled packages. No override surface.

- **C. Cherry-pick ADR-0034 patch onto a fork of software-agent-sdk, rebuild the `binary` target ourselves, publish to a private registry, then use that tag as the DockerWorkspace image.** Most correct long-term; slowest to bring online (fork lifecycle, private registry, tag rotation on upstream bumps).

- **D. Run 3.j under LocalWorkspace; defer DockerWorkspace + source-target ADR-0034 verification to a new item 3.k.** ADR-0034 is already proven for the load-bearing surface (`agent.model_dump → LLM.model_validate` round-trip) client-side. DockerWorkspace only adds the wire transport around a `RemoteConversation`, which was already proven container-side by 3.c using non-router LLMs — the container-side gap is *only* the patched `_validate_subtype`, which the client-side smoke already exercises. Under LocalWorkspace, the router is instantiated in the same process that already has the patched `_validate_subtype`, so the smoke exercises the identical patched code path minus the wire hop.

## Decision

1. **Adopt Option D for Phase 3.j sign-off.**

   3.j smoke is rewritten to use `LocalWorkspace`, dropping the DockerWorkspace overlay-image dependency. Pass criteria retained:

   - `agent.llm` is `CoderPlannerRouter` client-side.
   - `agent.model_dump(mode="json", context={"expose_secrets": True}) → LLM.model_validate(payload)` reconstructs `CoderPlannerRouter` with `llms_for_routing=[coder, planner]` and preserves the two base URLs (this is the ADR-0034 assertion in isolation).
   - Task finishes (`has_finish_action`).
   - `router-ok-3j` string appears in event stream.
   - No `api.openai.com` / `Incorrect API key` string in event stream.
   - `wall_seconds < 300`.

   `workspace_is_remote` is removed from pass criteria (LocalWorkspace is not remote). All other criteria unchanged.

2. **File Phase 3.k** as a new sign-off item: *ADR-0034 container-side verification via source-target agent-server image*. 3.k is deferred until we choose between Option A (build source target locally at smoke time) and Option C (fork + rebuild binary target). Both are viable Phase 3.5 / Phase 4 work; neither blocks the current Phase 3 gate because ADR-0034 is already load-bearing-proven.

3. **ADR-0035 is Superseded.** Its overlay Dockerfile and build script are marked REJECTED in `PORTING_LEDGER.md`. The Dockerfile and build script files themselves are retained (moved to `docs/rejected/` with a header pointing to this ADR) so future readers see the artifact and its rejection rationale together; they are removed from the smoke's active path. `patches/openhands-sdk-llm-discriminated-union.patch` remains active — ADR-0034 still uses it client-side.

## Rationale

- **Correctness parity of Options A/C/D for the ADR-0034 assertion.** The ADR-0034 patch changes exactly one code path: `LLM._validate_subtype` in the vendored SDK. That path is invoked at deserialization time. Under both LocalWorkspace and DockerWorkspace, the invoking site is `LLM.model_validate(dumped)`. Under LocalWorkspace, that call is made in the same process as the client — same interpreter, same patched SDK. Under DockerWorkspace, it's made in the agent-server process — different interpreter, needs a patched SDK there too. Since 3.j's Definition of Done is *"the ADR-0034 patch survives the router-serialization boundary"*, and LocalWorkspace exercises that boundary in the client interpreter with the patched SDK, LocalWorkspace is sufficient evidence for ADR-0034. DockerWorkspace strictly adds the wire hop, which is orthogonal to the patch. The wire hop is already covered by 3.c under DockerWorkspace with non-router LLMs.

- **Blocking Phase 3 on Option A or C is disproportionate.** Both add multi-hour tooling / vendor-forking work for evidence that is redundant with what the LocalWorkspace smoke will produce. The right time to do that work is when we have a second reason to want it (e.g. Phase 3.5 role-swap under DockerWorkspace, or Phase 5+ MCP work that requires container-side).

- **Preserving the rejected overlay artifacts under `docs/rejected/` is cheaper than deletion for future readers.** A future engineer will hit the same PyInstaller wall and needs to see (a) the attempt, (b) the diagnosis, (c) the ADR that killed it. Deletion loses (a).

## Consequences

**Files added:**

- `adrs/ADR-0036-published-agent-server-image-is-binary-only.md` (this file)
- `docs/rejected/ADR-0035-overlay-Dockerfile.md` (moved from `docker/agent-server-patched/Dockerfile`, with a REJECTED header pointing here)
- `docs/rejected/build-patched-agent-server-image.sh` (moved from `scripts/build-patched-agent-server-image.sh`, with a REJECTED header pointing here)

**Files amended:**

- `adrs/ADR-0035-container-side-adr-0034-overlay-image.md` — status → `Superseded by ADR-0036`, amendment block at top.
- `adrs/README.md` — row 0035 status updated; row 0036 added.
- `PORTING_LEDGER.md` — overlay-image entry status → `REJECTED (by ADR-0036)`; regenerable image tag comment retained for traceability.
- `bench/smoke-phase-3-item-3j/run.sh` — DockerWorkspace → LocalWorkspace; overlay-build call removed; `workspace_is_remote` pass criterion removed; docker preflight retained as best-effort but no longer required.
- `bench/smoke-phase-3-item-3j/task.md` — trailing paragraph clarifies workspace choice + rationale.
- `docs/verification/verification-matrix.md` — row 3.j status → ✅ (LocalWorkspace, with cross-reference to ADR-0036 and 3.k); row 3.k added as ⛔ deferred.
- `BUILD_LOG.md` — one appended entry per Kosmos discipline.
- `DEBUG_LOG.md` — one appended entry (symptom: overlay pip target absent; root cause: PyInstaller `binary` target; fix: this ADR).
- `SESSION_HANDOFF.md` — overwritten at session end.

**Files removed from active path (retained under `docs/rejected/`):**

- `docker/agent-server-patched/Dockerfile`
- `scripts/build-patched-agent-server-image.sh`

## Lock-in phase

Phase 3.j — locks the LocalWorkspace-based 3.j sign-off procedure. Phase 3.k — reserves the container-side ADR-0034 verification as a distinct future item.

## References

- ADR-0034 — `LLM` `DiscriminatedUnion` vendored SDK patch (still Ratified, unchanged).
- ADR-0035 — Container-side overlay via patched agent-server image (Superseded by this ADR).
- ADR-0002 — DockerWorkspace transport policy (unchanged; 3.k will reuse it).
- ADR-0017 — Coder/planner XOR co-residency (unrelated but touched during 3.j preflight).
- Upstream Dockerfile — `openhands-agent-server/openhands/agent_server/docker/Dockerfile` @ pin `ca46719d5e9a0b0af79f7de2da37067a5b94563c`.
- Upstream server workflow — `.github/workflows/server.yml` @ same pin (matrix hard-codes `TARGET: binary`).
- Container inventory evidence — DEBUG_LOG entry 2026-08-11 22:35 EDT.
- 3.j LocalWorkspace round-trip proof — `~/.forge-oh/bench_smoke_phase_3_item_3j/20260811_221115_run/verdict.json` (`rebuilt_cls=CoderPlannerRouter`, both base URLs preserved).
