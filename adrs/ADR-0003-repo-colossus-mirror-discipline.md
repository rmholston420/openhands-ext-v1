# ADR-0003 — Repo / Colossus Mirror Discipline

> **STATUS AMENDMENT (2026-08-11):** Added the **commit-message truth gate**
> in `scripts/session-end.sh`. It refuses to commit with subjects containing
> "all green", "verification table green", "phase -1 complete", or similar
> completion claims when the two Phase -1 smoke-test JSONs
> (`bench/results/phase-neg-1-smoke-{llama-cpp,vllm}-*.json`) do not both
> have `status: "pass"`. Every commit body now also carries
> `smoke.llama-cpp: <status>` and `smoke.vllm: <status>` lines so the truth
> travels with the commit. `ALLOW_GREEN_OVERRIDE=1` is available for
> exceptional bypass but leaves an explicit marker.
>
> Filed because commit `535bc35` was pushed with subject "phase(-1): §-1
> Verification table all green" while both smoke tests had failed
> (llama.cpp: build broke on CUDA-12.8/glibc-2.43 incompat; vllm: OOM at
> startup because ~29 GiB of VRAM was already held by other processes).
> See DEBUG_LOG.md entries 2026-08-11 and ADR-0004 (llama.cpp CUDA-13 pin).

**Status:** Amended
**Lock-in phase:** Pre-Phase -1 (all subsequent phases)
**Supersedes:** —

## Context

This project has two active surfaces:

- **Colossus** (the user's local workstation) — the **execution surface**. Runs
  builds, benchmarks, docker workloads, produces measurement results.
- **Perplexity Computer sessions** — the **authoring surface**. Writes specs, ADRs,
  scripts, ledger entries, and reviews history.

Both surfaces touch the same GitHub repo `rmholston420/openhands-ext-v1`. Without
explicit discipline, the following failure modes are inevitable:

- One surface edits a tracked file; the other surface pushes over it.
- Colossus produces a `BUILD_LOG.md` entry that never lands on GitHub; next
  Perplexity session re-authors it.
- Large artifacts (GGUF weights, `.venv`, build outputs) accidentally get committed.
- "Works on Colossus but not from a fresh checkout" — undocumented local state.

The user's explicit request was:

> we need our GitHub repo and Colossus to mirror each other perfectly while developing

"Perfectly" cannot literally mean byte-for-byte — venvs are ~2GB, GGUFs are 1-30GB
each, `vendor/llama.cpp/build` is ~4GB, and GitHub's per-file limit is 100MB. The
enforceable interpretation is **"the repo captures everything reproducibly."**

## Decision

**Three-category rule — every artifact under `~/dev/openhands-ext-v1/` (Colossus)
or the Perplexity project files checkout must be exactly one of:**

1. **Tracked in git** — source code, configs, ADRs, ledgers, scripts, spec docs,
   small JSON benchmark results, test fixtures. Committed to `main`.

2. **Regenerable by a tracked script** — `.venv`, `vendor/*`, `models/*`, docker
   images, build outputs. **Every regenerable artifact has a tracked
   `scripts/*.sh` that produces it deterministically.** The script's inputs
   (pinned versions in `VERSIONS.lock`, model IDs, build flags) are themselves
   tracked.

3. **Explicitly ephemeral** — `/tmp/*`, ad-hoc scratch outside the project tree.
   **Never referenced by any tracked file.**

**No fourth category.** If a file exists in `~/dev/openhands-ext-v1/` and is not
(1) or (3), we either commit it (1), write the script that produces it (2), or
delete it.

**Sync strictness: HARD.**

- `scripts/session-start.sh` refuses to run if the working tree is dirty or
  `origin/main` has commits not present locally.
- `scripts/session-end.sh` refuses to exit without pushing local commits to
  `origin/main`.
- `hooks/pre-push/no-diverged-remote.sh` rejects a push if `origin/main` has
  advanced since the last fetch — forces explicit rebase decision.
- Pre-commit size guard rejects any single file over 10 MiB unless allow-listed.

**Both surfaces push to `main` directly.** No feature branches for solo local-first
work. Matches the single-user posture from space custom instructions. When a
larger refactor warrants branch isolation, we file an amendment ADR.

**Colossus commits and Perplexity commits are both attributed** by including a
surface marker in the commit message body (e.g. `on-colossus` or
`perplexity-session:<uuid>`) so history review can distinguish which surface
authored a change.

## Rationale

Alternatives considered:

1. **No formal rule; trust discipline** — rejected. Two surfaces plus append-only
   logs plus large artifacts plus a solo operator across long time gaps
   guarantees divergence. Divergence is much cheaper to prevent than to
   reconcile.

2. **Soft warnings only in sync scripts** — rejected. The user explicitly chose
   "make optimal choice" for sync strictness; the optimal choice for a
   deterministic reproducibility discipline is hard-fail, not warnings. Warnings
   get ignored during flow states.

3. **Full workspace mirror via git-annex or LFS** — rejected. Adds a second
   storage system, doesn't solve the venv/docker-image problem (they're not
   files to sync, they're derived state), and introduces per-file cost. Scripts
   that regenerate are simpler and more auditable.

4. **Feature branches for every change** — rejected. Single-operator local-first
   work does not need PR review; branching adds ceremony without adding
   correctness. Reserved for genuine parallel refactors, filed as an amendment
   if that day comes.

## Consequences

New files:

- `hooks/pre-commit/size-guard.sh` — rejects files over 10 MiB with an
  explicit allow-list (initially empty).
- `hooks/pre-push/no-diverged-remote.sh` — rejects push if remote has advanced
  since the last fetch.
- `scripts/install-hooks.sh` — extended to install the pre-push hook and the
  size-guard pre-commit alongside the existing `no-localworkspace.sh`.
- `scripts/session-start.sh` — pulls, verifies clean tree, tails
  `SESSION_HANDOFF.md` and the last N `BUILD_LOG.md` entries.
- `scripts/session-end.sh` — commits any local changes with a user-supplied
  message, pushes, verifies remote received the commit.
- `scripts/bootstrap-venv.sh` — creates or re-creates `.venv`, installs
  base tooling (`hf` CLI, wheel, setuptools).
- `scripts/build-llama-cpp.sh` — clones and builds llama.cpp with
  `-DCMAKE_CUDA_ARCHITECTURES=120` and `-DCMAKE_CUDA_HOST_COMPILER=/usr/bin/gcc-13`
  per Colossus toolchain probe.
- `scripts/install-oh-sdk.sh` — installs pinned OpenHands SDK tags from
  `VERSIONS.lock`.
- `scripts/install-vllm.sh` — installs pinned vLLM tag.
- `scripts/pull-models.sh` — pulls Qwen2.5-1.5B-Instruct in GGUF + safetensors.
- `scripts/smoke-test-llama-cpp.sh` — §-1.5 verification (llama.cpp runtime).
- `scripts/smoke-test-vllm.sh` — §-1.5 verification (vLLM runtime).

Every script is idempotent — safe to re-run. Every script logs to
`/tmp/openhands-ext-v1-<script>-<timestamp>.log`. Scripts never modify the
interactive shell's environment via `exec`; when a script needs the venv
activated, it either activates within its own subshell or documents the
required incantation at the top.

Behavioral changes:

- Every Perplexity session begins by pulling from `origin/main` (already
  done via the project files checkout `sync`).
- Every Colossus session begins by running `bash scripts/session-start.sh`.
- Every Colossus session ends by running `bash scripts/session-end.sh`.
- The size guard prevents accidental commits of GGUFs or wheels; the
  `.gitignore` already covers the expected paths but the guard is defense in
  depth.

Not covered by this ADR (deferred):

- What to do when both surfaces make concurrent conflicting edits to the same
  file — handled at merge time by whichever operator resolves; no ADR needed
  until it happens.
- Backup / disaster recovery for Colossus-only state (models, venvs) — the
  regenerability contract makes this unnecessary.

## References

- User statement: "we need our GitHub repo and Collosus to mirror each other
  perfectly while developing" (session
  `a97513e8-710d-484b-a54a-2e2e18ae0c24`, 2026-08-10 23:39 EDT)
- ADR-0002 (LocalWorkspace guard = pre-commit hook, not GitHub Actions) — same
  local-first posture
- Space custom instructions: "single-user, local-first system"
- `SESSION_HANDOFF.md` schema (from user's kosmos-log-maintenance skill)
