# OpenHands-Ext v1 Session Handoff — 2026-08-11 06:10 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 benchmarking **PAUSED**. Production role assignments locked (ADR-0017 · Amended). Health-check script authored. Awaiting model downloads on Colossus.
- **Plugin / kernel component:** Production serve infrastructure complete for coder / planner / embedder; health-check ready; interim OpenHands dev-config **not yet authored** (Option B — pending model materialization).
- **Port(s) in progress:** none.

## Completed this session
- ADR-0014 (Ratified) — coder-fast pool reinstated 2→4.
- ADR-0015 (Ratified · Confirmed) — thinker-2507-awq unfit for planner Medium.
- ADR-0016 (Ratified) — Medium-tier hybrid scoring rubric.
- embedder-medium task set (both arms) + retrieval probe + BEIR materializer.
- Verdict aggregator + BEIR SciDocs materialized on Colossus (5000/100/603).
- **ADR-0017 (Ratified · Amended 2026-08-11 06:10 EDT) — production role selection locked:**
  - coder = qwen3-coder-30B-A3B-instruct-awq-4bit (vLLM, **port 8001** — was 8000; amended after conflict with OpenHands agent)
  - planner = qwen3.6-35B-A3B-Q4_K_XL GGUF (llama.cpp, port 8082)
  - embedder = qwen3-embedding-4B Q8_0 GGUF (llama.cpp, port 8090; always-resident)
  - co-residency = Option 2 (single-role-at-a-time for large models)
- Serve infrastructure: `scripts/serve-{coder,planner,embedder}.sh`, `scripts/stop-large-model.sh`.
- **`scripts/check-production-endpoints.sh`** authored: reads production-selection.json, verifies `/v1/models` and role-appropriate canary per endpoint.

## Locked production endpoints (post-amendment)

| Role | Endpoint | Server binary | Port |
|---|---|---|---|
| coder | http://127.0.0.1:8001/v1 | vLLM (venv `.venv/bin/vllm`) | **8001** |
| planner | http://127.0.0.1:8082/v1 | llama-server | 8082 |
| embedder | http://127.0.0.1:8090/v1 | llama-server | 8090 |

**Reserved (do not touch):** 127.0.0.1:8000 = OpenHands agent (PID 1670687, UID 10001 on Colossus).

## Deferred work (do not resume until user un-pauses)
- Interim `configs/dev-current/` (Option B) — publishes ADR-0017 endpoints to OpenHands as env/JSON. Deferred until models are materialized and endpoints verified with `check-production-endpoints.sh`.
- Embedder-medium bench (both arms) + verdict ADR-0018.
- Planner-medium task set + bench + verdict ADR-0019.
- Coder-medium task set + bench + verdict ADR-0020.
- Auto-router (lazy load large-model on demand) — only if Medium-tier evidence shows switch cost matters.

## Open questions / awaiting user answer
- None. Blocker is materialization of model files, not any design decision.

## Exact next action

On Colossus:

```bash
cd ~/dev/openhands-ext-v1
git pull --ff-only

# Verify the amendment landed
grep -n "PORT=" scripts/serve-coder.sh                                    # should show PORT="8001"
grep -n '"port"' bench/candidates/production-selection.json | head -3     # coder=8001, planner=8082, embedder=8090

# Preview the download plan (no bytes transferred)
bash scripts/pull-models.sh --role all --dry-run

# If the plan looks right and disk check passes, materialize the models
bash scripts/pull-models.sh --role all

# After download, verify layout
cat models/manifest.json | jq 'keys' | head -20
ls models/qwen3-coder-30b-a3b-instruct-awq-4bit/
ls models/qwen3_6-35b-a3b-q4kxl-gguf/
ls models/qwen3-embedding-4b-q8-gguf/

# Then start embedder (always-resident) and one large model, and health-check
nohup bash scripts/serve-embedder.sh > /tmp/serve-embedder.log 2>&1 &
sleep 30
nohup bash scripts/serve-coder.sh    > /tmp/serve-coder.log    2>&1 &
sleep 60
bash scripts/check-production-endpoints.sh              # should PASS all three (planner will fail — expected, not running)
bash scripts/check-production-endpoints.sh coder        # coder-only
bash scripts/check-production-endpoints.sh embedder     # embedder-only
```

Once `check-production-endpoints.sh` passes for coder + embedder, paste the summary back and I'll author the interim `configs/dev-current/` (Option B) for OpenHands wiring.

## Potential fixup on first serve

The three serve scripts expect model paths at:
- `models/qwen3-coder-30b-a3b-instruct-awq-4bit/hf/config.json`
- `models/qwen3_6-35b-a3b-q4kxl-gguf/gguf/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`
- `models/qwen3-embedding-4b-q8-gguf/gguf/Qwen3-Embedding-4B-Q8_0.gguf`

If `pull-models.sh` writes to a different layout (check `models/manifest.json`), paste the actual paths and I'll issue a targeted patch to the serve scripts.
