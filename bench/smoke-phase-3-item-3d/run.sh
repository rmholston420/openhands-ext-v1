#!/usr/bin/env bash
# Phase 3 · Item 3.d — Agent Canvas served through ingress :8000
# Assumes Canvas is already running at http://127.0.0.1:8000 (started via `npm run dev` in ~/dev/agent-canvas-stock with OH_CANVAS_SAFE_VITE_PORT=3002).

set -euo pipefail

OUT="${OUT:-$HOME/.forge-oh/bench_smoke_phase_3_item_3d/$(date +%Y%m%d_%H%M%S)_run}"
mkdir -p "$OUT"

python3 - "$OUT" <<'PY'
import json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

out = Path(sys.argv[1])
canvas_head = "/home/rmholston/dev/agent-canvas-stock/.git/HEAD"
verdict = {
    "task": "3d_agent_canvas_up",
    "spec_ref": "OpenHands-Ext v16 §Phase 3.d — Agent Canvas cloned + running against ingress endpoint",
    "ingress": "http://127.0.0.1:8000",
    "canvas_version": "v1.6.1",
    "canvas_sha": open(canvas_head).read().strip() if Path(canvas_head).exists() else None,
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "port_map": {"ingress": 8000, "frontend_vite": 3002, "agent_server": 18000, "automation": "N/A"},
    "notes": [
        "Vite remapped 3001->3002 via OH_CANVAS_SAFE_VITE_PORT (3001 owned by Gitea).",
        "automation-1.3.1 not launched: stale automations.db (rev 013).",
        "Automation not required for spec v16 §3.d acceptance.",
    ],
    "checks": [],
}
CHECKS = [
    ("frontend_index",   "http://127.0.0.1:8000/",             200, "OpenHands"),
    ("server_info",      "http://127.0.0.1:8000/server_info",  200, None),
    ("health",           "http://127.0.0.1:8000/health",       200, None),
    ("alive",            "http://127.0.0.1:8000/alive",        200, None),
    ("openapi_json",     "http://127.0.0.1:8000/openapi.json", 200, "openapi"),
]
all_pass = True
for name, url, want_status, want_needle in CHECKS:
    entry = {"name": name, "url": url}
    try:
        t0 = time.time()
        with urllib.request.urlopen(url, timeout=10) as r:
            body = r.read()
            entry["status"] = r.status
            entry["bytes"] = len(body)
            entry["wall_ms"] = int((time.time()-t0)*1000)
            ok = r.status == want_status
            if want_needle:
                nf = want_needle.lower() in body[:8192].decode(errors="replace").lower()
                entry["needle_found"] = nf
                ok = ok and nf
            entry["pass"] = ok
    except Exception as e:
        entry.update({"status": None, "error": repr(e), "pass": False})
    if not entry["pass"]:
        all_pass = False
    verdict["checks"].append(entry)

verdict["pass"] = all_pass
(out/"verdict.json").write_text(json.dumps(verdict, indent=2, default=str))
print(json.dumps(verdict, indent=2, default=str))
PY

echo
echo "Verdict: $OUT/verdict.json"
