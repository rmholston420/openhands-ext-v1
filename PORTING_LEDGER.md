# PORTING_LEDGER.md — OpenHands-Ext v1

Every vendored/ported component logged here **before** first commit that touches it.
Statuses: `PLANNED` → `VENDORED` → (optionally) `SUPERSEDED` / `REJECTED`.

Per space custom instructions:
> Prefer vendoring a verified permissively-licensed OSS component over hand-building
> anything the spec or a fresh check identifies as already solved upstream — log every
> port with source URL, commit hash, SPDX license, and modification notes.

---

## Donor repositories (upstream metadata)

| Repo | URL | HEAD SHA at inventory | License |
|---|---|---|---|
| `rmholston420/oh-gui` | https://github.com/rmholston420/oh-gui | `ef3ac1a5c681e52835dda9fca43cad4ab1331d76` | MIT |
| `rmholston420/Forge-OH` | https://github.com/rmholston420/Forge-OH | `df73ebed2d6d9df9397f7e95dd1eb66bd3dd98b2` | MIT |

Both donors are owned by the same GitHub user (`rmholston420`) as this repo.

---

## Phase 3 — Runtime / SDK vendored patch

#### `openhands-sdk` (LLM discriminated-union patch) — VENDORED
- **Source:** https://github.com/OpenHands/software-agent-sdk
- **Commit / Version:** `ca46719d5e9a0b0af79f7de2da37067a5b94563c` (tag `v1.41.0`, released 2026-08-06T13:29:11Z)
- **License:** MIT (upstream `LICENSE` — permissive per Kosmos vendor rules)
- **Kosmos location:** `vendor/openhands-sdk/` (regenerable per ADR-0003; tree is gitignored, produced deterministically by `scripts/vendor-openhands-sdk.sh` from the pinned commit + tracked patch)
- **Port(s):** replaces the pip-installed `openhands-sdk==1.41.0` (from `scripts/install-oh-sdk.sh`) with an editable install of the same source plus the ADR-0034 patch. No new formal port — this is a same-package upgrade of an existing SDK dependency, not the introduction of a new adapter surface.
- **Modifications:**
  - `openhands-sdk/openhands/sdk/llm/llm.py`: add `from openhands.sdk.utils.models import DiscriminatedUnionMixin` import (line 118); change `class LLM(BaseModel, RetryMixin, NonNativeToolCallingMixin):` to `class LLM(DiscriminatedUnionMixin, RetryMixin, NonNativeToolCallingMixin):` (line 209). Two lines total. Full patch: `patches/openhands-sdk-llm-discriminated-union.patch`.
  - Rationale: makes `Agent.llm: LLM` container-side deserialization dispatch to the correct concrete subclass (e.g. `CoderPlannerRouter`) via `DiscriminatedUnionMixin._validate_subtype`, instead of flattening to base `LLM` and dropping `llms_for_routing`. Every other major SDK polymorphic type (`Tool`, `Event`, `Condenser`, `Workspace`, `Analyzer`, `Critic`, `Secret`, `Agent`, `MCPTool`) already inherits `DiscriminatedUnionMixin`; `LLM` was the only outlier. Upstreamable as a PR after Phase 3.j smoke PASS.
  - Regeneration: on Colossus, run `scripts/vendor-openhands-sdk.sh` — it re-clones the pinned commit, verifies the SHA, applies the patch, and pip-installs `-e vendor/openhands-sdk/openhands-sdk` into `.venv`. Records provenance to `bench/results/vendor-oh-sdk-<UTC-timestamp>.json`.
- **ADR:** ADR-0034 (Proposed until 3.j smoke PASS ratifies).
- **Logged:** 2026-08-11 21:45 EDT

#### `ghcr.io/openhands/agent-server:latest-python` (overlay for ADR-0034 patch) — VENDORED (image overlay)
- **Source (base image):** `ghcr.io/openhands/agent-server` — the `latest-python` tag matching upstream `openhands-agent-server` at pin `ca46719d5e9a0b0af79f7de2da37067a5b94563c` (v1.41.0)
- **License:** MIT (upstream `OpenHands/software-agent-sdk`)
- **Kosmos location:** `docker/agent-server-patched/Dockerfile` (recipe, tracked) + local Docker image `openhands-ext-v1/agent-server-patched:<sha256(patch)[:12]>` (regenerable per ADR-0003; not committed — rebuilt on Colossus by `scripts/build-patched-agent-server-image.sh`)
- **Port(s):** no new formal port. Same DockerWorkspace surface as ADR-0002; the overlay only replaces the container's pre-built `openhands-sdk` package inside `/agent-server/.venv` with the ADR-0034-patched vendor tree.
- **Modifications:**
  - COPY `vendor/openhands-sdk/openhands-sdk` → `/agent-server/openhands-sdk-patched`.
  - `pip install --no-deps --force-reinstall /agent-server/openhands-sdk-patched` inside the container's venv.
  - Final `RUN` asserts `DiscriminatedUnionMixin in LLM.__mro__` so a missing patch fails the build (not runtime).
  - Tag is content-addressed on `sha256(patch_file)[:12]`; any change to `patches/openhands-sdk-llm-discriminated-union.patch` produces a new tag and cannot silently reuse an unpatched cache.
- **ADR:** ADR-0035 (Proposed until 3.j smoke PASS ratifies).
- **Logged:** 2026-08-11 22:15 EDT

---

## Phase 5 — GPU Telemetry MCP Server

#### `gpu_monitor` — PLANNED
- **Source:** https://github.com/rmholston420/Forge-OH/blob/df73ebed/bff/services/gpu_monitor.py
- **Commit / Version:** `d870a7e38a1f8b33b931e3c719e957879b7fc2e6` (last commit touching this file)
- **License:** MIT (Forge-OH root LICENSE)
- **Kosmos location:** `mcp-servers/gpu-monitor/gpu_monitor.py` (planned)
- **Port(s):** `GPUTelemetryPort` (new MCP tool: `gpu_status`)
- **Modifications:** Per spec §Phase 5 — extend `gpu_status()` to report the process name/role (coder/planner/embedder) bound to the GPU, not just utilization/temperature. Wrap behind `supergateway` (§2.2). Adapter code, not just config, needed if llama.cpp wins any role.
- **ADR:** — (Phase 5 execution)
- **Logged:** 2026-08-10 23:24 EDT

---

## Phase 6 — Inference Backend Health + Episodic Memory MCP Servers

#### `inference_backends` — PLANNED
- **Source:** https://github.com/rmholston420/Forge-OH/tree/df73ebed/bff/services/inference_backends
- **Commit / Version:** `98763c6d019a0f09e5b7f2616577b2285cccbeb2` (registry.py; whole dir travels together)
- **License:** MIT
- **Kosmos location:** `mcp-servers/inference-backends/lib/` (planned)
- **Port(s):** `InferenceBackendHealthPort` (MCP tools: `list_backends`, `backend_health`)
- **Modifications:** Existing adapters are Ollama/vLLM/SGLang; if llama.cpp wins any role (per Phase 0.3 outcome), `inference_backends/registry.py` needs real adapter code changes, not just registry config (spec §Phase 6 warning). Embedding health-check must be runtime-agnostic. CPU-resident embedder must register as its own adapter entry distinct from GPU-resident.
- **ADR:** — (Phase 6 execution; likely triggers a new ADR when llama.cpp adapter is added)
- **Logged:** 2026-08-10 23:24 EDT

#### `episodic_memory` — PLANNED
- **Source:** https://github.com/rmholston420/Forge-OH/blob/df73ebed/bff/services/episodic_memory.py
- **Commit / Version:** `aa0dd5ea91a9efabc59efada3b16fd6ed5aa4cd5`
- **License:** MIT
- **Kosmos location:** `mcp-servers/episodic-memory/episodic_memory.py` (planned)
- **Port(s):** `EpisodicMemoryPort`
- **Modifications:** Wrap behind `supergateway`. Trajectory records from this service are also the real corpus for the Phase 0.2 embedder retrieval-quality evaluation.
- **ADR:** —
- **Logged:** 2026-08-10 23:24 EDT

#### `openhands_client` (BFF backend contract) — INSPECT-ONLY
- **Source:** https://github.com/rmholston420/Forge-OH/blob/df73ebed/bff/openhands_client.py
- **Commit / Version:** `aa0dd5ea91a9efabc59efada3b16fd6ed5aa4cd5`
- **License:** MIT
- **Kosmos location:** N/A (inspection only, per spec §Phase 4)
- **Port(s):** N/A
- **Modifications:** Per spec §Phase 4: inspect `base_url` / `httpx.AsyncClient` usage before registering BFF as a second Canvas backend. Do not port; use for compatibility assessment only.
- **ADR:** —
- **Logged:** 2026-08-10 23:24 EDT

#### `event_normalize` (contingency patch source) — CONDITIONAL
- **Source:** https://github.com/rmholston420/Forge-OH/blob/df73ebed/bff/services/event_normalize.py
- **Commit / Version:** `4c665f3dee9f4f979d2867b50317609ac791d9a2`
- **License:** MIT
- **Kosmos location:** patched in place at `~/Forge-OH/bff/services/event_normalize.py` if Phase 4 event-shape incompatibility appears
- **Port(s):** N/A
- **Modifications:** Per spec §Phase 4: if event stream doesn't render after switching active backend, patch to pass through native SDK event shapes unmodified. Only executed if the contingency fires.
- **ADR:** — (would trigger ADR if fired, per spec Risk Note "Phase 4's event-shape compatibility is the highest technical risk")
- **Logged:** 2026-08-10 23:24 EDT

---

## Phase 7 — RepoGraph (Neo4j + MCP + Canvas Panel)

#### `repograph/index.py` — PLANNED
- **Source:** https://github.com/rmholston420/Forge-OH/blob/df73ebed/openhands_tools_ext/repograph/index.py
- **Commit / Version:** `242a0422186e6c805bf776f7ae856eed34360680`
- **License:** MIT
- **Kosmos location:** `mcp-servers/repograph/lib/index.py` (planned)
- **Port(s):** `RepoGraphIndexerPort` (MCP tool for triggering/updating index)
- **Modifications:** Wrap behind `supergateway`. Must fail safely on malformed repos (Phase 7 Verification).
- **ADR:** — (Phase 7 is the largest net-new engineering effort per spec; likely spawns multiple ADRs)
- **Logged:** 2026-08-10 23:24 EDT

#### `repograph/parser.py` — PLANNED
- **Source:** https://github.com/rmholston420/Forge-OH/blob/df73ebed/openhands_tools_ext/repograph/parser.py
- **Commit / Version:** `bdb8090f075b34eeb010833ab805b30725f26425`
- **License:** MIT
- **Kosmos location:** `mcp-servers/repograph/lib/parser.py` (planned)
- **Port(s):** internal to `RepoGraphIndexerPort`
- **Modifications:** —
- **ADR:** —
- **Logged:** 2026-08-10 23:24 EDT

#### `repograph/store.py` (Neo4j backend) — PLANNED
- **Source:** https://github.com/rmholston420/Forge-OH/blob/df73ebed/openhands_tools_ext/repograph/store.py
- **Commit / Version:** `924f3240a106868c75ec6f141054a54a4249fdc0`
- **License:** MIT
- **Kosmos location:** `mcp-servers/repograph/lib/store.py` (planned)
- **Port(s):** `RepoGraphStorePort` (Bolt protocol client)
- **Modifications:** Neo4j runs as independent infrastructure; Canvas panel connects via Bolt directly (spec §Phase 7).
- **ADR:** —
- **Logged:** 2026-08-10 23:24 EDT

---

## Phase 8 — Security Analyzer (Blast Radius)

#### `oh-gui/apps/gui/src/features/authorization/blast-radius.ts` — PLANNED (logic port, not code port)
- **Source:** https://github.com/rmholston420/oh-gui/blob/ef3ac1a5/apps/gui/src/features/authorization/blast-radius.ts
- **Commit / Version:** `bab46c91ffa8c0f1283a5a5b02d9834f34a4288b`
- **License:** MIT
- **Kosmos location:** `security/blast-radius/blast_radius.py` (Python rewrite, planned)
- **Port(s):** subclass of `openhands.sdk.security.SecurityAnalyzerBase`, layered on `LLMSecurityAnalyzer`
- **Modifications:** Per spec §Phase 8 — port the blast-radius **projection logic** only. OH-GUI's TypeScript `AuthorizationCard`/`BlastRadiusSection` UI components are **superseded**, not ported (Canvas's native confirmation UI replaces them). Preserve the four-outcome invariant against the documented mangled-class-name lookup bug (per spec Risk Note). Companion test file `blast-radius.test.ts` (same commit) is the reference for the four-outcome contract.
- **ADR:** — (Phase 8 execution)
- **Logged:** 2026-08-10 23:24 EDT

#### OH-GUI frontend components — REJECTED (native replacement)
- **Source:** `oh-gui/apps/gui/src/features/authorization/{AuthorizationCard,BlastRadiusSection,AgentAccountSection}.tsx`
- **Commit / Version:** various on `ef3ac1a5`
- **License:** MIT
- **Kosmos location:** N/A — **not ported**
- **Port(s):** N/A
- **Modifications:** N/A. Per spec Definition of Done: "No custom frontend code from either source repo ships in the final system." OH-GUI's frontend is replaced entirely by stock Agent Canvas.
- **ADR:** ADR-0001 (rationale for not forking OH-GUI at repo level)
- **Logged:** 2026-08-10 23:24 EDT

---

## Phase 11 — Decommission

Forge-OH `bff/routers/*.py` and Socket.IO relay are `PLANNED-DECOMMISSION` once every
router has a confirmed native-tool / hook / MCP / panel equivalent from Phases 5-10.
Archived to `~/dev/archived-frontends/` per spec §Phase 11, not deleted, for one
release cycle.

---

## Ledger conventions

- Every entry names its exact upstream URL, per-file commit SHA (not just the repo HEAD),
  and SPDX license.
- `PLANNED` = target identified, not yet vendored. `VENDORED` = code copied into this
  repo. `SUPERSEDED` = replaced by a later entry (link the successor). `REJECTED` = we
  chose native replacement over porting (link the ADR).
- New adoptions require an ADR only if load-bearing (adds/changes a port, storage
  backend, or plugin boundary) — routine copy-and-wrap ports do not need an ADR.
