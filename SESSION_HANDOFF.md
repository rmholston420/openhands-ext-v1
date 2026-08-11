# OpenHands-Ext v1 Session Handoff — 2026-08-11 06:24 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.2 benchmarking **PAUSED**. ADR-0017 (production role selection) amended twice today for port conflicts. Serve-script path layouts corrected. Models materialized on Colossus. Endpoints not yet started under the new port.
- **Plugin / kernel component:** Serve infrastructure ready. Health-check script ready. Interim OpenHands wiring **still pending** — awaiting successful health-check under port 8100 before Option B is authored.
- **Port(s) in progress:** none.

## Completed this session
- ADR-0014, ADR-0015 (Fast-tier verdict rounds), ADR-0016 (Medium-tier hybrid rubric).
- embedder-medium task set + BEIR SciDocs materializer + BEIR materialized on Colossus (5000/100/603).
- **ADR-0017 (Ratified · Amended twice 2026-08-11):**
  - coder = qwen3-coder-30B-A3B-instruct-awq-4bit (vLLM, port **8100** — amended 8000→8001 06:10 EDT, then 8001→8100 06:24 EDT)
  - planner = qwen3.6-35B-A3B-Q4_K_XL GGUF (llama.cpp, port 8082)
  - embedder = qwen3-embedding-4B Q8_0 GGUF (llama.cpp, port 8090; always-resident)
  - co-residency = Option 2
- Serve infrastructure authored: `scripts/serve-{coder,planner,embedder}.sh`, `scripts/stop-large-model.sh`.
- **Model layout mismatch fixed:** `pull-models.sh` writes flat to `models/<slug>/`, not `models/<slug>/{hf,gguf}/`. All three serve scripts updated.
- **`scripts/check-production-endpoints.sh`** authored: reads production-selection.json; automatically picked up new port with no code change.
- All 9 registry candidates materialized on Colossus (see `models/manifest.json`); 385 GiB free.

## Locked production endpoints (post amendments #1 + #2)

| Role | Endpoint | Server binary | Port |
|---|---|---|---|
| coder | http://127.0.0.1:8100/v1 | vLLM (venv `.venv/bin/vllm`) | **8100** |
| planner | http://127.0.0.1:8082/v1 | llama-server | 8082 |
| embedder | http://127.0.0.1:8090/v1 | llama-server | 8090 |

**Reserved on Colossus (do not touch):**
- 127.0.0.1:6379 = docker-pr (Redis)
- 127.0.0.1:8000 = OpenHands agent
- **0.0.0.0:8001 = OpenHands node frontend**
- 127.0.0.1:8080 = python3 (root)
- 127.0.0.1:8888 = docker-pr
- 127.0.0.1:11434 = ollama

## Flags raised this session, awaiting user directive (all deferred)
- **Flag: ADR-0017 status wording.** Spec §0.0 says only Phase 0.3 (Full tier) can declare a production winner; ADR-0017 uses the word "production" pre-0.3. Rename to `Interim · Amended (pre-Phase-0.3)` with a "Return to spec" clause?
- **Flag: Interim config path.** `configs/dev-current/` (invented) vs. env-vars-only for OpenHands `openhands serve` launch. Env-vars-only is stricter spec adherence.
- **Flag: Phase 1 DockerWorkspace grep hook.** Spec §Phase 1 requires CI/pre-commit enforcement of zero-`LocalWorkspace`. Hook does not exist yet.
- **Flag: `openai/` model-name prefix.** Non-negotiable per spec §2.4. Will apply when Option B (or env-vars) is authored.

## Deferred until user un-pauses benchmarking
- Phase -1 provenance re-verification (llama.cpp build tag + vLLM release tag freshly re-fetched with fetch timestamp) — MUST precede Medium tier.
- Fast-tier JSON audit for 7-category schema completeness (Category 3–7 + runtime tags).
- Embedder-medium bench (both arms) + ADR-0018.
- Planner-medium + ADR-0019.
- Coder-medium + ADR-0020.
- Auto-router (only if evidence justifies).

## Open questions / awaiting user answer
- None blocking the immediate serve-and-verify step. Flags above are for the post-verification interim-config choice.

## Exact next action

On Colossus:

```bash
cd ~/dev/openhands-ext-v1
git pull --ff-only

# Sanity checks
grep -n "PORT=" scripts/serve-coder.sh                                     # PORT="8100"
grep -n '"port":' bench/candidates/production-selection.json | head -3     # coder=8100, planner=8082, embedder=8090
grep -n "HF_MODEL_DIR\|^GGUF=" scripts/serve-coder.sh scripts/serve-planner.sh scripts/serve-embedder.sh

# Start embedder (always-resident) FIRST
nohup bash scripts/serve-embedder.sh > /tmp/serve-embedder.log 2>&1 &
sleep 30
tail -20 /tmp/serve-embedder.log        # confirm llama-server up on 8090

# Then coder
nohup bash scripts/serve-coder.sh > /tmp/serve-coder.log 2>&1 &
sleep 60
tail -20 /tmp/serve-coder.log           # confirm vLLM up on 8100

# Health-check
bash scripts/check-production-endpoints.sh embedder
bash scripts/check-production-endpoints.sh coder
```

**Expected outcomes:**
- embedder PASS on port 8090, vector dim reported (likely 1024 or 2560).
- coder PASS on port 8100, chat completion round-trip OK.

**If either FAILS:**
- Paste the last 40 lines of `/tmp/serve-{embedder,coder}.log`.
- Paste the failing `check-production-endpoints.sh` output.
- Do NOT amend ADR-0017 again — the port and layout are now verified. Any new failure is a runtime or model-loading issue, not port allocation.

Once both PASS, tell me and I'll:
1. Address the four flagged spec-compliance questions above.
2. Author the interim OpenHands wiring (env-vars-only if you choose that route).

## Handoff invariants (do not break)
- Coder = port 8100 (ADR-0017 amended twice).
- Planner = port 8082 (ADR-0017).
- Embedder = port 8090 (ADR-0017); always-resident; never stopped by `stop-large-model.sh`.
- OpenHands owns 8000 + 8001. Do not attempt to displace.
- Model layout is flat: `models/<slug>/`, no subdirectories.
