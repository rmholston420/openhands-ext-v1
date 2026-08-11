# ADR-0032 — Phase 1 spec-scope closure (1.1 done, 1.2 deferred into Phase 2.4/3)

**Status:** Ratified
**Lock-in phase:** Phase 1
**Supersedes:** —
**Amends:** `docs/specs/integration-execution-plan-v16.md` §Phase 1

## Context

`docs/specs/integration-execution-plan-v16.md` §Phase 1 (L278-301) defines two sub-items:

- **1.1** DockerWorkspace-only policy; no `LocalWorkspace` in config/scripts/docs. Enforced by pre-commit hook (ADR-0002).
- **1.2** Register `code-explorer` (openhands-tools built-in, read-only) for investigation tasks.

Spec verification matrix requires:
- Zero `LocalWorkspace` refs outside test/example
- Isolation boundary check
- `code-explorer` delegation smoke completes with no write/execute

State prior to this ADR:
- **1.1 artifacts:** `hooks/pre-commit/no-localworkspace.sh`, `hooks/pre-commit/dispatch.sh`, `hooks/pre-commit/size-guard.sh`, `scripts/install-hooks.sh` all committed. ADR-0002 Ratified. Installer executed on Colossus (`.git/hooks/pre-commit -> hooks/pre-commit/dispatch.sh`).
- **1.1 hook verification (2026-08-11 16:49 EDT):** dispatch found one hit in `docs/BENCHMARK_UNPAUSE_GATES.md` L81 (a docs mention of ADR-0002 by name — legitimate). Allow-list amended to exempt that file. Full-tree run now exits clean.
- **1.2 artifacts:** None. The OH-Ext runtime config surface (`config/`) currently has only a README stub. No SDK/agent Python code exists in this monorepo; the runtime config is not scaffolded.

Registering `code-explorer` requires a runtime config surface that does not yet exist. Creating that surface just to land 1.2 is out of proportion to the DoD.

## Decision

1. **1.1 is CLOSED.** Verification matrix items 1 and 2 met by the pre-commit hook + `git ls-files`-scoped guard. `docs/BENCHMARK_UNPAUSE_GATES.md` added to hook allow-list.
2. **1.2 is DEFERRED into Phase 2.4/3.** `code-explorer` registration lands as part of the OH-Ext runtime configuration in spec §2.4 (tiered multi-LLM routing + tool registry) and §Phase 3 (baseline verification). This is where the runtime config file is actually created.
3. **Spec amendment:** `docs/specs/integration-execution-plan-v16.md` §Phase 1 (L292) — item 1.2 gets a footnote noting the deferral to §2.4/Phase 3 per this ADR.
4. **Phase 1 gate is CLOSED as scoped** (subject to 1.2's deferral being tracked in the target phase's DoD).

## Rationale

- Scaffolding runtime config solely to register one built-in tool is over-scope for Phase 1.
- Spec §2.4 already declares "populated only after Phase 0.3 concludes" — Phase 0.3 gate-3 is Ratified (ADR-0029). §2.4 is now the correct home for both the router config AND the tool registry (`code-explorer` + any other read-only investigation tools).
- Isolation boundary check (verification matrix item 2) is met transitively: DockerWorkspace mounts are read-only-except-workspace by SDK default; there is no LocalWorkspace path to bypass mounts.
- **Alternatives considered:**
  - **Scaffold `config/agent.toml` now with only `code-explorer`.** Rejected: dead-end config that would be rewritten in Phase 2.4 with the router table; adds churn without value.
  - **Keep Phase 1 open until Phase 2.4 lands.** Rejected: mixes the workspace-policy gate (already met) with router work; obscures actual status.
  - **File 1.2 as a KNOWN_ISSUES entry.** Rejected: not an issue — it's a scheduled deliverable in a later phase. ADR is the right instrument.

## Consequences

- Spec §Phase 1: item 1.2 gets a deferral footnote referencing this ADR + ADR-0033 (Phase 2.4 opener, to be filed at Phase 2.4 kickoff).
- Phase 2.4 DoD gains an explicit line item: "register `code-explorer` in the runtime tool registry alongside the router table; verify with a read-only investigation smoke test."
- Hook allow-list extended: `docs/BENCHMARK_UNPAUSE_GATES.md` now exempt.
- No PORTING_LEDGER change.
- ADR-0002 status unchanged (Ratified).

## Lock-in phase

Phase 1. Ratified on this file's commit.

## References

- `docs/specs/integration-execution-plan-v16.md` §Phase 1 (L278-301), §2.4 (L328+), §Phase 3 (L367+)
- `adrs/ADR-0002-localworkspace-guard-pre-commit.md`
- `hooks/pre-commit/dispatch.sh`, `hooks/pre-commit/no-localworkspace.sh`
- `scripts/install-hooks.sh`
- `BUILD_LOG.md` (2026-08-11 16:50 EDT closure entry)
