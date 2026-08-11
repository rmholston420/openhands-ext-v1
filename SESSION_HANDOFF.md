# Kosmos / OpenHands-Ext v1 Session Handoff — 2026-08-11 08:12 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 1 · Full-suite live-proof COMPLETE.
- **Next stage:** Phase 0.3 (Medium-tier inference-backend selection) — was paused to prove full-suite viability first. Now proven, resume when user directs.
- **Plugin / kernel component:** openhands-app v1.11.0 + agent-server 1.36.0-python + coder vLLM (qwen3-coder-30B-A3B-AWQ4) + embedder llama.cpp CPU.

## Completed this session

- Phase −1 verification (ADR-0018, commit d45cb2f).
- Phase 2.1 / 2.2 / 2.3 implementation (ADR-0019, commit 7dad739): openhands-mode.sh dispatcher, mcp-supergateway.sh template, .agents/skills/ convention.
- Diagnosed and fixed full-suite sandbox spawn failure (ADR-0020, this commit): UFW default-DROP was blocking docker bridge → host published ports, killing the sandbox healthcheck after 15 s grace.
- Wrote v3 API-driven smoke test (`tests/smoke/test_openhands_suite_v3.py`, 5 tests including LLM traffic + event verification).
- Full-suite smoke 5/5 PASS on Colossus: T4 = +18113 prompt_tokens, T5 = 20 events.

## Remaining before current Definition of Done

- **None for the current sub-task.** Full-suite smoke Definition of Done: LLM traffic + agent events observed against the isolated openhands-app deployment. MET.
- Sandbox cleanup: transient sandbox `oh-agent-server-df2dec50*` still `Up` after the smoke. Delete when done: `docker rm -f $(docker ps -q --filter name=oh-agent-server)`.

## Open questions / awaiting user answer

- Resume Phase 0.3 (Medium-tier bake-off) or stay on Phase 1 hardening (add stop-conversation to smoke, cleanup automation, Canvas GUI dedicated visual test)?

## Exact next action

Wait for user direction. If Phase 0.3 resume:

```bash
cd ~/dev/openhands-ext-v1
git pull origin main
# then follow docs/PHASE-0.3-*.md
```

If Phase 1 hardening on smoke:

```bash
# add cleanup + Canvas visual assertion to test_openhands_suite_v3.py
# then re-run and confirm 5/5 still passes with new assertions
```

## Colossus state at end of session

- **openhands-app:** LIVE on :3000, image `docker.openhands.dev/openhands/openhands:latest`, mount `~/.openhands-smoke-2026-08-11/`.
- **coder:** LIVE on :8100, vLLM 0.27.0, `qwen3-coder-30b-a3b-instruct-awq-4bit`, bound `0.0.0.0`, VLLM_USE_FLASHINFER_SAMPLER=0.
- **embedder:** LIVE on :8090, llama.cpp CPU, `qwen3-embedding-4b-q8-gguf`, dim 2560.
- **UFW:** rule `ALLOW IN from 172.17.0.0/16 to any` added (ADR-0020).
- **VRAM:** ~31.4 GiB used, ~750 MiB free (coder saturating).
