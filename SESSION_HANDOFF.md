# SESSION_HANDOFF — 2026-08-11 12:24 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.3 gate-3 (coder Full-tier re-eval)
- **Plugin / kernel component:** bench harness (multi-turn) · coder role
- **Port(s) in progress:** none (bench-only)
- **Governing ADR:** ADR-0028 (Ratified 2026-08-11 12:05 EDT · amended 2026-08-11 12:17 EDT for F05 runner-constraint swap)

## Completed this session
- ADR-0027 (gate-2 verdict: CONFIRM AWQ) authored and Ratified; commit `af732e2` pushed.
- ADR-0028 gate-3 opener + Full-tier task-set scaffold committed; commit `cffda04` pushed.
- Gate-3 fixture lock-in (`27d4869`): populated 10 fixtures, authored 10 gold rubric files, `bench/rubrics/full-scored.json` (adds `-10` deduction for FinishAction omission on report-style tasks), 2 candidate cell files, pinned docker SHA digest.
- **F05 amendment (`b676755`):** ADR-0028 amended; F05 class swapped from "git status + git log summary" (unrunnable — required `fixture_setup_command` hook that `bench/runner/probes.py` does not honor) to "JSON config schema report" (runner-friendly, report-style class preserved, finish-action clause in reversal criteria preserved).
- **Runner verified end-to-end against source (this session):** entrypoint, port assignments, coder branching, per-task-field honoring, rubric lock guard, docker transport, candidate JSON shape — all confirmed by direct source read.

## Remaining before current Definition of Done
Gate-3 DoD steps 5–7 (from ADR-0028 §Sub-decision 5):
5. Execute probe runs — one run per candidate on the 10-task set.
6. Score all 20 (2 candidates × 10 tasks) via Perplexity Max against `bench/gold/coder-full-multi-turn/*.md`. Compute per-task scores + macro. Mechanically apply reversal criteria (no post-hoc reinterpretation).
7. Author verdict ADR-0029 (CONFIRM AWQ / FLIP to 35b / INTERMEDIATE + log per-task mix), update `adrs/README.md`, append BUILD_LOG, overwrite SESSION_HANDOFF.

## Open questions / awaiting user answer
- **None.** All fixture-lock choices made; F05 amendment applied; docker digest pinned; reversal criteria + post-hoc lock in place; runner verified.

## Exact next action

**Pre-flight sequence (STOP if any check fails):**

```bash
cd ~/dev/openhands-ext-v1 && git pull --ff-only

# 1. Verify openhands-sdk is installed and matches task-set expected version.
#    If this fails, ALL coder tasks silently degrade to single-turn tool-call
#    fallback (no Docker workspace, no FinishAction available) — same failure
#    mode as gate-2 stage-2. Task set expects openhands_sdk_version 1.41.0.
.venv/bin/python -c "import openhands.sdk; from importlib.metadata import version; print('openhands-sdk', version('openhands-sdk'))"
.venv/bin/python -c "from openhands.sdk import Agent, Conversation, LLM; from openhands.sdk.event import ActionEvent, AgentErrorEvent, MessageEvent, ObservationEvent; from openhands.tools.preset.default import get_default_tools; from openhands.workspace import DockerWorkspace; print('SDK imports OK')"

# 2. Verify Docker daemon is up (SDK boots container per cell).
docker version --format '{{.Server.Version}}'

# 3. Verify docker0 bridge IP is 172.17.0.1 (SDK path rewrites 127.0.0.1 to
#    172.17.0.1 to reach host-bound vLLM/llama.cpp from container). If a
#    non-stock docker0 gateway, the container cannot reach the LLM.
ip -4 addr show docker0 | grep -oP 'inet \K[0-9.]+' || echo 'MISSING docker0 - install docker or start service'

# 4. Pre-pull the container image at the pinned digest.
docker pull ghcr.io/openhands/agent-server@sha256:117d4bcc95e19f306b9158fce1dce8c35808379663289407b60ef5357aa7aa79

# 5. Stop any pre-existing servers on runner-managed ports.
sudo systemctl stop vllm@coder 2>/dev/null || true
pkill -f 'vllm.*--port 8501' 2>/dev/null || true
pkill -f 'llama-server.*--port 8082' 2>/dev/null || true
(ss -ltn | grep -E ':(8501|8082) ' && echo 'PORT STILL OCCUPIED - STOP') || echo 'ports 8501+8082 free'

# 6. Dry-run to validate schema-conformant scaffold before real launch.
.venv/bin/python scripts/benchmark-tier-runner.py \
  --tier full --role coder \
  --task-set bench/tasks/coder-full-multi-turn.json \
  --candidate-file bench/candidates/coder-full-awq.json \
  --rubric bench/rubrics/full-scored.json \
  --dry-run
```

**Only if all six pre-flight checks pass, fire real probes:**

```bash
# Candidate A - AWQ (vLLM, :8501, runner-launched)
.venv/bin/python scripts/benchmark-tier-runner.py \
  --tier full --role coder \
  --task-set bench/tasks/coder-full-multi-turn.json \
  --candidate-file bench/candidates/coder-full-awq.json \
  --rubric bench/rubrics/full-scored.json \
  --vllm-release v0.27.0

# Candidate B - 35b (llama.cpp, :8082, runner-launched)
.venv/bin/python scripts/benchmark-tier-runner.py \
  --tier full --role coder \
  --task-set bench/tasks/coder-full-multi-turn.json \
  --candidate-file bench/candidates/coder-full-35b.json \
  --rubric bench/rubrics/full-scored.json \
  --llama-cpp-build b10356
```

**Immediate check after each candidate finishes:**

```bash
latest=$(ls -t bench/results/phase-0-full-coder-*.json | head -1)
python3 -c "import json; d=json.load(open('$latest')); m=d['run_metadata']; print('notes:', m.get('notes')); print('sdk_version:', m.get('openhands_sdk_version')); print('docker_image:', m.get('docker_image'))"
```

If `notes` contains 'degraded' OR `openhands_sdk_version` is null OR `docker_image` is null, **STOP** — the SDK path did not execute. Do not proceed to scoring.

Results land in `bench/results/` as `phase-0-full-coder-*.json` (metadata) + `.probe.json` (per-task tool_trace). Dump traces per the `local-llm-bench` skill scoring protocol and paste back for Perplexity-Max scoring against `bench/gold/coder-full-multi-turn/*.md`.

## Runner-behavior notes (verified against source 2026-08-11 12:24 EDT)

Read directly from `bench/runner/main.py` and `bench/runner/probes.py`. All bullets confirmed by grep + read.

- **Runner entrypoint:** `scripts/benchmark-tier-runner.py` calls `bench.runner.main.run_tier`. It launches its own servers (`bench.runner.server.VLLMServer` or `LlamaCppServer`) at coder :8501 (vLLM) / :8082 (llama.cpp) per the `PORTS` map at `bench/runner/main.py:85-91`. Do NOT pre-start servers.
- **Coder probe branching:** `probe_coder` (`bench/runner/probes.py:374`) tries `_probe_coder_sdk` first; falls back to `_probe_coder_fallback` on `ImportError` or `NotImplementedError` (lines 400-406). The fallback is single-turn `/v1/chat/completions` with a fixed 4-tool schema (`read_file`, `str_replace_editor`, `execute_bash`, `write_file`) and NO `finish` tool. **If the SDK is unavailable, FinishAction cannot be emitted and every report-style task auto-fires reversal rule 2 clause 3.** Pre-flight step 1 catches this.
- **Runner-honored per-task fields:** `fixtures` (files uploaded to container), `expected_final_state` (dict path->content, runner cats each), `expected_final_state_mode` (`no_changes_expected` triggers modified coarse_pass; anything else falls through to default), `smoke_test_command` (executed, exit_code + stdout/stderr recorded).
- **`expected_final_state_mode: rubric_only_with_immutable_check`** is a scorer-only semantic. The runner accepts it (falls through to `rubric_only` coarse_pass logic). The immutable-check (files must be byte-identical) is enforced by the Perplexity-Max scoring pass reading `final_states` from the artifact, not by the runner.
- **`fixture_setup_command`** is NOT honored (grep confirmed no reference in `bench/runner/`). The only pre-run setup hook is the hard-coded `$note` sentinel for `tid == "coder-medium-08-check-git-status"` in `bench/runner/probes.py:594` — no generalization. F05 amendment (JSON config schema) uses plain fixtures only.
- **`docker_image_digest_expected`** is NOT verified by the runner (grep confirmed). It is documentation-only. Pre-flight step 4 pre-pulls at the digest so the tag `:latest-python` resolves to the pinned digest for this run.
- **Container transport:** SDK path rewrites loopback endpoints to `172.17.0.1` (docker0 bridge) so the container can reach the host-bound LLM (`bench/runner/probes.py:498-510`, ADR-0026 amendment 3). Pre-flight step 3 verifies this bridge exists.
- **Rubric lock guard:** `_load_rubric` (line 149) falls back to `authored_utc` when `locked_at_utc` is absent. `full-scored.json` has `authored_utc: 2026-08-11T16:03:00Z` (12:03 EDT); guard passes for any run started after 12:03 EDT.
- **`task_set.identity` is derived from `f"{role.value}-{tier.value}"` (line 685)** — the runner stamps `"coder-full"` regardless of what the source JSON says. Do not rely on `identity` to prove which task file was used.

## Known-not-blocking observations
- Gate-2 stage-2 coder runs on record all show `notes: "degraded: sdk path stubbed (OpenHands SDK coder path not yet implemented ... use fallback)"`. That message is baked in from an older `_probe_coder_sdk` stub that was replaced in commit `933fd9d` ("Phase 0.3 gate-2: extend run schema + implement _probe_coder_sdk"). The current source raises `NotImplementedError` only if `openhands.sdk.event` / `openhands.tools.preset.default` / `openhands.workspace` fail to import. **The ADR-0027 CONFIRM AWQ verdict was made against fallback-path outputs, not the multi-turn Docker path.** Not this session's problem, but be aware if the Full-tier verdict lands differently than gate-2.
- vLLM AWQ candidate carries `tool_call_parser: qwen3_coder` (correct; propagates via `extra_flags` at `main.py:460`). Reasoning parser is unset (correct; coder is non-thinking). 35b llama.cpp uses `-ngl 999` (correct for GPU device).
