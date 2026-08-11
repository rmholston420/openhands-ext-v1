# canvas-panel/ — Purpose-Built Canvas Plugin Surfaces

Per spec Definition of Done, **exactly one** new frontend surface ships in the final
system: the RepoGraph Canvas plugin panel. Everything else in this directory tree is
guarded scaffolding.

## repograph/ (Phase 7)

Canvas plugin panel that connects via **Bolt protocol** to a live Neo4j instance
populated by `mcp-servers/repograph/`. Built against Canvas's native plugin API,
using `neovis.js`.

Per spec Phase 7 Verification:

- Neo4j restart persistence
- Malicious-repo index safety (indexer fails safely, no crash/corruption)
- Panel renders in Canvas against live Bolt connection
- Scale: 1000+-symbol repo remains responsive

Phase 7 is the **largest net-new engineering effort** in this project and is scoped as
its own mini-project. Do not let it block Phases 8-11.
