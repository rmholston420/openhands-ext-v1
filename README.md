# OpenHands-Ext v1

OpenHands extended and optimized for **Colossus** (128GB RAM, RTX 5090 32GB VRAM,
Blackwell SM_120, Kubuntu). Single-user, local-first. No cloud control planes. No
multi-user assumptions. No GitHub-native CI beyond what already exists in the source
repos.

## Layout

| Path | Purpose |
|---|---|
| [`docs/specs/`](docs/specs/) | Authoritative execution plan (v16, standalone) |
| [`docs/donor-inventory.md`](docs/donor-inventory.md) | Snapshot of OH-GUI + Forge-OH donor repos at bootstrap |
| [`adrs/`](adrs/) | Architecture Decision Records |
| [`PORTING_LEDGER.md`](PORTING_LEDGER.md) | Every ported component with source URL + commit SHA + SPDX license |
| [`VERSIONS.lock`](VERSIONS.lock) | Live-fetched upstream version baseline (freshness reference; Colossus re-fetches at Phase -1) |
| [`BUILD_LOG.md`](BUILD_LOG.md) | Append-only build log |
| [`DEBUG_LOG.md`](DEBUG_LOG.md) | Append-only debug log (search first before diagnosing) |
| [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) | Open unresolved issues |
| [`SESSION_HANDOFF.md`](SESSION_HANDOFF.md) | Current session state (overwritten each session end) |
| `hooks/pre-commit/` | Local pre-commit hooks (ADR-0002) |
| `scripts/` | Installer + utility scripts |
| `bench/` | Benchmark harness (Phase 0 tiers) |
| `mcp-servers/` | Ported MCP servers (Phases 5-7) |
| `security/blast-radius/` | Phase 8 native SecurityAnalyzerBase subclass |
| `canvas-panel/repograph/` | Phase 7 Canvas plugin panel (neovis.js + Bolt) |
| `config/` | Populated **only** from Phase 0.3 Full-tier winners |

## Bootstrap on Colossus

```bash
mkdir -p ~/dev && cd ~/dev
gh repo clone rmholston420/openhands-ext-v1
cd openhands-ext-v1
bash scripts/install-hooks.sh
cat SESSION_HANDOFF.md
cat docs/specs/integration-execution-plan-v16.md | less
```

Then execute Phase -1 per spec §-1.4 / §-1.5. Do **not** carry the numbers in
`VERSIONS.lock` forward — that file is a freshness reference; Colossus re-fetches.

## Status

**Pre-Phase -1 (author-side setup complete).** See `SESSION_HANDOFF.md` for the exact
next action.
