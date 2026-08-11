#!/usr/bin/env bash
# Phase 3 · Item 3.g (embedder half) — embedding round-trip smoke.
#
# Direct HTTP POST to http://127.0.0.1:8090/v1/embeddings (no SDK, no litellm),
# per Row-2 pattern of isolating endpoint capability from SDK layers.
#
# ADR-0017 amendment #3: embedder is CPU-resident, always-on, coexists with
# whichever large GPU model is up (coder or planner). This smoke is intended
# to run WHILE planner is up on :8082.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

OUT_ROOT="$HOME/.forge-oh/bench_smoke_phase_3_item_3g_embedder"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$OUT_ROOT/${TS}_run"
mkdir -p "$OUT_DIR"

echo "=== Phase 3 · Item 3.g (embedder) round-trip smoke — $(date -Iseconds) ==="
echo "Output dir: $OUT_DIR"

# Sanity: embedder up?
if ! curl -sf -m 3 http://127.0.0.1:8090/v1/models >/dev/null 2>&1; then
    echo "FAIL: embedder :8090 not responding to /v1/models" >&2
    echo '{"pass": false, "error": "embedder :8090 not up"}' > "$OUT_DIR/verdict.json"
    cat "$OUT_DIR/verdict.json"
    exit 2
fi

.venv/bin/python - "$OUT_DIR" <<'PY'
import json
import math
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

out_dir = Path(sys.argv[1])
verdict = {
    "task": "3g_embedder_roundtrip",
    "endpoint": "http://127.0.0.1:8090/v1",
    "started_utc": datetime.now(timezone.utc).isoformat(),
}

# Three inputs: two distinct, one duplicate of #1 for determinism check.
INPUTS = [
    "The quick brown fox jumps over the lazy dog.",
    "OpenHands-Ext v1 targets Colossus with a single-user local-first stack.",
    "The quick brown fox jumps over the lazy dog.",
]
verdict["inputs"] = INPUTS


def cos(a, b):
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return num / (na * nb)


def l2(v):
    return math.sqrt(sum(x * x for x in v))


try:
    payload = {
        "model": "qwen3-embedding-4b-q8-gguf",
        "input": INPUTS,
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8090/v1/embeddings",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as r:
        status = r.status
        body = json.loads(r.read().decode())
    wall = round(time.time() - t0, 3)
    verdict["http_status"] = status
    verdict["wall_seconds"] = wall

    data = body.get("data", [])
    verdict["response_has_data"] = bool(data)
    verdict["n_returned"] = len(data)
    verdict["n_expected"] = len(INPUTS)

    if len(data) != len(INPUTS):
        raise RuntimeError(
            f"expected {len(INPUTS)} embeddings, got {len(data)}"
        )

    vecs = [item.get("embedding") for item in data]
    verdict["vec_types"] = [type(v).__name__ for v in vecs]
    verdict["vec_lens"] = [len(v) if v is not None else None for v in vecs]

    # All vectors present, same length, floats, nonzero.
    lens = set(verdict["vec_lens"])
    verdict["all_same_length"] = len(lens) == 1 and None not in lens
    verdict["all_float"] = all(
        v is not None and all(isinstance(x, (int, float)) for x in v) for v in vecs
    )
    verdict["l2_norms"] = [round(l2(v), 6) for v in vecs]
    verdict["all_nonzero"] = all(n > 0 for n in verdict["l2_norms"])

    # Discrimination: input 0 vs input 1 must differ.
    verdict["cos_0_1"] = round(cos(vecs[0], vecs[1]), 6)
    verdict["different_inputs_differ"] = verdict["cos_0_1"] < 0.999

    # Determinism: input 0 vs input 2 (identical text) must match.
    verdict["cos_0_2"] = round(cos(vecs[0], vecs[2]), 6)
    max_abs_diff = max(abs(a - b) for a, b in zip(vecs[0], vecs[2]))
    verdict["identical_inputs_max_abs_diff"] = float(max_abs_diff)
    # Float32 epsilon-scale tolerance:
    verdict["identical_inputs_match"] = max_abs_diff < 1e-5

    verdict["pass"] = bool(
        status == 200
        and verdict["response_has_data"]
        and verdict["all_same_length"]
        and verdict["all_float"]
        and verdict["all_nonzero"]
        and verdict["different_inputs_differ"]
        and verdict["identical_inputs_match"]
        and wall < 30
    )
    verdict["error"] = None
except Exception as e:
    traceback.print_exc()
    verdict["pass"] = False
    verdict["error"] = repr(e)

(out_dir / "verdict.json").write_text(
    json.dumps(verdict, indent=2, default=str)
)
print(json.dumps(verdict, indent=2, default=str))
PY

RC=$?
echo "=== Item 3.g (embedder) smoke complete — rc=$RC — verdict at $OUT_DIR/verdict.json ==="
exit "$RC"
