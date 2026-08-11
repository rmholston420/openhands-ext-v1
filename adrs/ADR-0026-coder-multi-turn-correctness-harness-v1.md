# ADR-0026 — Coder multi-turn correctness harness v1 (Docker workspace + Perplexity-Max scored 0-100 + supersede prior verdict)

**Status:** Amended (amend 3, 2026-08-11 EDT: transport + tools + scoping + trace schema v1.1) · Ratified (scope-lock; implementation follows)
**Lock-in phase:** Phase 0.3 gate-2
**Supersedes:** planner-role-independent portion of ADR-0017 (coder scoring shape) at the medium-tier surface
**Extends:** ADR-0007 (§0.0c category 1 SDK path), ADR-0022 (Phase 0.2 task-set + gold protocol pattern), ADR-0023 (coder role assignment — re-verified post-harness)

> **STATUS AMENDMENT 3 (2026-08-11 11:30 EDT) — stage-2 wire-up corrections + trace schema v1.1 + task-10 mode**
>
> Stage-2 execution on Colossus exposed four issues that the original ADR body did not specify concretely enough to preclude. All four are corrected below without changing decisions 1–6. The bench artifact `harness_version` field bumps to **v1.1** so the scoring stage can gate on it and refuse older shapes.
>
> **1. LLM transport (host ↔ container).** `DockerWorkspace` runs the agent inside a container on Docker's default bridge. Inside the container, `127.0.0.1` is the container loopback, not the host. The runner-launched vLLM / llama.cpp servers must therefore (a) bind `0.0.0.0` (was `127.0.0.1`), and (b) be reached by the agent via the docker0 bridge gateway `172.17.0.1` (host `127.0.0.1` / `localhost` / `0.0.0.0` are rewritten in `_probe_coder_sdk` before `LLM(...)` construction). UFW rule `allow from 172.17.0.0/16 to any` from ADR-0020 is a prerequisite and is confirmed active on Colossus. Fix landed in commit `034dad6` (2026-08-11 11:10 EDT).
>
> **2. Default tool preset.** The original ADR body's canonical example showed `Agent(llm=..., tools=[])`. That silently yields only the SDK's auto-registered `finish` + `think` tools and produces an infinite Action / Error loop on any file / bash task. The harness must build tools via `openhands.tools.preset.default.get_default_tools(enable_browser=False, enable_sub_agents=False)` and assert the list is non-empty. Fix landed in commit `4c05562` (2026-08-11 11:16 EDT).
>
> **3. Scoping.** `default_tools` is built once per cell in `_probe_coder_sdk` and must be threaded into `_run_sdk_task` as a keyword argument (same pattern as the other injected SDK symbols). Fix landed in commit `8963a10` (2026-08-11 11:22 EDT).
>
> **4. Event / tool trace schema (v1 → v1.1).** The original ADR body says "capture event trace" and "extract event trace: count `ActionEvent`s, list tool names invoked in order, count `AgentErrorEvent`s." Stage-2 confirmed that this is not enough for the Perplexity-Max scoring stage: `tool_trace: list[str]` (tool names only) makes it impossible to judge whether a `file_editor` call targeted the right path or used the right operation. From v1.1, `tool_trace` is `list[dict]` where each entry contains at minimum:
>
>   - `tool` — tool name
>   - `args` — arg dict from `ActionEvent.action` (best-effort; truncated per-field to 1024 chars)
>   - `success` — `True` unless a matching `AgentErrorEvent` was emitted for this action
>   - `observation` — the corresponding `ObservationEvent`'s observation content, truncated to 2048 chars
>
> `events_tail` (last 40 events) is retained as-is. Legacy string entries are not backward-produced; scoring stage matches on `harness_version >= v1.1` before ingesting the new shape.
>
> **5. Task-10 verification mode (clarification, not change).** `coder-medium-10-implement-from-docstring` is a docstring-driven implementation task with no unique correct output. Task-set already authors it under `expected_final_state_mode: "rubric_only"` with `expected_final_state: {"/workspace/repo/src/algos.py": null}`. In `rubric_only` mode, the `null` `expected` value is a scoring-stage hint that means "extract this file's content into `final_states[path].actual` for Perplexity-Max to read and score against the rubric." The v1 harness populates `final_states` regardless of mode, so a `null` `expected` will always look like `expected != actual` if a reader checks equality without honoring `mode`. This is not a bug — the scoring stage's contract is: if `mode == "rubric_only"`, ignore `expected`, read `actual`, apply rubric. The rubric itself is `post_hoc_edit_locked` per ADR-0016 / ADR-0022. No file change; this bullet exists to prevent scoring-side misreads.
>
> **Files changed under this amendment:**
>
> - `bench/runner/probes.py` — items 1-4.
> - `bench/runner/server.py` — item 1.
> - `BUILD_LOG.md`, `DEBUG_LOG.md` — running records.
>
> **Consequences.** Scoring stage (Perplexity-Max) receives artifacts with `harness_version=v1.1` and MUST refuse to score `harness_version=v1` artifacts (they lack args / observation in `tool_trace`, so the rubric cannot be applied). Existing v1 probe artifacts under `bench/results/smoke/` are retained on disk per standing rule but are marked invalid for the coder gate in `BUILD_LOG.md`.
>
> **Lock-in phase.** Same as the parent ADR — Phase 0.3 gate-2.

> **IMPLEMENTATION NOTE (2026-08-11 10:22 EDT) — SDK 1.41.0 import path**
>
> Verified on Colossus `.venv` (Python 3.14.4): `openhands-sdk==1.41.0`, `openhands-tools==1.41.0`, `openhands-workspace==1.41.0`, `openhands-agent-server==1.41.0`, `docker==7.2.0`; Docker Server 29.6.1 healthy.
>
> In SDK 1.41.0, `DockerWorkspace` is **not** exported from `openhands.sdk.workspace` — that path only exposes the base classes (`BaseWorkspace`, `LocalWorkspace`, `RemoteWorkspace`, `Workspace`). `DockerWorkspace` lives in the separate `openhands-workspace` package at **`openhands.workspace.DockerWorkspace`** (source: `.venv/lib/python3.14/site-packages/openhands/workspace/docker/workspace.py`). The `openhands-workspace` package also exposes `APIRemoteWorkspace`, `ApptainerWorkspace`, `OpenHandsCloudWorkspace`, and a lazy `DockerDevWorkspace`.
>
> All implementation-slice references to "`openhands.sdk.workspace.DockerWorkspace`" in the original ADR body should be read as "`openhands.workspace.DockerWorkspace`." Decision 1 (workspace mechanism = DockerWorkspace) is unchanged; this is an import-path correction only.
>
> Version pin captured in `bench/runner/openhands-sdk-freeze-20260811T142200Z.txt`.

> **IMPLEMENTATION NOTE (2026-08-11 10:26 EDT) — SDK 1.41.0 real surface (locks harness shape)**
>
> Full introspection of the installed 1.41.0 packages resolves the exact surface the harness will drive. This note supersedes the original ADR body's more general wording about "Conversation loop and ActionEvent/ObservationEvent streams" with concrete method names and types. Decisions 1-6 remain unchanged; this note pins the implementation contract.
>
> **Container lifecycle (DockerWorkspace):**
>
> - `DockerWorkspace(...)` starts the `ghcr.io/openhands/agent-server:latest-python` container on construction (no `.start()` call; smoke run measured ~10.5 s cold on Colossus).
> - `ws.cleanup()` tears down the container (the container also carries `--rm` so process exit auto-removes it, but `cleanup()` is the explicit teardown).
> - `DockerWorkspace` extends `RemoteWorkspace` → `Conversation(agent=..., workspace=ws)` returns a `RemoteConversation` (factory dispatches on workspace type).
>
> **Workspace file/exec surface (inherited from `BaseWorkspace` / `RemoteWorkspace`):**
>
> - `ws.execute_command(command: str, cwd=None, timeout=30.0) -> CommandResult` — bash execution inside the container.
> - `ws.file_upload(source_path, destination_path) -> FileOperationResult` — fixture seeding (host → container).
> - `ws.file_download(source_path, destination_path) -> FileOperationResult` — final-state extraction (container → host).
> - `ws.git_diff(path)` / `ws.git_changes(path)` — state-comparison utilities.
>
> **Conversation contract:**
>
> - Canonical usage (from SDK 1.41.0 docstring at `openhands/sdk/conversation/conversation.py`):
>
>   ```python
>   agent = Agent(llm=LLM(model="...", base_url="...", api_key=SecretStr("...")), tools=[])
>   conv = Conversation(agent=agent, workspace=docker_ws, callbacks=[on_event],
>                       max_iteration_per_run=20)
>   conv.send_message(task["prompt"])
>   conv.run()
>   ```
>
> - `callbacks: list[Callable[[Event], None]]` is the event-stream capture surface. Event types imported from `openhands.sdk.event`: `ActionEvent`, `ObservationEvent` (subclass of `ObservationBaseEvent`), `MessageEvent`, `AgentErrorEvent`, `PauseEvent`. Per-task counting of `ActionEvent`s in the callback enforces the ADR-0026 stop condition "per-task turn count > 20".
> - `max_iteration_per_run` (default 500) provides an SDK-native cap; harness sets this to **20 per task** to match the ADR-0026 stop condition, so runaway loops stop inside the SDK rather than in the callback.
> - Container is **reused across all 10 tasks in a cell**; between tasks the harness wipes fixtures via `ws.execute_command("rm -rf /workspace/repo && mkdir -p /workspace/repo")` before seeding the next task's fixtures. One `DockerWorkspace()` per cell keeps startup cost amortized to ~10.5 s once, not 105 s across 10 tasks.
>
> **Fixture-seeding + verification contract per task (drives `bench/tasks/coder-medium-multi-turn.json` shape):**
>
> 1. Wipe: `ws.execute_command("rm -rf /workspace/repo && mkdir -p /workspace/repo")`.
> 2. Seed: for each `path -> content` in the task's `fixtures`, write `content` to a host tempfile, then `ws.file_upload(tempfile, path)`, then delete the tempfile.
> 3. Register callback: closure that appends `Event` objects to a per-task list.
> 4. Create `Conversation(agent=..., workspace=ws, callbacks=[cb], max_iteration_per_run=20)`.
> 5. `conv.send_message(task["prompt"])`; `conv.run()`.
> 6. Verify final state: for each `path -> expected_content` in `expected_final_state`, `ws.execute_command(f"cat {path}")` and compare to expected (whitespace-normalized diff is the default; exact-diff opt-in per task). Store both actual and expected.
> 7. Smoke test (optional per task): `ws.execute_command(task["smoke_test_command"], cwd="/workspace/repo", timeout=30)`; capture exit code + stdout/stderr.
> 8. Extract event trace: count `ActionEvent`s, list tool names invoked in order, count `AgentErrorEvent`s.
> 9. Persist per-task record in the cell JSON.
>
> **LLM adapter contract for local vLLM/llama.cpp servers:**
>
> The bench router already runs coder cells at `http://127.0.0.1:8100` (vLLM served-model-name derived from the cell id) with an OpenAI-compatible `/v1/chat/completions` endpoint. The SDK's `LLM` class supports arbitrary OpenAI-compatible endpoints via `LLM(model="openai/<served_name>", base_url="http://127.0.0.1:8100/v1", api_key=SecretStr("sk-local"))`. Sampling parameters (temperature/top_p/etc.) pass through `**kwargs` to litellm. Harness constructs one `LLM` per cell before entering the task loop.
>
> **Stop-condition mapping (concrete):**
>
> - `pip install openhands-sdk openhands-tools` failure → already satisfied (installed at 1.41.0).
> - DockerWorkspace image cannot start → already satisfied (smoke run succeeded).
> - Per-task turn count > 20 → enforced natively by `max_iteration_per_run=20`; callback also records the actual count so we can distinguish "hit the cap" from "finished cleanly".
> - Fixture cannot be seeded → `ws.file_upload(...)` raises; harness catches, records `fixture_seed_failed`, moves to next task without invoking Conversation.
>
> Task-set + gold file authoring (Consequences: files created by implementation slice) proceed on this contract.

## Context

Phase 0.2 medium-tier coder scoring used `_probe_coder_fallback` (single-turn `/v1/chat/completions` with tool_choice=auto). The fallback:

- Sends prompt + tool schemas, receives one response.
- Verifies only `expected_tool_sequence[0]` (the FIRST tool call).
- Never executes the tool. Never returns an observation. Never verifies file state.
- Scores tool selection under `bench/rubrics/medium-scored.json`, capped at ~85 because the "correctness" input is largely absent — model gets credit for calling `str_replace_editor` even if the args would produce broken code.

This produced the Phase 0.2 verdict `coder-30B-instruct-awq: 78.9 quality / 3.3s wall (tiebreak winner over 35b-a3b-q4kxl 80.9 / 6.2s)`. Wall-time tiebreak within the 3-pt band chose 30B-instruct-awq. That decision was locked in ADR-0023 for the router but flagged as ceiling-limited by the harness.

The `_probe_coder_sdk` function has been an explicit `NotImplementedError` stub since ADR-0007. Wiring it fully requires: SDK install, workspace mechanism, fixture seeding, real Conversation loop, and file-state verification. Every dimension is scope-open.

Kosmos discipline requires an ADR before this multi-surface change. This ADR locks scope for one implementation slice; a follow-up ADR files the re-verification verdict after the harness runs.

## Decision

### Decision 1 — Workspace mechanism: **DockerWorkspace (SDK default)**

The coder probe SDK path uses `openhands.sdk.Conversation` bound to a `DockerWorkspace` (SDK-provided image). Per-task fixture seeding happens inside the container before Conversation start; expected file-state verification happens by reading the container filesystem after Conversation end.

**Why:** matches the production OpenHands runtime exactly. `execute_bash` runs in the container where it belongs; no host contamination risk; container isolation makes probe idempotent across cells. Docker-in-Docker overhead is measured (~30s container startup) and budgeted per-cell.

**Rejected:** Process-based tempdir (loses production parity; execute_bash runs on host — measurement diverges from Phase 1 runtime). Hybrid (adds probe complexity for negligible speed gain because Docker-startup is per-cell not per-task if the SDK reuses one container).

### Decision 2 — Correctness definition: **Perplexity-Max scored 0-100 with tool-sequence + file-state + code-correctness inputs**

The rubric shape matches planner-medium (`bench/rubrics/medium-scored.json` — no rubric change; already covers coder role at 0-100 bands). Per-task gold files are authored in `bench/gold/coder-medium/` matching the ADR-0022 pattern:

- Existing per-task gold `.md` files remain (they carry task summaries).
- New sibling per-task `.md` files under `bench/gold/coder-medium-multi-turn/` carry the multi-turn rubric bands.
- Bands input three signals: (a) actual tool sequence vs `expected_tool_sequence`, (b) final file state vs gold reference state, (c) code correctness (does the resulting code compile/run/pass a smoke test defined in the gold).

Scoring authority: **Perplexity Max (Claude Sonnet 4.6 via Perplexity Computer)**. Self-scoring prohibited (`self_scoring_prohibited: true`). Post-hoc gold edit prohibited (`post_hoc_edit_locked: true`). Gold hashes captured in the new task-set JSON.

**Why:** highest fidelity to what "coder quality" actually means (does the model produce working code, not just call the right tool). Matches ADR-0022 pattern; no new rubric surface required. Perplexity-Max scoring authority is stable and self-scoring is already banned by rubric.

**Rejected:** File-state gold match alone (misses code correctness — model can produce valid-shaped output that's still broken). Tool-sequence + file-state only (same limitation). Deterministic scoring (would require me to write a test harness per task; higher engineering cost than authoring bands).

### Decision 3 — Prior verdict fate: **Supersede at medium-tier; ADR-0023 coder assignment re-verified post-harness**

Phase 0.2 medium-tier coder scores are tagged `harness_version=v0-single-turn-fallback` in metadata; new harness runs are tagged `harness_version=v1-multi-turn-sdk`. Router decisions (ADR-0023 coder = `qwen3-coder-30b-a3b-instruct-awq-4bit`) remain in force **until** the follow-up ADR (0027 or later) files the re-verification verdict. If the new harness produces a different ranking (i.e., 35b-a3b-q4kxl now leads outside the 3-pt tiebreak), the follow-up ADR flips or confirms.

Pre-registered reversal criteria (mirroring ADR-0024 pattern) are locked in the task-set JSON before scoring:

1. Flip coder to 35b-a3b-q4kxl if: it scores ≥85 on ALL 10 tasks AND leads 30b-instruct-awq macro-avg by >3 pts.
2. Confirm ADR-0023 coder if: 30b-instruct-awq leads macro-avg by ≥3 pts, OR 35b <70 on any 2 tasks.
3. Intermediate: confirm ADR-0023 coder + log per-task mix.

Third pool cell (`qwen3_6-27b-q6k-gguf` on coder) was dropped from coder-medium pool in Phase 0.2 for quality reasons (76.4). It is NOT re-run under v1 harness — cost vs signal doesn't justify (would need to prove 27b-q6k jumps ≥10 pts under multi-turn to matter, which is implausible given its single-turn quality was already lowest).

**Why:** clean supersede at the harness boundary; existing router keeps working during transition; pre-registered reversal criteria prevent post-hoc bias exactly as with the planner probe.

**Rejected:** Amend-not-supersede (creates two coexisting quality scores — confusing for downstream ADRs). Phase-0.3+-only (leaves the 78.9 number in the record as authoritative even though the harness is known-ceiling-limited).

### Decision 4 — Task set: **Reuse `bench/tasks/coder-medium.json` unchanged; add `bench/tasks/coder-medium-multi-turn.json` for multi-turn re-eval**

The 10 tasks in `coder-medium.json` are appropriate for the new harness. They already carry `fixtures` (workspace seed files), `expected_tool_sequence` (multi-step, e.g. `['read_file', 'str_replace_editor']`), and prompts that require file changes. `coder-medium.json` is `post_hoc_edit_locked` so we do NOT edit it. Instead:

- New file `bench/tasks/coder-medium-multi-turn.json` copies the 10 tasks from coder-medium.json, adds per-task `expected_final_state` (path → content for verification), adds per-task `smoke_test_command` (optional bash command to run inside the container to verify functional correctness — e.g. `python -m pytest test_foo.py` or `python -c "import mymod; assert mymod.f() == 42"`), and updates `gold_dir` to `bench/gold/coder-medium-multi-turn/`.
- New 10 gold files under `bench/gold/coder-medium-multi-turn/` carry per-task 0-100 rubric bands with the three-input scoring shape from Decision 2.
- Gold SHA-256 hashes recorded in the new task-set JSON `#/gold_hashes`.

**Why:** matches ADR-0022 pattern (post-hoc-edit lock on existing task-set; new versioned file for new harness). Reuses proven tasks. Adds only the new verification surfaces.

**Rejected:** Editing coder-medium.json in place (violates post_hoc_edit_locked). Authoring 10 net-new tasks (unnecessary; the existing 10 already exercise the tool sequences the multi-turn harness is designed to measure).

### Decision 5 — SDK version pin and dependency management

- SDK: `openhands-sdk` and `openhands-tools` pinned to a specific version tag (to be captured in `bench/runner/candidates.py` metadata + `run_metadata.openhands_sdk_version`). Version selection happens at first install; ADR-0007 already flags the general dependency but does not pin.
- Installed into the runner venv `~/dev/openhands-ext-v1/.oh-venv` (Colossus venv, per user's environment discipline). NOT into a new venv.
- Docker image: whatever `DockerWorkspace` default uses at install time. Image tag captured in `run_metadata.docker_image` per run.

**Why:** matches existing Colossus venv discipline (do not create parallel venvs for one-off work). Pin captured in metadata for reproducibility.

**Rejected:** Isolated venv (violates single-venv discipline). Pinning to older/newer than what SDK default installs (introduces bugs we don't own).

### Decision 6 — Co-residency and runtime envelope

Multi-turn harness cells run under the same sequential-block co-residency protocol as ADR-0022 Decision 4: **coder OR planner, not both**; **embedder CPU-resident throughout**. DockerWorkspace container runs on host (not GPU); the coder model itself runs on GPU via vLLM at :8100 as usual. Per-cell overhead estimate:

- vLLM startup: ~60s
- DockerWorkspace startup: ~30s
- Per-task turn (10 tasks × ~3-5 turns × ~10s): ~5-15 min
- Teardown: ~10s
- **Total per cell: ~6-17 min** (vs Phase 0.2 single-turn ~2 min per cell)

Two cells → ~12-34 min total wall (well within the "hour or two" budget for a single re-eval).

**Why:** matches existing co-residency ADR; makes the wall envelope predictable so I don't propose the wrong runbook when it's time to execute.

## Rationale

**Why now, not later.** Phase 0.3 gate-2 is the correct place: gate-1 locked role assignments given the harness limitation, gate-2 verifies that lock against a real harness before Phase 1 wiring. Wiring the router at Phase 1 against a known-ceiling-limited coder score would bake the ceiling into Phase 1 baselines and make future harness upgrades disruptive.

**Why Docker over process-based.** The v1 harness is the reference for all future coder runs. Getting production-parity right at v1 is worth the ~30s startup overhead per cell. If future runs need to test on multiple SDK versions or workspace configurations, that's a v2 concern, not v1.

**Why Perplexity-Max scored bands over deterministic pass/fail.** File-state gold match is brittle — a valid one-line diff in whitespace kills the test. Smoke-test-based scoring is stronger but still binary. 0-100 bands with three inputs (tool sequence, file state, code correctness) capture the actual quality gradient the router will select on. Matches proven planner-medium pattern.

**Why supersede rather than amend.** Two competing quality numbers for the same role is a maintenance liability. The v0 fallback is known-ceiling-limited; the v1 result is what future Phase 1 baselines should reference. Keep v0 numbers accessible in the archive (via git history) but not in the live rubric or router.

**Why not re-run 27b-q6k.** Its Phase 0.2 single-turn quality was already the lowest of the pool (76.4). Multi-turn typically compresses the gap between models rather than reordering them dramatically. Not worth the ~10 min of cell time.

## Consequences

- **Files created by implementation slice:**
  - `bench/tasks/coder-medium-multi-turn.json` (net-new; 10 tasks + gold_hashes + reversal_criteria)
  - `bench/gold/coder-medium-multi-turn/coder-medium-*.md` × 10 (net-new; per-task 0-100 rubric bands with three-input scoring shape)
  - `bench/runner/probes.py` — `_probe_coder_sdk` promoted from stub to full implementation
  - `.oh-venv` — `openhands-sdk` + `openhands-tools` installed (captured in `pip freeze` snapshot at `bench/runner/openhands-sdk-freeze-<ts>.txt`)

- **Files modified by implementation slice:**
  - `bench/runner/candidates.py` — SDK version pin surfaces in `run_metadata`
  - `bench/schema/run.py` + `run.schema.json` — new fields `harness_version`, `openhands_sdk_version`, `docker_image` on `run_metadata`

- **Not touched:**
  - `bench/tasks/coder-medium.json` (`post_hoc_edit_locked`)
  - `bench/gold/coder-medium/*.md` (`post_hoc_edit_locked`)
  - `bench/rubrics/medium-scored.json` (rubric shape already covers 0-100 coder scoring)
  - `bench/candidates/coder-medium-pool.json` (same 2-cell pool; 27b-q6k stays out)
  - Router config (waits for follow-up ADR verdict)

- **Follow-up ADR expected:** ADR-0027 (or later) files the multi-turn verdict against the pre-registered reversal criteria in the task-set JSON. Confirms or supersedes ADR-0023 coder row.

- **Stop conditions for the implementation slice:**
  - If `pip install openhands-sdk openhands-tools` in `.oh-venv` fails or requires a Python version outside the current 3.14 venv → stop, escalate.
  - If SDK's DockerWorkspace image cannot start on Colossus Docker → stop, escalate.
  - If per-task turn count on any candidate exceeds 20 (indicates the harness is looping) → stop, cap and log per-task, but do not silently accept — flag for follow-up.
  - If verification reveals a task's fixtures cannot be seeded (e.g., path outside container writable area) → stop, fix in task-set with a fresh ADR amendment.

## Lock-in phase

Phase 0.3 gate-2. This ADR locks harness scope. Implementation and re-verification verdict are separate commits, each with their own BUILD_LOG entries. Follow-up ADR (0027+) files the verdict.

## References

- ADR-0007 (§0.0c category 1 SDK path — this ADR promotes the stub)
- ADR-0016 (medium-tier scoring rubric — reused unchanged)
- ADR-0022 (Phase 0.2 task-set + gold protocol pattern — mirrored)
- ADR-0023 (Phase 0.3 router-selection — coder assignment awaits re-verification)
- ADR-0024 (planner migration-ordering probe — pre-registered reversal pattern reused)
- ADR-0025 (planner probe verdict — confirms the reversal-criteria pattern works)
- `bench/tasks/coder-medium.json` (existing 10 tasks; source for new multi-turn task-set)
- `bench/runner/probes.py:418` (`_probe_coder_sdk` stub — target of this ADR)
