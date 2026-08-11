# Kosmos Session Handoff — 2026-08-11 01:52 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0.1 (Fast tier) — pre-execution methodology lock-in complete.
- **Plugin / kernel component:** Bench harness (`scripts/benchmark-tier-runner.py`), Fast-tier task files, elimination rubric.
- **Port(s) in progress:** None (Phase 0 pre-tier work is authored code, not vendored ports).

## Completed this session

- Coder pool (5 candidates, 25m41s) and planner pool (1 new candidate, 3m14s) downloaded to Colossus with pinned HF revisions in `models/manifest.json`.
- `bench/candidates/registry.json` `approx_size_gib` values calibrated from measured manifest sizes (deltas: int4-autoround +4, 35B-A3B-Q4KXL +2, 35B-A3B-AWQ +5, thinking-2507-AWQ −2).
- Filed **ADR-0007** — Fast-tier task authoring, sampling, and elimination-rubric methodology (Ratified). Resolves skill/spec sampling and scoring conflicts; ratifies a project-wide progress-visibility discipline for all harness scripts.
- Wrote `bench/tasks/coder-fast.json` (5 tool-call probes), `bench/tasks/planner-fast.json` (3 structured-plan prompts with JSON schema), `bench/tasks/embedder-fast.json` (8 fixed queries).
- Wrote `bench/rubrics/fast-elimination.json` (timestamped, `scoring.enabled=false`).
- Added `[i/N]` counter, per-candidate elapsed, and cumulative batch elapsed to `scripts/pull-models.sh`.
- Added progress-visibility guard clause (#8) to `scripts/benchmark-tier-runner.py` docstring so the constraint travels with the file.
- Appended three BUILD_LOG entries (coder+planner pull, registry calibration, ADR-0007 + task/rubric authoring).

## Remaining before current Definition of Done

Phase 0.1 pre-execution scaffolding is complete. To actually run the Fast tier we still need:

1. Real serving implementation in `scripts/benchmark-tier-runner.py` — replace `build_dry_run_record` placeholder with:
   - vLLM launcher: `docker rm -f vllm-bench`, `docker run` per candidate, wait for `/v1/models` (per `local-llm-bench` vLLM launcher pattern).
   - llama.cpp launcher: `./llama.cpp/llama-server -m <path> --host 127.0.0.1 --port 8082 -ngl 999 -c 32768 -fa on --cache-type-k q8_0 --cache-type-v q8_0 --jinja --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0` (spec §0.1 uniform sampling).
   - Task loader consuming `bench/tasks/{coder,planner,embedder}-fast.json`.
   - Elimination-rubric enforcement per `bench/rubrics/fast-elimination.json` rules R1–R4.
   - Progress-visibility per ADR-0007 §7 and runner-docstring Guard #8: line-buffered timestamped output, `[i/N]` counters, per-phase bookends, elapsed heartbeat on any phase > ~15 s.
2. NVML sampler wiring for Category 3 (GPU envelope) and Category 4 (CPU envelope for embedder CPU cells) — must exist before any Fast-tier scored/eliminated run per spec §0.0c category 3.
3. AVX-512 detection for embedder CPU-vLLM cell (spec §0.0b known-constraint gate).

## Open questions / awaiting user answer

None. User approved all clarifying-question answers and (A)/(A) task-material choices; user also requested the project-wide progress-visibility preference which is now saved to memory and ratified in ADR-0007 §7.

## Exact next action

`git add -A && git status` at `/tmp/oh-ext`, then confirm the push with the user, then push to `origin/main` via `api_credentials=["github"]`. Contents of this commit: ADR-0007, ADR index update, registry calibration, three task JSONs, one rubric JSON, pull-models.sh progress ticker, benchmark-tier-runner.py docstring update, three BUILD_LOG appends, and this SESSION_HANDOFF overwrite.
