# OpenHands-Ext v1 · Session Handoff — 2026-08-11 07:19 EDT

## Current build-sequencing position
- **Stage / phase:** Phase −1 COMPLETE; Phase 2.1, 2.2, 2.3 COMPLETE (docs + wrappers). Phase 1 (DockerWorkspace-only) was completed earlier this session cluster.
- **Plugin / kernel component:** none in flight.
- **Port(s) in progress:** none.

## Completed this session
- Phase −1 verification (all 6 rows PASS, ADR-0018 filed, drift-tolerant baseline).
- Phase 2.1: `scripts/openhands-mode.sh` (tui/serve/headless dispatcher with --acknowledge-low-risk gate).
- Phase 2.2: `scripts/mcp-supergateway.sh` (template) + `docs/MCP_PORT_ALLOCATION.md` (8110–8199 reserved).
- Phase 2.3: `.agents/skills/` repo-local skills directory with README + retirement rules.
- ADR-0019 filed (D1 acknowledgment gate · D2 port range · D3 skills split).
- Both new scripts syntax-checked (`bash -n`) and executable.

## Remaining before current Definition of Done
- Phase 2.1/2.2/2.3 DoD: MET.
- Phase 2.4: DO NOT TOUCH — populated only after Phase 0.3 concludes with winning model/endpoint per role.
- Phase 2.5: deferred to Phase 3+.

## Open questions / awaiting user answer
- None from this session.
- Pending Colossus verification (informational; not blocking):
  - Is `openhands` CLI installed? Is `supergateway` on PATH? Docker daemon reachable? — see the emitted Colossus check block. Wrappers fail-loud in either case, so this is not a gate.
- Recorded in KNOWN_ISSUES.md (unchanged this session):
  - llama.cpp b10356 → b10359 drift
  - vLLM 0.27.0 → 0.27.1 drift
  - CUDA 12.8 → 12.9 upgrade path
  - 4B-CPU vs 0.6B-GPU embedder benchmark

## Exact next action
Phase 3 (Baseline Verification) is spec-gated: it runs only AFTER Phase 0.3 concludes and Phase 2.4 is populated. Do not start Phase 3 until Phase 0.3 winners are known and §2.4 config is filled.

Interim options if you want work moving:
1. Phase 0.3 (Full-tier combination test) — requires the Path D benchmark harness to run over the full role×model×quant matrix on Colossus. This is the natural sequencer.
2. Optional Phase 2 hardening (not required by spec): add a `--dry-run` mode to `scripts/openhands-mode.sh` that prints the resolved command without executing.

Before starting either, restate scope and flag any ambiguity for confirmation.
