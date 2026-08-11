# OpenHands-Ext v1 — Session Handoff — 2026-08-11 02:10 EDT

## Current build-sequencing position

- **Phase:** 0.1 — Fast-tier (30 min) triage & infeasibility elimination
- **Component:** `bench/runner/` package + `scripts/benchmark-tier-runner.py`
- **Ports touched:** none (harness code)

## Completed this session

- ADR-0007 filed + Fast-tier task JSONs + elimination rubric (commit `66b859c`).
- Registry sizes calibrated against `models/manifest.json`.
- `scripts/pull-models.sh` progress-ticker.
- Progress-visibility discipline (ADR-0007 §7) added to runner scaffold docstring.
- **Runner design revised (this turn):** switched from separate `bench/launchers/*.sh` scripts to inline Popen supervision in Python. Removed the four launcher drafts.
- **`bench/runner/` package written and dry-run-verified:**
  - `progress.py` — line-buffered `[i/N]` printer with heartbeat context-manager
  - `server.py` — `VLLMServer` + `LlamaCppServer` Popen supervisors with stdout tee, `atexit`/SIGINT/SIGTERM cleanup, structured `ServerLaunchError`
  - `nvml.py` — background pynvml sampler with coverage tracking
  - `probes.py` — planner (JSON + DAG), embedder (cosine probes), coder (fallback tool-call; SDK path stubbed)
  - `candidates.py` — registry × manifest expansion + oversize filter + embedder GPU/CPU matrix
  - `main.py` — end-to-end orchestration, guards, rubric R1-R4 application, schema-validated writes
- `bench/tasks/README.md` — task-set JSON contract doc.
- `scripts/benchmark-tier-runner.py` rewritten as thin CLI shim.
- Sandbox-local dry-run passes for planner (5), coder (4), embedder (8). Guard §0.0a fires exit=2 on planner without `--rubric`.

## Remaining before current Definition of Done (Phase 0.1)

1. **Pull this commit on Colossus** (`cd ~/dev/openhands-ext-v1 && git pull`).
2. **Install `openhands-sdk` + `openhands-tools`** into the runner venv so `_probe_coder_sdk` can replace its `NotImplementedError` with a real Conversation loop + DockerWorkspace. Until then coder cells run in fallback mode and are tagged `degraded: openhands-sdk unavailable`.
3. **Materialize `.versions/llama.cpp` and `.versions/vllm`** (or accept them via CLI flags) so `run_metadata.llama_cpp_build_tag` / `vllm_release_tag` are populated.
4. **First real (non-`--dry-run`) planner invocation on Colossus** — smallest of the pool first (`qwen3-30b-a3b-thinking-2507-awq`, ~18 GiB) to confirm the launch/probe loop end-to-end before running the full role.
5. Iterate through coder (fallback), planner, embedder Fast-tier cells; produce elimination report.

## Open questions / awaiting user answer

- None. Design confirmed (Q1 Full SDK / Q2 raw for planner+embedder / Q3 revised to inline Popen supervision after re-examination).
- `_probe_coder_sdk` will be filled in as a follow-on commit once `openhands-sdk` is confirmed installed on Colossus. Recommend that as the very next slice.

## Exact next action

On Colossus:

```
cd ~/dev/openhands-ext-v1
git pull
# Confirm the runner package imports cleanly
python -c "from bench.runner.main import run_tier; print('ok')"
# Dry-run to confirm end-to-end schema validation on your box:
python scripts/benchmark-tier-runner.py --tier fast --role planner \
  --task-set bench/tasks/planner-fast.json \
  --rubric bench/rubrics/fast-elimination.json --dry-run
```

Then decide whether to (a) install `openhands-sdk` first and finish the SDK path, or (b) run the fallback coder probe now and defer the SDK integration to Phase 0.2.
