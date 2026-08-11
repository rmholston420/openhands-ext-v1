# ADR-0002 — LocalWorkspace Guard: Pre-Commit Hook, Not GitHub Actions

**Status:** Ratified
**Lock-in phase:** Phase 1
**Supersedes:** —

## Context

Spec §Phase 1 mandates that the "zero `LocalWorkspace`" policy be enforced **by
mechanism, not documentation alone**:

> No `LocalWorkspace` fallback anywhere in configuration, scripts, or documentation —
> enforced by a grep check in CI or a pre-commit hook, not documentation alone.

Spec Risk Notes reiterate:

> Phase 1's zero-`LocalWorkspace` policy must be enforced by CI/pre-commit grep, not
> documentation alone — a single missed fallback path defeats the entire trust model.

The spec offers the choice CI-or-hook. Space custom instructions push the choice
firmly in one direction:

> single-user, local-first system — never introduce cloud control planes, multi-user
> assumptions, or GitHub-native CI dependencies unless I explicitly ask.

And Perplexity Computer Custom Instruction #3 (spec §Perplexity Computer Execution
Package):

> Grep for "LocalWorkspace" after every phase that touches configuration or code and
> fail the phase if any reference is found outside test/example code.

User explicitly ratified "pre-commit hook" in session `a97513e8-710d-484b-a54a-2e2e18ae0c24`.

## Decision

Enforce the zero-`LocalWorkspace` policy via a **local pre-commit hook**:
`hooks/pre-commit/no-localworkspace.sh`. Installed on every Colossus checkout by
`scripts/install-hooks.sh`. No GitHub Actions workflow is created for this purpose.

The hook `grep -rn "LocalWorkspace" .` across the working tree (excluding
`docs/specs/`, `docs/donor-inventory.md`, `adrs/`, `PORTING_LEDGER.md`, `BUILD_LOG.md`,
`DEBUG_LOG.md`, `KNOWN_ISSUES.md`, `SESSION_HANDOFF.md`, and test/example paths) and
exits non-zero if any match is found in code or config.

## Rationale

Alternatives considered:

1. **GitHub Actions workflow** — rejected. Introduces cloud CI dependency that the
   space custom instructions explicitly disallow. Also runs post-push, after the
   violation is already in the repo history — worse than pre-commit which blocks the
   commit locally.

2. **Documentation only** — rejected by spec (§Phase 1 and Risk Notes) as insufficient.

3. **Pre-commit hook (chosen)** — runs locally on Colossus before commit lands, aligns
   with local-first posture, no cloud dependency, matches spec's "grep check" wording
   directly. Installer script is idempotent and needs to run once per checkout.

## Consequences

- New file: `hooks/pre-commit/no-localworkspace.sh` — the hook script.
- New file: `scripts/install-hooks.sh` — copies the hook into `.git/hooks/pre-commit`
  and marks it executable. Idempotent.
- Every new Colossus checkout of this repo must run `bash scripts/install-hooks.sh`
  once. `SESSION_HANDOFF.md` includes this in its "next action" section.
- The hook must be re-run manually or re-installed if a developer bypasses it with
  `git commit --no-verify` — this is a soft failure mode by design (local-first =
  trusts the operator to not lie to themselves).
- The hook's allow-list (paths where "LocalWorkspace" is a spec quote, not a code
  reference) is maintained inside the script and updated when new documentation paths
  legitimately quote the term.
- Files that touch this decision: `hooks/pre-commit/no-localworkspace.sh`,
  `scripts/install-hooks.sh`, `SESSION_HANDOFF.md`, `BUILD_LOG.md`.

## References

- Spec §Phase 1 — Fixed Workspace Policy
- Spec Risk Notes (zero-`LocalWorkspace` enforcement)
- Space custom instructions (no GitHub-native CI dependencies)
- Perplexity Computer Custom Instruction #3
