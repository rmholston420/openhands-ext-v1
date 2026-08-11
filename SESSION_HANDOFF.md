# SESSION_HANDOFF — 2026-08-11 12:06 EDT

## Current build-sequencing position
- **Stage / phase:** Phase 0.3 gate-3 (coder Full-tier re-eval)
- **Plugin / kernel component:** bench harness (multi-turn) · coder role
- **Port(s) in progress:** none (bench-only)
- **Governing ADR:** ADR-0028 (Ratified 2026-08-11 12:05 EDT)

## Completed this session
- ADR-0027 (gate-2 verdict: CONFIRM AWQ) authored and Ratified; commit `af732e2` pushed.
- ADR-0028 gate-3 opener + Full-tier task-set scaffold committed; commit `cffda04` pushed.
- **Gate-3 fixture lock-in** (this commit): populated 10 fixtures in `bench/tasks/coder-full-multi-turn.json`, authored 10 gold rubric files, authored `bench/rubrics/full-scored.json` (adds `-10` deduction for FinishAction omission on report-style tasks), authored 2 candidate cell files, pinned docker SHA digest, flipped ADR-0028 Proposed → Ratified.

## Remaining before current Definition of Done
Gate-3 DoD steps 5–7 (from ADR-0028 §Sub-decision 5):
5. Execute probe runs — one run per candidate on the 10-task set. AWQ (`qwen3-coder-30b-a3b-instruct-awq-4bit` at :8501) + 35b (`qwen3_6-35b-a3b-q4kxl-gguf` at :8082).
6. Score all 20 (2 candidates × 10 tasks) via Perplexity Max against `bench/gold/coder-full-multi-turn/*.md`. Compute per-task scores + macro. Mechanically apply reversal criteria (no post-hoc reinterpretation).
7. Author verdict ADR-0029 (CONFIRM AWQ / FLIP to 35b / INTERMEDIATE + log per-task mix), update `adrs/README.md`, append BUILD_LOG, overwrite SESSION_HANDOFF.

## Open questions / awaiting user answer
- **None.** All fixture-lock choices made under "make optimal choices" mandate; docker digest supplied by user; reversal criteria + post-hoc lock in place.

## Exact next action
On Colossus, after pulling:

```bash
cd ~/dev/openhands-ext-v1 && git pull --ff-only
# Verify AWQ vLLM is up at :8501 and 35b llama.cpp at :8082 before running probes.
# Probe-runner invocation (canonical harness entry per ADR-0026 v1.1):
python -m bench.run_multi_turn \
  --task-set bench/tasks/coder-full-multi-turn.json \
  --candidates bench/candidates/coder-full-awq.json \
  --out bench/results/coder-full-awq
python -m bench.run_multi_turn \
  --task-set bench/tasks/coder-full-multi-turn.json \
  --candidates bench/candidates/coder-full-35b.json \
  --out bench/results/coder-full-35b
```

Then dump traces per the local-llm-bench skill scoring protocol and paste back for Perplexity-Max scoring.
