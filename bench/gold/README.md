# Gold references — freeze policy

Per **ADR-0022** (Ratified 2026-08-11), all gold-reference files in this directory are single-pass Perplexity-Max generations, authored once, hashed into the task-set JSON's `gold_hashes` field at freeze time, and **not** re-editable in place.

## Freeze policy

- After the first Medium-tier scored run consumes a gold reference, that gold reference is frozen.
- If a gold answer is later found wrong or ambiguous, the correct remedy is **task-set version bump** (rename the task-set file to `<name>-v2.json` and re-author affected gold files) via a superseding ADR — never in-place edit.
- SHA-256 hashes stored in the task-set JSON's `gold_hashes` field enable freeze verification. Any hash mismatch at run time is a hard fail.

## Regeneration

If you need to regenerate a gold file (e.g. because the task changed materially), you must:

1. Author a superseding ADR justifying the change.
2. Bump the task-set version.
3. Regenerate the gold via a single Perplexity-Max pass (not multi-sample).
4. Update `gold_hashes` in the new task-set JSON.
5. Never delete or modify the original gold file — leave it for audit.

## Related

- ADR-0016 — Medium-tier scoring rubric shape (Perplexity-gold for coder + planner)
- ADR-0022 — Phase 0.2 coder + planner task-set + gold protocol
- `bench/rubrics/medium-scored.json` — frozen rubric (`post_hoc_edit_policy.allowed=False`)
- `local-llm-bench` skill — canonical Perplexity-gold protocol
