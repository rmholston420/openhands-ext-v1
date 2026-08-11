# ADR-0019 — Phase 2 MCP port range, mode wrapper, and skills convention

**Status:** Ratified · 2026-08-11 07:18 EDT
**Lock-in phase:** Phase 2
**Supersedes:** —

## Context

Spec §2.1–2.3 describes three suite-wide configuration surfaces (deployment modes, MCP install pattern, retroactive skill capture) but leaves several choices to the implementer:

1. **§2.1 headless-mode gating.** Spec says "reserve headless/CI automation for low-risk, well-scoped tasks only" without specifying an allowlist mechanism.
2. **§2.2 MCP port range.** Spec locks the `supergateway` install pattern but does not reserve a port range for Phases 5–7 MCP servers.
3. **§2.3 skill storage.** Spec offers both `<repo>/.agents/skills/` and `~/.agents/skills/` without guidance on which to use when.

Colossus already occupies ports 8000/8001/8082/8090/8100 (OpenHands defaults + coder/planner/embedder). MCP servers landing in Phases 5–7 must not collide.

## Decision

**D1. Headless gating = explicit invoker acknowledgment.**
`scripts/openhands-mode.sh headless` requires `--acknowledge-low-risk` as the first positional argument. No allowlist. The invoker asserts risk classification per invocation. Automation to grep task intent is premature until Phase 3+ provides task-shape metadata.

**D2. MCP port range = 8110–8199.**
Reserved for all supergateway-proxied MCP servers filed under this repo. 90 ports, above every currently-occupied host port, below 8200 (kept clear as buffer). Ports assigned first-come per Phase 5–7 filing. `scripts/mcp-supergateway.sh` rejects ports outside this range.

**D3. Skills storage = both, with clear split.**
Repo-local `<repo>/.agents/skills/` for skills shared across every clone of this repo (committed). User-local `~/.agents/skills/` for personal cross-repo skills (not committed to any repo). Retroactive-only per §2.3 discipline.

## Rationale

**D1 — invoker acknowledgment beats speculative allowlist.**
An allowlist requires task metadata (risk score, blast radius, reversibility) that Phase 2 has no source for. A grep-only allowlist would be either too permissive (blocks nothing real) or too brittle (breaks on paraphrasing). Explicit invoker acknowledgment via bare flag forces a moment of thought without pretending to encode judgment. Trivial to tighten later when Phase 3+ produces task-shape metadata; wrapper `--acknowledge-low-risk` becomes a hard-coded gate at that point.

**D2 — 8110–8199 chosen for three reasons.**
(a) Above every currently-occupied host port on Colossus. (b) 90 ports covers any plausible Phase 5–7 MCP fanout. (c) Round-number lower bound (8110) is easy to remember and grep for. Reserving 8200+ preserves headroom if MCP allocation ever fills.

**D3 — both, because they serve different purposes.**
Repo-local skills are part of the codebase (versioned, reviewed, shared). User-local skills are personal preferences (not-versioned, per-user). Forcing one or the other loses signal. The split is explicit in `.agents/skills/README.md`.

**Rejected alternative for D2:** dynamic port allocation (bind port 0, publish actual port to a registry file). Rejected because MCP tools' `base_url` is often hardcoded in agent instructions or Canvas configs; dynamic ports would force re-discovery on every restart.

**Rejected alternative for D1:** hardcoded task allowlist regex. Rejected because §2.1's phrasing is intentionally judgment-based ("low-risk, well-scoped") and regexes over free-text task descriptions are false-positive machines.

## Consequences

- New file: `scripts/openhands-mode.sh` — three-way dispatcher with preflight.
- New file: `scripts/mcp-supergateway.sh` — MCP launcher template with port-range gate.
- New file: `docs/MCP_PORT_ALLOCATION.md` — allocation table for Phases 5–7 to append to.
- New file: `.agents/skills/README.md` + `.gitkeep` — retroactive-capture convention.
- New file: `docs/PHASE-2-CONFIG.md` — Phase 2.1–2.3 summary and file map.
- No install action taken. `openhands` CLI and `supergateway` remain user-installed prereqs; wrappers fail-loud with install instructions if either is missing.
- No changes to §2.4 (Phase 0.3-gated) or §2.5 (Phase 3+).
- Phase 5–7 MCP servers MUST use `scripts/mcp-supergateway.sh` and MUST append their allocated port row to `docs/MCP_PORT_ALLOCATION.md` before first launch.

## Lock-in phase

Phase 2. Amendment allowed at any time; a change to the port range (D2) requires re-checking every filed allocation. A change to headless gating (D1) requires updating every downstream automation touching `scripts/openhands-mode.sh headless`.

## References

- `docs/specs/integration-execution-plan-v16.md` § Phase 2.1–2.3
- `docs/PHASE-2-CONFIG.md`
- `docs/MCP_PORT_ALLOCATION.md`
- ADR-0002 (LocalWorkspace guard) — Phase 1 policy that the mode wrapper defers to
