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
| 0005 | [flashinfer Blackwell (SM_120) workaround via VLLM_USE_FLASHINFER_SAMPLER=0](ADR-0005-flashinfer-blackwell-workaround.md) | Amended (2026-08-11) · superseded by ADR-0006 | Phase -1 |
| 0006 | [flashinfer SM_120 support via flashinfer-jit-cache==0.6.16.post3+cu129](ADR-0006-flashinfer-jit-cache-cu129.md) | Ratified | Phase -1 / Phase 0 prereq |

Not yet filed (deferred to their lock-in phase; numbers reserved but not committed — renumber at filing time):

- llama.cpp adapter for `inference_backends/registry.py` (fires only if llama.cpp wins any role at Phase 0.3)
- Neo4j deployment topology for RepoGraph (Phase 7)
- Cross-plugin coupling policy inside `mcp-servers/*` (Phase 5/6 boundary)
- `select_model` dynamic-switching MCP tool inclusion decision (Phase 10, fires only if Full-tier produces multi-model split)
