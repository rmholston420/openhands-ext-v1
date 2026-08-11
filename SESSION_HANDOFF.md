# OpenHands-Ext v1 — Session Handoff — 2026-08-10 23:24 EDT

## Current build-sequencing position

- **Stage / phase:** Pre-Phase -1 (author-side setup complete; Colossus-side execution not yet started)
- **Plugin / kernel component:** Repo bootstrap, scaffolding, governance
- **Port(s) in progress:** none (donor inventory complete, ports remain PLANNED)

## Completed this session

- Created private repo `rmholston420/openhands-ext-v1` (MIT).
- Committed `integration-execution-plan-v16.md` to `docs/specs/`.
- Live-fetched all upstream versions → `VERSIONS.lock` (fetch timestamp `2026-08-11T03:24:45Z`).
- Scaffolded directory structure for all downstream phases.
- Initialized four operational logs: `BUILD_LOG.md`, `DEBUG_LOG.md`, `KNOWN_ISSUES.md`, `SESSION_HANDOFF.md`.
- Initialized `PORTING_LEDGER.md` with 9 pre-drafted `PLANNED` entries (per-file SHAs captured from donors).
- Authored `ADR-0001-repo-bootstrap.md` and `ADR-0002-localworkspace-guard-pre-commit.md`.
- Wrote pre-commit hook `hooks/pre-commit/no-localworkspace.sh` and installer `scripts/install-hooks.sh`.
- Wrote donor inventory `docs/donor-inventory.md` with commit SHAs for OH-GUI and Forge-OH.

## Remaining before current Definition of Done

Definition of Done for this session was **author-side scoping only** — met. The next DoD
belongs to Phase -1 on Colossus, per spec §-1 Verification table:

- Re-fetch live tags on Colossus (compare against `VERSIONS.lock`).
- `pip install` OpenHands stack at re-verified tags.
- Build llama.cpp from re-verified tag with `-DCMAKE_CUDA_ARCHITECTURES=120`.
- `pip install vllm==<top-of-releases-at-Colossus-build-time>`.
- Run §-1.5 SDK-to-runtime smoke test on a small model, both runtimes.
- Report the Phase -1 Verification table row-by-row.
- Then, and only then, populate Phase 0.0c Category 7 run metadata with the actual
  runtime build/release tags Colossus used.

## Open questions / awaiting user answer

None. All ambiguities from the previous session have been resolved by user answers
recorded in ADR-0001 and ADR-0002.

## Exact next action

On Colossus (from a fresh terminal):

```bash
mkdir -p ~/dev && cd ~/dev
gh repo clone rmholston420/openhands-ext-v1
cd openhands-ext-v1
bash scripts/install-hooks.sh
cat VERSIONS.lock                             # freshness reference
cat SESSION_HANDOFF.md                        # this file
cat docs/specs/integration-execution-plan-v16.md | head -100
```

Then begin Phase -1 execution per spec §-1.4 and §-1.5.
