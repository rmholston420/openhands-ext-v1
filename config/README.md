# config/ — Production Configuration

**This directory is EMPTY by design at bootstrap.**

Per spec §Phase 2.4 and Perplexity Computer Custom Instruction #2:

> Do not populate this file from Fast- or Medium-tier results, even provisionally.

`config.toml` for the tiered LLM router (coder / planner / condenser / embedding) will
be written here **only** after Phase 0.3 (Full tier) concludes and declares winners.
Attempting to populate it earlier is a spec violation.

The pre-commit hook `no-localworkspace.sh` (ADR-0002) will also apply here once files
exist — this directory is not in the allow-list.
