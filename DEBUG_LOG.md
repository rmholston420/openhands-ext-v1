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
