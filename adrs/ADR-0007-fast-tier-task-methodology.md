# ADR-0007 — Fast-tier task authoring, sampling, and elimination-rubric methodology

**Status:** Ratified
**Lock-in phase:** Phase 0.1 (Fast tier)
**Supersedes:** —

## Context

`docs/specs/integration-execution-plan-v16.md` §0.1 defines Fast-tier counts
(coder 3–5 tasks/candidate, planner 2–3 tasks/candidate, embedder 1 query set
of 5–10 queries/matrix cell) and its intent ("rough tool-call validity",
"completes without truncating at 4096 tokens; rough plan coherence", "cell
launches at all; rough latency; non-degenerate vectors"). It does **not**
enumerate specific task IDs, prompt text, JSON schemas, or elimination-rubric
thresholds.

Task selection at Fast tier is load-bearing: Medium and Full tiers inherit
Fast-tier eliminations by definition, and later tiers scale up from the same
task-authoring conventions. Silent drift here corrupts later stages.

The `local-llm-bench` user skill (Path D v2, F.19-pre) prescribes a canonical
harness pattern already in use across Kosmos benches; adopting it here keeps
methodology aligned across projects. Two skill/spec conflicts must be resolved
in-scope:

1. Skill uses per-role Qwen sampling presets sent per-request. Spec §0.1
   llama.cpp launch command sets sampling at server-launch time
   (`--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0`), matching the skill's
   **planner** preset only.
2. Skill's canonical scoring layer (Perplexity-gold-standard) applies to
   quality ranking. Spec §0.1 explicitly forbids ranked scoring at Fast tier:
   Fast tier performs elimination only.

## Decision

### 1. Task authoring conventions

- Prompts/inputs live on disk under `bench/tasks/{coder,planner,embedder}-fast.json`.
  Never embed prompt text in harness scripts.
- Task files are JSON documents with schema-versioned envelopes, tier-tagged,
  and timestamped at commit time.
- Each task carries a deterministic pass/fail probe (see per-role details
  below) — no free-form scoring at Fast tier.

### 2. Task counts and material

- **Coder — 5 tasks, synthetic OpenHands tool-call probes.** Exercise
  `read_file`, `str_replace_editor`, `execute_bash`, `write_file`, and a
  short delegate/subtask chain. Each task hard-codes an expected
  tool-invocation sequence; pass = observed sequence matches expected within
  tolerance (order preserved, no forbidden tools called). Real SWE-bench
  belongs at Full tier (spec §0.3, "SWE-bench-Verified subset (or full 500)")
  — Fast tier is triage.
- **Planner — 3 structured-plan prompts with a fixed JSON schema.** Each
  prompt describes a small realistic Forge-OH-style task and requests a
  plan in a fixed JSON shape (`{steps: [{id, desc, deps: [id...]}]}`). Pass
  = valid JSON, matches schema, dependency graph is a DAG, no truncation at
  4096-token budget.
- **Embedder — 8 fixed queries.** Includes identical-input pair (must
  produce identical vectors), orthogonal-pair (must produce non-degenerate
  cosine distance), and 6 realistic Forge-OH trajectory-record snippets.
  Pass = launches, all 8 vectors non-null, identical-pair cosine ≥ 0.999,
  orthogonal-pair cosine ≤ 0.9 (rules out degenerate output).

### 3. Sampling policy

- **llama.cpp cells:** launch flags set uniformly to spec's Fast-tier values
  (`--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0`). This is the skill's
  planner preset; using it uniformly at Fast tier is a spec-driven trade-off
  (llama.cpp cannot vary sampling per-request at Fast-tier launch cadence).
- **vLLM cells:** per-role Qwen presets sent as OpenAI-compatible request
  params. Coder = `temperature=0.7, top_p=0.8, top_k=20, min_p=0.0,
  presence_penalty=1.0, repetition_penalty=1.05`. Planner/thinking =
  `temperature=0.6, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.0`.
- `<think>...</think>` blocks stripped before any probe check.
- Greedy decoding forbidden on thinking-mode cells (Qwen model-card warning).

### 4. Elimination rubric (single file, all three roles)

`bench/rubrics/fast-elimination.json` — timestamped at commit, no post-hoc
edits per spec §0.0a. Rules apply directly to Category-1/Category-2/Category-3
schema fields:

- **Launch failure:** any candidate that fails to bring up the runtime on the
  target device → eliminated for that (device, runtime) combo only, per
  spec §0.1. For coder/planner (GPU-only in this pool), one launch failure =
  eliminated outright.
- **Malformed output:** >1 malformed task (invalid tool call for coder;
  invalid JSON or non-DAG plan for planner; degenerate vector for embedder)
  → eliminated. "Malformed" counts stay in the denominator per spec §0.0a
  bullet 1.
- **Latency outlier:** wall-time or per-call latency >5× the fastest
  candidate on the same task with no offsetting quality signal → flagged
  (not dropped) for Medium-tier confirmation, per spec §0.1.
- **Runtime-version regression flag:** launch failures traced to
  runtime-flag/behavior changes since a prior working cache are labeled
  separately from model failures, per spec §0.1 v16-addition and §0.1
  verification table row 4.

### 5. Output layout

Per-run JSON records land under
`bench/results/phase-0-fast/<UTC-timestamp>/<slug>.json` — never overwrite,
never share a JSON file across candidates. Matches `local-llm-bench` skill
principle #4 and existing runner scaffold in
`scripts/benchmark-tier-runner.py`.

### 6. Scored rubric deferred

Perplexity-gold-standard scoring (`local-llm-bench` scoring protocol) is
**not** used at Fast tier — Fast tier is elimination-only. It first applies
at Medium tier (§0.2 planner rubric, coder pass/fail scoring) and Full tier
(§0.3 ranked outcomes). A future ADR will lock the Medium-tier rubric before
first Medium-tier scored output.

### 7. Progress-visibility discipline (harness runtime)

Every Fast-tier harness invocation MUST emit line-buffered, timestamped
progress — no silent multi-minute phases. Specifically:

- Print an explicit `starting <phase>` line at the top of each phase (cell
  launch, per-task probe, teardown, manifest append) and a `done in Xs`
  bookend when the phase completes.
- Include an `[i/N] YYYY-MM-DD HH:MM:SS EDT` prefix on per-candidate and
  per-task lines so batches show position and wall-clock at a glance.
- Any phase whose expected duration exceeds ~15 seconds must emit an
  elapsed-seconds heartbeat (byte counter for downloads, task counter for
  loops, or a plain elapsed ticker for waits) at least every 10 seconds.
- Python child processes run with `PYTHONUNBUFFERED=1` or line-buffered
  stdio. Bash pipelines use `set -o pipefail` and never send hot-path
  output to `/dev/null`.
- `subprocess.run(..., capture_output=True)` without a concurrent tee is
  forbidden on the serving path; use `Popen` with a streaming reader.

This is a project-wide constraint that also applies to Medium and Full
tiers when their ADRs are filed.

## Rationale

- Fast tier's ≤30-minute total budget across all three roles cannot support
  real SWE-bench material for coder (250+ min at minimum) or free-form
  rubric-scored planner output — both would blow the budget while
  Medium/Full tiers exist specifically to carry that weight.
- Deterministic pass/fail probes at Fast tier match the spec's explicit
  intent ("triage and infeasibility elimination") and preserve statistical
  discipline (§0.0a) by keeping malformed-in-denominator handling mechanical.
- Skill/spec sampling conflict is resolved by binding to the actual runtime
  affordance: llama.cpp fixes sampling at launch, vLLM per-request. Uniform
  planner-preset at llama.cpp cells does bias coder cells toward planner
  sampling — accepted at Fast tier because coder cells are eliminated by
  tool-call-validity, not by output-quality subtleties that sampling would
  swing.
- Adopting `local-llm-bench` skill conventions here (prompts-on-disk,
  JSON-per-cell, per-run dirs, `<think>`-stripping) keeps future benches
  in this project consistent with Kosmos benches.

## Consequences

Files created:

- `bench/tasks/coder-fast.json`
- `bench/tasks/planner-fast.json`
- `bench/tasks/embedder-fast.json`
- `bench/rubrics/fast-elimination.json`

Files updated:

- `bench/candidates/registry.json` — `approx_size_gib` calibrated from
  measured manifest sizes (co-committed).
- `adrs/README.md` — index row appended.
- `BUILD_LOG.md` — appended per `kosmos-log-maintenance`.
- `SESSION_HANDOFF.md` — overwritten with post-authoring state.

Downstream:

- Medium-tier task/rubric ADR (numbered at filing) inherits these
  authoring conventions.
- `scripts/benchmark-tier-runner.py` — future real-serving implementation
  must consume `bench/tasks/*-fast.json` and enforce
  `bench/rubrics/fast-elimination.json` mechanically.

## Lock-in phase

Phase 0.1 (Fast tier). Ratified before any Fast-tier scored/eliminated run
so §0.0a "no post-hoc rubric editing" rule is satisfied.

## References

- `docs/specs/integration-execution-plan-v16.md` §0.0a, §0.0c, §0.1, §0.4
- User skill `local-llm-bench` (Path D v2, F.19-pre)
- ADR-0006 — flashinfer SM_120 support (Fast-tier vLLM cells depend on it)
- `bench/schema/run.schema.json` — 7-category instrumentation schema
