# OpenHands-Ext v1 — Session Handoff — 2026-08-11 00:57 EDT

## Current build-sequencing position

- **Stage / phase:** Phase 0 — pre-tier scaffolding in place. Phase -1 §-1 closed.
- **Plugin / kernel component:** none (harness scaffolding).
- **Port(s) in progress:** none.

## Completed this session (cumulative, since last handoff)

- **flashinfer SM_120 workaround retired.** ADR-0005 amended · superseded by ADR-0006 (cu129 JIT cache). `scripts/smoke-test-vllm.sh` unconditional `VLLM_USE_FLASHINFER_SAMPLER=0` export removed. `scripts/install-vllm.sh` gained step 2b that installs `flashinfer-jit-cache==<flashinfer-python-version>+cu129` from `https://flashinfer.ai/whl/cu129/`. Verification smoke: `bench/results/phase-neg-1-smoke-vllm-20260811T044948Z.json` (pass, no workaround).
- **7-category schema (v16 §0.0c) landed.** `bench/schema/run.schema.json`, `bench/schema/run.py`, `bench/schema/__init__.py`, `bench/schema/README.md`. Nullable fields corrected (rubric/notes/optional latency) — all 7 schema tests pass on Colossus.
- **Tier runner scaffold landed.** `scripts/benchmark-tier-runner.py` enforces §0.0a rubric-lock, latency-must-be-measured, denominator-exclusion; §0.0b open-pool; §0.1/0.3 tier-scope for category 6. Dry-run emits a schema-valid record on Colossus.
- **Phase 0 candidate registry authored.** `bench/candidates/registry.json` lists 9 candidates across coder/planner/embedder pools with canonical HF repo IDs.
- **`scripts/pull-models.sh` rewritten.** Table-driven from the registry, `--role coder|planner|embedder|all`, `--dry-run`, disk preflight, idempotent, live HF-revision pinning, `models/manifest.json` append-only.
- **Old `pull-models.sh` renamed** to `scripts/pull-smoke-model.sh` (unchanged, Phase -1 smoke fetch preserved).
- Latest commit: `47bba16` on `main` (schema null-fix + ADR-0006). This session's pending commit adds the candidate registry + rewritten pull-models.sh.

## Remaining before current Definition of Done (Phase 0 §0.1 Fast tier readiness)

1. Push the pending candidate-registry + pull-models.sh commit.
2. On Colossus: `git pull`, then run `scripts/pull-models.sh --role embedder --dry-run` to verify the plan, then `--role all` for real (~165 GiB, wall-clock long).
3. Author `bench/tasks/coder-fast.json`, `bench/tasks/planner-fast.json`, `bench/tasks/embedder-fast.json` (§0.1).
4. Author `bench/rubrics/planner-fast.json` with `locked_at_utc`.
5. Implement real serving+scoring in `benchmark-tier-runner.py` (replace `build_dry_run_record`) — this is the big Phase 0 build item.
6. First Fast-tier real run on the embedder pool (smallest, fastest smoke of the full pipeline).

## Open questions / awaiting user answer

- None. Both close-call choices (Intel over Lorbus for the AutoRound-27B; 30B-A3B over 235B for the thinking model) were resolved on the "make optimal choice" rule.

## Exact next action

Confirm and push the pending commit (candidate registry + rewritten pull-models.sh). Then on Colossus:

```bash
cd ~/dev/openhands-ext-v1
git pull origin main
bash scripts/pull-models.sh --role embedder --dry-run
```

Paste the dry-run output before running the real download so we can eyeball the disk preflight and plan.
