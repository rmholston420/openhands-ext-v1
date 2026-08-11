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
| 0017 | [Production role selection (pre-Medium-tier): coder=qwen3-coder-30B-instruct-awq, planner=qwen3.6-35B-A3B-Q4_K_XL, embedder=qwen3-embedding-4B-Q8_0; co-residency Option 2](ADR-0017-production-role-selection-pre-medium.md) | Ratified v25 · Amended ×3 (pre-Phase-0.3) | Phase 0.2 → Phase 1 handoff |
| 0018 | [Phase −1 version pins (drift-tolerant baseline)](ADR-0018-phase-minus-1-version-pins.md) | Ratified | Phase −1 |
| 0019 | [Phase 2 MCP port range, mode wrapper, skills convention](ADR-0019-phase-2-mcp-port-range-and-mode-wrapper.md) | Ratified | Phase 2 |
| 0020 | [UFW bridge egress for sandbox healthcheck](ADR-0020-ufw-bridge-egress-for-sandbox-healthcheck.md) | Ratified | Phase 1 |

Not yet filed (deferred to their lock-in phase; numbers reserved but not committed — renumber at filing time):

- llama.cpp adapter for `inference_backends/registry.py` (fires only if llama.cpp wins any role at Phase 0.3)
- Neo4j deployment topology for RepoGraph (Phase 7)
- Cross-plugin coupling policy inside `mcp-servers/*` (Phase 5/6 boundary)
- `select_model` dynamic-switching MCP tool inclusion decision (Phase 10, fires only if Full-tier produces multi-model split)
