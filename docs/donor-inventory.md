# Donor Repository Inventory

Snapshot of the two donor repositories at the time this project was bootstrapped.
The `PORTING_LEDGER.md` pins per-file commit SHAs for every planned port; this document
records the top-level context (HEAD SHAs, licenses, directory shape) so future sessions
can reason about donor drift.

Fetch timestamp: `2026-08-11T03:24:45Z` (UTC).

---

## rmholston420/oh-gui

- **URL:** https://github.com/rmholston420/oh-gui
- **HEAD SHA at inventory:** `ef3ac1a5c681e52835dda9fca43cad4ab1331d76`
- **HEAD commit:** `docs: change review witnessed live 3/3; handoff` (2026-08-09)
- **License:** MIT (`Copyright (c) 2026 R. M. Holston`)

### Top-level layout (relevant portions)

```
oh-gui/
├── adrs/                                  # 30+ ADRs — reference material only, not ported
├── apps/gui/                              # TypeScript/React frontend — DECOMMISSIONED per spec DoD
│   └── src/features/authorization/        # blast-radius logic lives here (Phase 8 port target)
│       ├── blast-radius.ts                # <-- PORTED (logic rewrite to Python)
│       ├── blast-radius.test.ts           # <-- reference for four-outcome contract
│       ├── BlastRadiusSection.tsx         # <-- REJECTED (UI replaced by stock Canvas)
│       ├── AuthorizationCard.tsx          # <-- REJECTED (same)
│       └── AgentAccountSection.tsx        # <-- REJECTED (same)
├── bench/                                 # benchmark infra — reference for our bench/ layout
├── services/middleware/                   # decommissioned per spec §Phase 11
└── review/_sdk_src/1.41.0/                # snapshot of openhands-sdk 1.41.0 for reference
```

**Ports drawn from this repo:** exactly one — the blast-radius projection logic (Phase 8).
All UI code is replaced by stock Agent Canvas.

---

## rmholston420/Forge-OH

- **URL:** https://github.com/rmholston420/Forge-OH
- **HEAD SHA at inventory:** `df73ebed2d6d9df9397f7e95dd1eb66bd3dd98b2`
- **HEAD commit:** `Slice 8.0.5: closeout entry for SMOKE_100 populate + updated session handoff` (2026-08-06)
- **License:** MIT (`Copyright (c) 2026 rmholston420`)

### Top-level layout (relevant portions)

```
Forge-OH/
├── bff/                                   # FastAPI backend-for-frontend — decommissioned per spec §Phase 11
│   ├── openhands_client.py                # <-- INSPECTED (Phase 4 contract check; not ported)
│   └── services/
│       ├── gpu_monitor.py                 # <-- PORTED (Phase 5, MCP server)
│       ├── episodic_memory.py             # <-- PORTED (Phase 6, MCP server)
│       ├── event_normalize.py             # <-- CONDITIONAL patch (Phase 4 contingency)
│       └── inference_backends/
│           └── registry.py                # <-- PORTED (Phase 6, MCP server; needs adapter code changes if llama.cpp wins)
├── openhands_tools_ext/
│   ├── repograph/                         # Phase 7 port target
│   │   ├── index.py                       # <-- PORTED
│   │   ├── parser.py                      # <-- PORTED
│   │   └── store.py                       # <-- PORTED (Neo4j Bolt client)
│   ├── memory/                            # newer memory subsystem — inspect at Phase 6 for episodic_memory synergy
│   ├── gpu/                               # newer GPU subsystem — inspect at Phase 5 for gpu_monitor synergy
│   ├── search/                            # not in Phase 5-10 scope
│   ├── selfeval/                          # not in Phase 5-10 scope
│   ├── verify/                            # not in Phase 5-10 scope
│   └── ...
└── bench/                                 # benchmark infra — reference for our bench/ layout
```

**Ports drawn from this repo:** GPU telemetry (Phase 5), episodic memory + inference-backend
health (Phase 6), RepoGraph indexer + parser + store (Phase 7). Backend contract inspection
only (Phase 4).

Newer subsystems in `openhands_tools_ext/memory/` and `openhands_tools_ext/gpu/` were **not**
enumerated in the v16 spec's Phase 5/6 port list — they may supersede the older
`bff/services/` versions, but the spec references the `bff/services/` paths explicitly.
**Flagged for Phase 5/6 review**: check whether the newer subsystems are the intended
source and the v16 spec's `bff/services/*` references are stale.

---

## Verification

Both donors verified MIT-licensed. Both cloned by `gh repo clone` under authenticated
user `rmholston420` — same owner as this repo. No third-party dependencies added by
these inventories.
