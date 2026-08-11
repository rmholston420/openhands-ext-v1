# ADR-0001 — Repo Bootstrap: Fresh Private Repo, Not Fork

**Status:** Ratified
**Lock-in phase:** Pre-Phase -1
**Supersedes:** —

## Context

The v16 execution plan integrates capabilities from two donor repos owned by the same
user (`rmholston420/oh-gui`, `rmholston420/Forge-OH`) into a **stock, unforked** Agent
Canvas UI. The Definition of Done in the spec states:

> No custom frontend code from either source repo ships in the final system; the one new
> frontend surface (a RepoGraph panel) is purpose-built against Canvas's plugin API.

The question at bootstrap: where does the new integration code live?

## Decision

Bootstrap a **fresh, private, MIT-licensed GitHub repo** at `rmholston420/openhands-ext-v1`.
Vendor from OH-GUI and Forge-OH file-by-file into structured subdirectories
(`mcp-servers/`, `security/`, `canvas-panel/`) per the v16 spec's phase-by-phase port
plan, with each port logged in `PORTING_LEDGER.md` with source URL, commit SHA, and
SPDX license.

## Rationale

Alternatives considered:

1. **Fork OH-GUI or Forge-OH** — rejected. Both donors' primary artifacts (OH-GUI's
   TypeScript frontend, Forge-OH's `bff/` FastAPI layer + Socket.IO relay) are
   **decommissioned by design** per spec Definition of Done and §Phase 11. A fork would
   start with ~all the code marked for archival.

2. **Monorepo containing OH-GUI + Forge-OH as git submodules** — rejected. The spec
   explicitly requires archiving both frontends after decommission, not maintaining
   them. Submodules would perpetuate the version-drift and event-shape-compatibility
   risks flagged in spec Risk Notes.

3. **Fresh repo (chosen)** — matches the spec's "stock, unforked Agent Canvas" intent,
   provides clean provenance for every ported component via `PORTING_LEDGER.md`, and
   avoids inheriting donor frontends' git history and CI baggage.

Private (not public) matches this repo's owner's session preference expressed at
bootstrap time.

## Consequences

- New repo at `rmholston420/openhands-ext-v1`, private, MIT.
- `PORTING_LEDGER.md` becomes the authoritative record of what came from where.
- Both donor repos remain independent upstream references — this repo pulls **files**,
  not commits/tags.
- Phase 11 decommission archives donor code to `~/dev/archived-frontends/` per spec
  §Phase 11; nothing in this repo's git history requires rewriting.
- Files that touch this decision: `README.md`, `.gitignore`, `PORTING_LEDGER.md`,
  `docs/specs/integration-execution-plan-v16.md`.

## References

- Spec §Definition of Done
- Spec §Phase 11 — Decommission
- `PORTING_LEDGER.md` — Donor repositories section
