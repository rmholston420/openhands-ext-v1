# ADR Index — OpenHands-Ext v1

Architecture Decision Records for load-bearing decisions in this project. One file per
decision, filed at `adrs/ADR-####-kebab-case-title.md`. Statuses: `Proposed`, `Ratified`,
`Amended`, `Superseded by ADR-####`, `OPEN`.

Filing procedure: see space skill `kosmos-adr-authoring` (loaded).

| # | Title | Status | Lock-in phase |
|---|---|---|---|
| 0001 | [Repo bootstrap: fresh private repo, not fork](ADR-0001-repo-bootstrap.md) | Ratified | Pre-Phase -1 |
| 0002 | [LocalWorkspace guard = pre-commit hook, not GitHub Actions](ADR-0002-localworkspace-guard-pre-commit.md) | Ratified | Phase 1 |
| 0003 | [Repo / Colossus mirror discipline](ADR-0003-repo-colossus-mirror-discipline.md) | Amended (2026-08-11) | Pre-Phase -1 |
| 0004 | [llama.cpp CUDA toolchain pin: CUDA 13.0 + gcc-13 + SM_120](ADR-0004-llama-cpp-cuda-13-pin.md) | Amended (2026-08-11) | Phase -1 |
| 0005 | [flashinfer Blackwell (SM_120) workaround via VLLM_USE_FLASHINFER_SAMPLER=0](ADR-0005-flashinfer-blackwell-workaround.md) | Ratified (reinstated 2026-08-11 02:26 EDT for sampler path) | Phase -1 / Phase 0.1 |
| 0006 | [flashinfer SM_120 support via flashinfer-jit-cache==0.6.16.post3+cu129](ADR-0006-flashinfer-jit-cache-cu129.md) | Ratified · Amended (attention only; sampler deferred to ADR-0005) | Phase -1 / Phase 0 prereq |
| 0007 | [Fast-tier task authoring, sampling, and elimination-rubric methodology](ADR-0007-fast-tier-task-methodology.md) | Ratified | Phase 0.1 |
| 0008 | [Fast tier disables thinking mode for planner (opt-in for coder)](ADR-0008-fast-tier-thinking-disabled.md) | Ratified | Phase 0.1 |
| 0009 | [Fast-tier planner uses guided decoding (response_format=json_schema)](ADR-0009-fast-tier-guided-decoding.md) | Ratified | Phase 0.1 |
| 0010 | [Fast-tier vLLM per-role launch flags](ADR-0010-fast-tier-vllm-role-flags.md) | Amended · see ADR-0011 | Phase 0.1 |
| 0011 | [Fast-tier coder tool-call parser = hermes (default, per-cell override)](ADR-0011-fast-tier-coder-tool-call-parser-hermes.md) | Ratified v25 2026-08-11 · AMENDMENT 3 partially reversed by ADR-0014 | Phase 0.1 |
| 0012 | [Registry amendment: 30B thinker is dual-role coder+planner](ADR-0012-registry-dual-role-30b-thinker.md) | Ratified | Phase 0.1 |
| 0013 | [Registry exclusion: Qwen3.5-VL multimodal not coder-pool](ADR-0013-registry-exclude-qwen3_5-multimodal-from-coder.md) | Ratified | Phase 0.1 |
| 0014 | [Coder-fast pool reinstates R2-warning survivors after harness rubric-compliance fix](ADR-0014-coder-fast-pool-reinstate-r2-warning-survivors.md) | Ratified | Phase 0.1 |
| 0015 | [Planner Medium-tier thinker-2507-awq budget-hypothesis probe (pre-registered)](ADR-0015-planner-medium-thinker-budget-probe.md) | Ratified · Confirmed (2026-08-11) — thinker unfit for planner Medium pool | Phase 0.2 |
| 0016 | [Medium-tier scoring rubric: hybrid (embedder programmatic; planner/coder Perplexity-gold)](ADR-0016-medium-tier-scoring-rubric-hybrid.md) | Ratified | Phase 0.2 |
| 0017 | [Production role selection (pre-Medium-tier): coder=qwen3-coder-30B-instruct-awq, planner=qwen3.6-35B-A3B-Q4_K_XL, embedder=qwen3-embedding-4B-Q8_0; co-residency Option 2](ADR-0017-production-role-selection-pre-medium.md) | Ratified v25 · Amended ×3 · Planner row superseded by ADR-0023 | Phase 0.2 → Phase 1 handoff |
| 0018 | [Phase −1 version pins (drift-tolerant baseline)](ADR-0018-phase-minus-1-version-pins.md) | Ratified | Phase −1 |
| 0019 | [Phase 2 MCP port range, mode wrapper, skills convention](ADR-0019-phase-2-mcp-port-range-and-mode-wrapper.md) | Ratified | Phase 2 |
| 0020 | [UFW bridge egress for sandbox healthcheck](ADR-0020-ufw-bridge-egress-for-sandbox-healthcheck.md) | Ratified | Phase 1 |
| 0021 | [Live UI Playwright smoke test](ADR-0021-live-ui-playwright-smoke.md) | Ratified | Phase 1 |
| 0022 | [Phase 0.2 coder + planner Medium-tier task-set, gold-reference, and co-residency protocol](ADR-0022-phase-0-2-coder-planner-medium-task-and-gold-protocol.md) | Ratified | Phase 0.2 |
| 0023 | [Phase 0.3 router-selection: post-Medium production role update (planner flips 35B-a3b-q4kxl → 27B-q6k on quality-first)](ADR-0023-phase-0-3-router-selection-post-medium.md) | Ratified | Phase 0.3 gate-1 |
| 0024 | [Planner migration-ordering probe (Phase 0.3 pre-registered re-eval): 4-task probe + pre-registered reversal criteria for ADR-0023 planner ordering](ADR-0024-planner-migration-ordering-probe.md) | Ratified | Phase 0.3 gate-1 |
| 0025 | [Planner migration-ordering probe verdict: CONFIRM ADR-0023 (27b-q6k retained; 91.75 vs 86.50 macro-avg; 27b leads by 5.25 pts, outside 3-pt tiebreak)](ADR-0025-planner-migration-probe-verdict-confirm-adr-0023.md) | Ratified | Phase 0.3 gate-1 |
| 0026 | [Coder multi-turn correctness harness v1 (DockerWorkspace SDK path + Perplexity-Max scored 0-100 + supersede Phase 0.2 medium coder verdict)](ADR-0026-coder-multi-turn-correctness-harness-v1.md) | Amended (amend 3: transport + tools + scoping + trace schema v1.1) | Phase 0.3 gate-2 |
| 0027 | [Phase 0.3 gate-2 coder verdict: CONFIRM AWQ (qwen3-coder-30b-a3b-instruct-awq-4bit); 85.4 vs 88.7 macro-avg, 35b fails T05/T08 finish-action; reversal-criteria rule 3 fired robust to strict/loose <70 reading)](ADR-0027-phase-0-3-gate-2-coder-verdict-confirm-awq.md) | Ratified | Phase 0.3 gate-2 |
| 0028 | [Phase 0.3 gate-3 coder Full-tier re-eval (AWQ vs 35b, pre-registered; 10-task Full multi-turn set with 3 report-style tasks; finish-action clause in reversal criteria)](ADR-0028-phase-0-3-gate-3-coder-full-tier-re-eval.md) | Ratified (amended 2026-08-11 12:17 EDT: F05 class swap for runner constraint) | Phase 0.3 gate-3 |
| 0029 | [Phase 0.3 gate-3 coder verdict: CONFIRM AWQ (Full-tier re-eval; AWQ macro 88.1 vs 35b 66.0; 35b omitted FinishAction on all 3 report-style tasks; 3 independent reversal-criterion clauses fired)](ADR-0029-phase-0-3-gate-3-coder-verdict-confirm-awq.md) | Ratified | Phase 0.3 gate-3 |
| 0030 | [Phase 0.4 embedder Full-tier re-eval opener (three-way: 4B-Q8 incumbent vs 8B-Q6_K vs 0.6B-Q8; all llama.cpp GPU cold; 2 blocks × 2 chunkers × 3 candidates = 12 cells; 40 queries; V3+W3 reversal criteria pre-locked; amended 2026-08-11 to restore scope + switch placement CPU→GPU)](ADR-0030-phase-0-4-embedder-full-tier-re-eval.md) | Proposed (Ratifies on fixture lock-in) | Phase 0.4 gate-4 |
| 0030b | [Embedder co-residency viability under coder XOR planner (methodology + verdict criteria for ADR-0030 quality winners; VRAM math + contention protocol + startup swap cost)](ADR-0030b-embedder-co-residency-viability.md) | Proposed · deferred (execution conditional on future full re-eval per ADR-0031) | Phase 0.4 gate-4 |
| 0031 | [Phase 0.4 gate-4 embedder verdict: DEFER (accept 4-query calibration, retain 4B-Q8 incumbent; N=4 below rubric N=20/block threshold; step-6b pool + calibration qrels persist for future re-eval)](ADR-0031-phase-0-4-embedder-verdict-defer.md) | Ratified | Phase 0.4 gate-4 |
| 0032 | [Phase 1 spec-scope closure: 1.1 DockerWorkspace-only policy CLOSED (hook clean full-tree); 1.2 code-explorer registration DEFERRED to §2.4/Phase 3 where the runtime tool registry actually gets scaffolded; docs/BENCHMARK_UNPAUSE_GATES.md added to hook allow-list](ADR-0032-phase-1-spec-scope-closure-and-1-2-defer.md) | Ratified | Phase 1 |
| 0033 | [Phase 2.4 config surface: Python module `config/agent.py`, not TOML (SDK 1.41 has no TOML loader; `RouterLLM` is Pydantic; option 6c = LLMCallContext metadata dispatch; option 7a = coder-as-condenser)](ADR-0033-phase-2-4-config-surface-python-not-toml.md) | Ratified | Phase 2.4 · Phase 3 |
| 0034 | [Vendor openhands-sdk to patch `LLM` for `DiscriminatedUnion` serialization (Phase 3.j: RouterLLM subclass survives RemoteConversation boundary)](ADR-0034-llm-discriminated-union-vendored-sdk-patch.md) | Ratified | Phase 3.j |
| 0035 | [Container-side ADR-0034 patch via overlay agent-server image (Phase 3.j: patch must live in both host venv and DockerWorkspace container)](ADR-0035-container-side-adr-0034-overlay-image.md) | Superseded by ADR-0036 | Phase 3.j |
| 0036 | [Published `agent-server:*-python` images are PyInstaller binary; 3.j runs under LocalWorkspace; source-target rebuild deferred to 3.k](ADR-0036-published-agent-server-image-is-binary-only.md) | Ratified | Phase 3.j · Phase 3.k |

Not yet filed (deferred to their lock-in phase; numbers reserved but not committed — renumber at filing time):

- llama.cpp adapter for `inference_backends/registry.py` (fires only if llama.cpp wins any role at Phase 0.3)
- Neo4j deployment topology for RepoGraph (Phase 7)
- Cross-plugin coupling policy inside `mcp-servers/*` (Phase 5/6 boundary)
- `select_model` dynamic-switching MCP tool inclusion decision (Phase 10, fires only if Full-tier produces multi-model split)
