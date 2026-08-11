# OpenHands-Ext v1 · Session Handoff — 2026-08-11 06:39 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 (Medium-tier authoring paused)
- **Plugin / kernel component:** serve infra · production endpoints bring-up
- **Port(s) in progress:** coder (8100) restart pending; embedder (8090) config-changed, restart pending

## Completed this session
- ADR-0017 amendment #1 (coder 8000 → 8001) — committed 5ea0a2d
- ADR-0017 amendment #2 (coder 8001 → 8100; path layout fixes) — committed b61ced7
- Coder `--quantization awq_marlin` flag removed (compressed-tensors auto-detect) — committed cdc4117
- ADR-0017 amendment #3 (embedder GPU → CPU per spec; ctx 32768 → 4096; ngl 999 → 0) — pending commit
- DEBUG_LOG entry with compound-cause diagnosis + 3 reusable lessons
- KNOWN_ISSUES entry: deferred 4B-CPU vs. 0.6B-GPU embedder comparison

## Remaining before current Definition of Done
- Commit + push amendment #3 (embedder CPU, ADR update, selection JSON)
- On Colossus: stop current GPU-embedder; pull; restart embedder (now CPU); verify VRAM free ≥ 30 GiB; restart coder; run `check-production-endpoints.sh`
- Investigate Ollama-shaped `/v1/models` response on port 8090 (separate; low priority; embedder verified functional via `dim=2560`)
- Return to 4 deferred spec-compliance questions once coder is healthy

## Open questions / awaiting user answer
- Four deferred spec-compliance questions (ADR-0017 status label, env-vars vs. `configs/dev-current/`, Phase-1 pre-commit hook, un-pause checklist location) — deferred until coder healthy

## Exact next action
On Colossus (`~/dev/openhands-ext-v1`):
```bash
# Stop current (GPU) embedder
pkill -f 'llama-server.*8090' || true
sleep 2
# Pull amendment #3
git pull
# Restart embedder (now CPU)
bash scripts/serve-embedder.sh >/tmp/serve-embedder.log 2>&1 &
sleep 8
# Verify: VRAM should be near-full-free (~31 GiB), embedder responds on 8090
nvidia-smi --query-gpu=memory.free --format=csv,noheader
curl -sS http://127.0.0.1:8090/v1/models | head -20
# Restart coder
bash scripts/serve-coder.sh >/tmp/serve-coder.log 2>&1 &
sleep 30
# Full health check
bash scripts/check-production-endpoints.sh
```
