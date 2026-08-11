# ADR-0021 — Live UI Playwright Smoke Test

**Status:** Ratified
**Lock-in phase:** Phase 1 (full-suite smoke)
**Supersedes:** —

## Context

The Phase 1 full-suite smoke (v3, ADR-0020) validated backend plumbing via API. What was still missing: proof that a real user could open the browser at `http://127.0.0.1:3000/`, type a task into the composer, and see the agent respond in the DOM. Combobox-based settings modal drove earlier UI probes to failure; that motivated the API-first settings preload used here.

## Decision

Adopt `tests/smoke/test_openhands_live_ui.py` as the canonical Phase 1 live-UI smoke test. Structure:

- Pre-seed agent settings via `POST /api/v1/settings` (bypass the combobox modal).
- Playwright headless chromium drives 8 UI steps against `openhands-app :3000`.
- Selectors discovered via `probe_dom.py` + `probe_conversation.py`:
  - Composer: `div[data-testid="chat-input"]` (contenteditable, not textarea)
  - Send: `button[data-testid="submit-button"]`
  - Consent: `button[data-testid="confirm-preferences"]`
  - New conversation: `button[data-testid="launch-new-conversation-button"]`
  - Canvas tabs: `button[data-testid="conversation-tab-{planner,editor,vscode,terminal,browser}"]`
- UI6 (`agent-loading-spinner`) is a **SOFT** check — it is transient and can be missed on fast responses. Ground truth is UI7: expected token appears in page DOM AND vLLM delta > 500 tokens.

## Rationale

- **API pre-seed** avoids the fragile combobox that failed earlier iterations.
- **Token-in-DOM + vLLM metric delta** together prove: (a) the frontend rendered the assistant message, (b) coder actually processed the prompt.
- **Full-page screenshots at every step** give visual proof for humans reviewing the run.
- **SOFT spinner** because the spinner can render and unrender inside a single 200 ms poll cycle on very fast responses; failing the whole test on that race would be brittle.

## Consequences

- Files created:
  - `tests/smoke/test_openhands_live_ui.py` (headless, canonical CI test)
  - `tests/smoke/test_openhands_live_ui_headed.py` (headed v1, sentinel task — kept for reference)
  - `tests/smoke/test_openhands_live_ui_headed_v2.py` (headed canonical — multi-step coding task, streaming visible)
  - `tests/smoke/probe_dom.py` (DOM discovery helper)
  - `tests/smoke/probe_conversation.py` (conversation-view DOM discovery)
- Artifacts written to `/tmp/oh-live-ui/`, `/tmp/oh-live-ui-headed/`, `/tmp/oh-live-ui-headed-v2/` on every run.
- Baselines recorded:
  - **Headless** 2026-08-11 08:22 EDT: 7/8 hard PASS + UI6 SOFT · `vllm_delta = +18113 prompt_tokens` · token `OK-LIVE-UI-2026` visible in DOM.
  - **Headed v2** 2026-08-11 08:30 EDT: natural stop at t+28.5s · `prompt_tokens_delta = +74565` · `generation_tokens_delta = +931` · `body_chars 838 → 3598` in visible increments · terminal + editor tab screenshots captured.

### Why the v1 headed test is superseded

v1 headed used the same one-word sentinel task as the headless test. On Colossus with a warm coder pool the agent completed the sentinel in <1 second, faster than Playwright's screenshot cadence. All post-submit screenshots ended up identical. v2 uses a real multi-step coding task (write file → run → report output) that reliably takes 15-40 s, so streaming is visible frame-to-frame in the browser and in the per-second terminal log.

## Lock-in phase

Phase 1 · Definition of Done: "OpenHands app boots on Colossus, browser-driven test proves user can interact and get a response."

## References

- ADR-0020 (UFW bridge egress fix — prerequisite)
- `tests/smoke/test_openhands_suite_v3.py` (API-driven companion, 5/5 PASS)
- `BUILD_LOG.md` 2026-08-11 08:22 EDT
