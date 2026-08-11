# ADR-0015 — Planner Medium-tier `thinker-2507-awq` budget-hypothesis probe (pre-registered)

**Status:** Proposed (evidence pending)
**Lock-in phase:** Phase 0.2 (Medium tier authoring) — no Medium-tier code paths land until this probe resolves.
**Supersedes:** —

## Context

At Fast tier (2026-08-11 rescore) `qwen3-30b-a3b-thinking-2507-awq` was legitimately eliminated from the **planner** pool on rubric R2 (>1 malformed) despite passing every coder task. The Fast-tier task set carries `chat_template_kwargs.enable_thinking=false` and `budget_tokens=4096` (ratified in ADR-0008 and ADR-0009 respectively).

Two competing hypotheses explain the elimination:

- **H0 (structural refusal):** the Thinking-2507 checkpoint cannot honor `enable_thinking=false`. Its instruction-tuning treats the `<think>` block as mandatory; the `enable_thinking` chat-template flag is only a router hint at inference time, not a training-time constraint. Under H0, no completion budget makes the planner cell viable.
- **H1 (budget-bound):** the model *does* honor `enable_thinking=false` but writes an internal reasoning block anyway that consumes most of 4096 tokens, leaving no room for the schema-conformant JSON tail. Under H1, a higher completion budget allows the JSON to emit.

Neither can be settled from Fast-tier evidence alone because the Fast-tier budget is fixed. This ADR pre-registers the probe and its success criteria so we cannot move the goalposts once evidence lands.

## Decision

Run a two-step, sequential budget-hypothesis probe on **exactly the three Fast-tier planner prompts** with the following variations, in this order:

1. **Probe A:** `budget_tokens=8192`. All other parameters identical to `bench/tasks/planner-fast.json`.
2. **Probe B:** `budget_tokens=16384`. Only run if Probe A does NOT falsify H0.

Files:

- `bench/tasks/planner-medium-thinker-probe-b8k.json` (Probe A task set)
- `bench/tasks/planner-medium-thinker-probe-b16k.json` (Probe B task set)
- `bench/candidates/planner-medium-thinker-probe.json` (single-cell candidate, role=planner)

The probe runs under `--tier fast --smoke` because:

- `--smoke` bypasses the §0.0b open-pool guard (probe is 1-cell diagnostic, not a pool run).
- `--tier fast` reuses the existing rubric/harness plumbing; the Medium-tier code path does not yet exist. Result JSONs are tagged `smoke=true` — they are NOT admissible as pool-decision evidence, only as probe evidence for this ADR.

## Pre-registered success criteria (immutable after this ADR is committed)

**Falsified — thinker-2507-awq is viable at Medium-tier planner ("H1 wins"):**
All three of the following must hold on Probe A or Probe B:
1. `malformed_count ≤ 1` (of 3 tasks) per rubric R2's non-eliminating threshold.
2. `median(wall_seconds) ≤ 60` across the 3 tasks. Absolute SLO; the ratified rubric R3 is relative and does not apply to a 1-cell probe.
3. Of the ≥ 2 valid completions, all conform to the planner `output_schema` (min_steps met, ids match `^s[0-9]+$`, deps form a DAG referencing only earlier ids).

**Confirmed — thinker-2507-awq is unfit for planner role ("H0 wins"):**
At least one of:
- `malformed_count ≥ 2` on BOTH Probe A and Probe B (structural failure survives budget expansion), OR
- `median(wall_seconds) > 60` on any probe (latency SLO fail even with valid JSON; not viable on the request fast path).

**No verdict — retry required:** Any probe run whose result JSON is missing a `.probe.json` sidecar, is truncated, or where the harness records a launch failure. Re-run the same probe; do not draw a verdict from incomplete data.

## Rationale

- **Two budgets, not one, and sequential.** A single budget cannot distinguish "8k too small, 16k enough" from "no budget helps". Two data points bracket the answer. Sequential ordering saves ~10 min of cold-start time when Probe A already answers the question (either direction).
- **Reuse Fast-tier prompts verbatim.** Any prompt change confounds the budget variable with the task variable. Identical prompts + only budget varies = clean isolation.
- **60s absolute SLO.** Fast-tier planner survivors (27B Q6_K, 35B Q4_K_XL, both llama.cpp/gpu) run structural-JSON under 10s per task. 60s is a 6× ceiling — the router would never pick a slower cell over one of the survivors even if quality tied. Anything worse is SLO-hostile at Medium tier where planner is on the request fast path.
- **Pre-registration.** Post-hoc criterion tuning was the failure mode that produced the two reversed coder eliminations under ADR-0014. This ADR fixes the criteria BEFORE evidence lands, so the verdict is forced by the data.
- **`--smoke` tagging.** The probe is diagnostic. Even if Probe A shows all-pass with fast latency, we do NOT admit the result JSON into the planner-fast pool retroactively. The Fast-tier pool is locked; this probe informs Phase 0.2 Medium-tier authoring only.

## Alternatives considered

- **Give up and exclude thinker from planner Medium-tier by default.** Rejected: the model has genuine reasoning strength (5/5 coder pass). If a small budget change unlocks it for planner too, that's a real capability we shouldn't strand on an untested assumption.
- **Run 3 budgets (4k, 8k, 16k) in parallel.** Rejected: 4k is already known-failed from Fast-tier evidence. Parallelism costs ~3× VRAM contention or ~3× wall time on a single 5090; no decision-relevant information gained.
- **Change prompts to shorter/simpler tasks.** Rejected: confounds the budget variable with prompt difficulty. If shorter prompts succeed we still don't know whether it was budget or prompt.

## Consequences

- Two new task-set files, one new single-cell candidate file, one new ADR — no changes to `bench/runner/`, `bench/rubrics/`, or the planner-fast pool.
- One BUILD_LOG entry filing this ADR.
- After probe evidence lands, ADR-0015 is amended with **Ratified** status and either:
  - a **Falsified** verdict, adding thinker-2507-awq to `bench/candidates/planner-medium-pool.json` when it is authored in Phase 0.2, OR
  - a **Confirmed** verdict, excluding thinker-2507-awq from the planner Medium-tier pool with the recorded latency/malformed evidence.
- Registry entry `qwen3-30b-a3b-thinking-2507-awq` retains its dual-role marker either way (Fast-tier coder viability is unchanged).
- No spec (`Kosmos-Build-Spec-v25.md`, `Kosmos-Build-Sequence-v25.md`) surfaces change; nothing in `PORTING_LEDGER.md` changes.

## Run commands (for the human operator on Colossus)

```bash
# Probe A: 8k budget
.venv/bin/python scripts/benchmark-tier-runner.py --tier fast --role planner \
  --task-set bench/tasks/planner-medium-thinker-probe-b8k.json \
  --rubric bench/rubrics/fast-elimination.json \
  --candidate-file bench/candidates/planner-medium-thinker-probe.json --smoke

# Only if Probe A does NOT satisfy the Falsified criterion:
# Probe B: 16k budget
.venv/bin/python scripts/benchmark-tier-runner.py --tier fast --role planner \
  --task-set bench/tasks/planner-medium-thinker-probe-b16k.json \
  --rubric bench/rubrics/fast-elimination.json \
  --candidate-file bench/candidates/planner-medium-thinker-probe.json --smoke
```

Inspect raw content (both to size follow-ups and to diagnose failure modes):

```bash
python3 scripts/inspect-raw-content.py bench/results/*thinker-2507-awq*b8k*.probe.json
```

## References

- ADR-0008 — Fast-tier disables thinking mode (defines `enable_thinking=false` for planner).
- ADR-0009 — Fast-tier planner guided decoding.
- ADR-0012 — Registry: 30B thinker is dual-role coder+planner.
- ADR-0014 — Coder-fast pool reinstates R2-warning survivors (motivates pre-registration discipline).
- `bench/rubrics/fast-elimination.json` — R2 threshold ">1 malformed", R3 relative-latency.
- `bench/tasks/planner-fast.json` — source prompts (unchanged, reused verbatim).
