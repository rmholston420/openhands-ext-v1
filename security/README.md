# security/ — Phase 8 Native Security Analyzer

Phase 8 port: a native `SecurityAnalyzerBase` subclass that reimplements OH-GUI's
blast-radius projection logic on top of Canvas's built-in `LLMSecurityAnalyzer`.

**This is a logic port, not a code port.** OH-GUI's blast-radius logic is TypeScript
(`apps/gui/src/features/authorization/blast-radius.ts` at commit
`bab46c91ffa8c0f1283a5a5b02d9834f34a4288b`); the reimplementation here is Python against
`openhands.sdk.security.SecurityAnalyzerBase`. OH-GUI's frontend UI components
(`AuthorizationCard`, `BlastRadiusSection`, `AgentAccountSection`) are **not** ported —
Canvas's native confirmation UI replaces them per spec Definition of Done.

## Guarded invariants

Per spec §Phase 8:

- Preserve the four-outcome invariant.
- Guard against the documented mangled-class-name lookup bug (spec Risk Notes).

The companion test file `oh-gui/apps/gui/src/features/authorization/blast-radius.test.ts`
(same commit) is the reference for the four-outcome contract — port its cases to
`security/blast-radius/test_blast_radius.py` before writing the analyzer.
