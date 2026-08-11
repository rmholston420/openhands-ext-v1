# OpenHands-Ext v1 Session Handoff — 2026-08-11 06:00 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 benchmarking **PAUSED**. Production role assignments locked. Ready for Phase 1 handoff (OpenHands router / MCP wiring).
- **Plugin / kernel component:** Production serve infrastructure complete for coder / planner / embedder.
- **Port(s) in progress:** none.

## Completed this session
- ADR-0014 (Ratified) — coder-fast pool reinstated 2→4. Pushed 66249e1.
- ADR-0015 (Ratified · Confirmed) — thinker-2507-awq unfit for planner Medium. Pushed dbfa0fd.
- ADR-0016 (Ratified) — Medium-tier hybrid scoring rubric frozen. Pushed 03efcee.
- embedder-medium task set (both arms) + retrieval probe + BEIR materializer. Pushed 8e17bd2.
- Verdict aggregator + BEIR SciDocs materialized on Colossus (5000/100/603). Pushed c1f6c50.
- **ADR-0017 (Ratified) — production role selection locked pre-Medium-tier.**
  - coder = qwen3-coder-30B-A3B-instruct-awq-4bit (vLLM, port 8000)
  - planner = qwen3.6-35B-A3B-Q4_K_XL GGUF (llama.cpp, port 8082)
  - embedder = qwen3-embedding-4B Q8_0 GGUF (llama.cpp, port 8090; always-resident)
  - co-residency = Option 2 (single-role-at-a-time for large models)
- **Serve infrastructure authored:**
  - `scripts/serve-coder.sh`, `scripts/serve-planner.sh`, `scripts/serve-embedder.sh`, `scripts/stop-large-model.sh`
  - `bench/candidates/production-selection.json` (canonical role → model mapping)

## Locked production endpoints
| Role | Endpoint | Server binary | Port |
|---|---|---|---|
| coder | http://127.0.0.1:8000/v1 | vLLM (Docker or venv) | 8000 |
| planner | http://127.0.0.1:8082/v1 | llama-server | 8082 |
| embedder | http://127.0.0.1:8090/v1 | llama-server | 8090 |

## Deferred work (do not resume until user un-pauses)
- Embedder-medium bench (both arms) on Colossus.
- Aggregator run + ADR-0018 (embedder-medium tier verdict).
- Planner-medium task set + bench + ADR-0019 (verdict).
- Coder-medium task set + bench + ADR-0020 (verdict).
- Auto-router (lazy load large-model on demand) — only if Medium-tier evidence shows switch cost matters.

## Open questions / awaiting user answer
- None. Selection is ratified. User's next move determines whether to (a) start the servers on Colossus and hand off to OpenHands router work, or (b) resume Medium-tier benchmarking.

## Exact next action

On Colossus, verify model files are present, then start the always-resident embedder + one large-model server:

```bash
cd ~/dev/openhands-ext-v1
git pull --ff-only

# Verify HF/GGUF files exist for the three production models
ls models/qwen3-coder-30b-a3b-instruct-awq-4bit/hf/config.json
ls models/qwen3_6-35b-a3b-q4kxl-gguf/gguf/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf
ls models/qwen3-embedding-4b-q8-gguf/gguf/Qwen3-Embedding-4B-Q8_0.gguf

# Start embedder (always-on) in a tmux/screen or nohup
nohup bash scripts/serve-embedder.sh > /tmp/serve-embedder.log 2>&1 &

# Start whichever large model you need first — coder or planner
nohup bash scripts/serve-coder.sh   > /tmp/serve-coder.log   2>&1 &
# OR
nohup bash scripts/serve-planner.sh > /tmp/serve-planner.log 2>&1 &

# Check status any time
bash scripts/stop-large-model.sh status

# Swap between coder and planner
bash scripts/stop-large-model.sh coder     # then start planner
bash scripts/stop-large-model.sh planner   # then start coder
```

If any of the three model files is missing, the serve script will exit with a `huggingface-cli download` command you can copy-paste to fetch it.
