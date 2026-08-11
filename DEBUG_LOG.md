# DEBUG_LOG.md — OpenHands-Ext v1

Append-only. Newest entries at the bottom. Do not edit prior entries.

**Hard rule (space custom instructions):** Before investigating any new error, `grep -in
"<symptom keywords>" DEBUG_LOG.md` first. If a matching or similar symptom exists, reuse
the recorded fix instead of re-diagnosing.

Entry format:

```markdown
## <YYYY-MM-DD HH:MM EDT> — <symptom summary>

- **Symptom:** <exact error text / behavior observed>
- **Affected stage / plugin / port:** <e.g. Phase 0.1 · llama.cpp coder cell>
- **Root cause:** <what was actually wrong>
- **Fix applied:** <what was changed>
- **Files changed:** <bullet list>
- **Related BUILD_LOG entry:** <timestamp or —>
```

---

## 2026-08-10 23:26 EDT — Pre-commit hook rejected initial commit (verification-matrix.md quotes LocalWorkspace)

- **Symptom:** `bash scripts/install-hooks.sh` self-check exited 1 with message "LocalWorkspace reference detected (mode: staged)" pointing at `docs/verification/verification-matrix.md:14` — a spec-verbatim quote in the Phase 1 row.
- **Affected stage / plugin / port:** ADR-0002 · pre-commit hook allow-list
- **Root cause:** Initial allow-list included `docs/specs/` and `docs/donor-inventory.md` but not `docs/verification/`, so the verification checklist (which necessarily quotes spec Phase 1's "Zero LocalWorkspace" language) triggered a false positive.
- **Fix applied:** Added `docs/verification/` to the allow-list regex in `hooks/pre-commit/no-localworkspace.sh`. The category of file is documentation that quotes spec sections verbatim — same rationale as `docs/specs/` and `adrs/`. Not a real policy violation.
- **Files changed:** `hooks/pre-commit/no-localworkspace.sh`
- **Related BUILD_LOG entry:** 2026-08-10 23:24 EDT (ADR-0002 filing)

## 2026-08-10 23:38 EDT — Phase -1 prep script killed the interactive bash shell

- **Symptom:** Colossus reported that pasting a Phase -1 prep script into an interactive `bash` shell caused the shell to die mid-script. The script had partially succeeded (apt install of cmake/ninja/gcc-13/g++-13 completed, `.venv/` created, pip upgraded, huggingface_hub installed) before the terminal was killed. Log at `/tmp/phase-1-prep-1786419502.log` shows the last visible line was a `hf`/`huggingface-cli` deprecation warning.
- **Affected stage / plugin / port:** Pre-Phase -1 · Colossus session-startup scripts
- **Root cause:** The script used two anti-patterns at interactive scope: (1) `set -euo pipefail` at the top of a pasted block runs in the *interactive* shell, so any non-zero exit terminates it; (2) `exec > >(tee -a "$LOG") 2>&1` redirects the interactive shell's own stdout/stderr through a subprocess `tee`, so when the pipeline received a nonzero exit under `pipefail`, the shell tore down its own fd redirection and died. The `huggingface-cli`/`hf_transfer` deprecation warnings from `huggingface_hub 1.27.0` were the likely trigger (they don't cause a nonzero exit themselves but the extras `[cli,hf_transfer]` are gone in 1.x, and any subsequent command that errored propagated into the killed tee pipeline).
- **Fix applied:** All new operational scripts under `scripts/*.sh` follow four rules: (a) instruct the user to invoke via `bash scripts/foo.sh` — never paste raw `set -e` blocks into an interactive shell; (b) redirect the *inside* of the script with `{ ...; } 2>&1 | tee "$LOG"` scoped to a single block, never `exec` at top-level; (c) use the modern `hf` CLI from `huggingface_hub>=1.0`, drop the deprecated `HF_HUB_ENABLE_HF_TRANSFER` env var; (d) each script is idempotent so a re-run after a crash resumes cleanly.
- **Files changed:** `scripts/bootstrap-venv.sh` (new, replaces the killed inline script), plus all other new `scripts/*.sh` files follow the same discipline. Added the constraint as a documented design principle in the top comment of `scripts/bootstrap-venv.sh`.
- **Related BUILD_LOG entry:** 2026-08-10 23:45 EDT (ADR-0003 mirror discipline + Phase -1 executable scripts)
