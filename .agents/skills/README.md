# Retroactively Captured Skills

**Spec:** § Phase 2.3.
**Scope:** repo-local skills, shared across every clone of this repo.

## What lives here

Skills captured **after** a workflow has been completed at least once. Never file a skill speculatively — spec §2.3 discipline is retroactive capture only.

## What does NOT live here

- Personal, cross-repo skills → `~/.agents/skills/` (not committed to any repo).
- Skills that describe a workflow you haven't actually done — those are speculation, not skills.

## Naming convention

`.agents/skills/<kebab-case-name>.md`

The kebab-case name should describe the workflow's action, not its subject.

Good: `retire-benchmark-cell.md`, `restart-large-model-role.md`.
Bad:  `models.md`, `benching.md`.

## Capture procedure

1. Finish the workflow. Note what was mechanical, what was judgment.
2. In your active OpenHands session:
   ```
   /skill-creator Create a skill for automating this workflow in the future
   ```
3. Skill-creator writes a draft to `.agents/skills/<name>.md` (or `~/.agents/skills/<name>.md` for personal skills).
4. Review the draft; delete session-specific detail (paths, timestamps, credentials).
5. Commit the repo-local ones.

## Retirement

If a skill becomes obsolete:
- Move it to `.agents/skills/retired/<name>.md` (do not delete — keep for history).
- Note the retirement reason at the top of the file.

## Discovery

Skills in this directory are auto-discovered by OpenHands sessions launched from this repo root. Sessions launched from `~/.agents/skills/` are auto-discovered globally by any OpenHands session that user starts.

## Currently filed

None. Skills arrive retroactively during Phase 3+.
