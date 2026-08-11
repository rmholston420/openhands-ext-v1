# Phase 3 · Item 3.d — Agent Canvas served through ingress :8000

## Spec ref
OpenHands-Ext v16 §Phase 3.d — Agent Canvas cloned + running against ingress endpoint.

## Result
**PASS** (5/5 spec-relevant HTTP checks against ingress :8000).

## Setup

| Component | Port | Source |
|---|---|---|
| Ingress proxy | 8000 | `scripts/dev-with-automation.mjs` |
| Vite frontend | 3002 | `dev:frontend` (remapped from 3001 via `OH_CANVAS_SAFE_VITE_PORT`; 3001 owned by Gitea) |
| Agent-server | 18000 | `uvx openhands-agent-server` (Canvas-managed) |
| Automation | 18001 | **NOT LAUNCHED** (see DEBUG_LOG 2026-08-11) — not required for §3.d |

## Canvas checkout
- Repo: https://github.com/OpenHands/agent-canvas.git
- Tag: v1.6.1
- SHA: 43f091baf135142ed6c146f888f44a957141193f
- Local path: ~/dev/agent-canvas-stock

## Checks executed
| Name | URL | Expected | Actual |
|---|---|---|---|
| frontend_index | http://127.0.0.1:8000/ | 200, contains "OpenHands" | 200, 1.13 MB, needle found |
| server_info | http://127.0.0.1:8000/server_info | 200 | 200, 660 B |
| health | http://127.0.0.1:8000/health | 200 | 200, 15 B |
| alive | http://127.0.0.1:8000/alive | 200 | 200, 15 B |
| openapi_json | http://127.0.0.1:8000/openapi.json | 200, contains "openapi" | 200, 544 KB, needle found |

## Deferred / out of scope for 3.d
- `/api/automation/*` — 502 because automation-1.3.1 aborts on stale `~/.openhands/automation/automations.db` (alembic revision `013` mismatch). Stale DB moved to `automations.db.stale-20260811_194023`. Automation is NOT in spec v16 §3.d acceptance criteria. Tracked in DEBUG_LOG 2026-08-11 19:44 EDT.

## Verdict file
`~/.forge-oh/bench_smoke_phase_3_item_3d/20260811_194509_run/verdict.json`
