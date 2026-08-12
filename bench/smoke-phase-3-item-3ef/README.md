# Phase 3.e / 3.f — Canvas UI Event Stream + Confirmation UI

**Run:** 2026-08-11 21:11 EDT
**Verdict:** ✅ PASS (both items, HTTP + Playwright live)

## Scope

- **3.e** — Event stream renders in Canvas
- **3.f** — Confirmation UI fires in Canvas

Both items require an operator LLM configured in Canvas Settings and a live conversation. Verified end-to-end via HTTP (`curl` + on-disk event log) **and** live UI-driving via Playwright.

## Environment

- **LLM:** `hosted_vllm/qwen3-coder-30b-a3b-instruct-awq-4bit` @ `http://127.0.0.1:8100/v1` (vLLM 0.27.0, tool-parser `qwen3_coder`, max-model-len 32768)
- **Canvas ingress:** `http://127.0.0.1:8000`
- **Canvas Vite (frontend):** `http://127.0.0.1:3002`
- **Canvas agent-server:** `http://127.0.0.1:18000`
- **Playwright:** 1.62.0 + chromium 1234, `~/.forge-oh/pw-venv` (Python 3.14)

## Results matrix

| Item | Method | Conversation | Verdict |
|---|---|---|---|
| 3.e | HTTP: create finished conversation, verify `execution_status=finished` + events on disk | `73792f58-1e59-4c33-8897-a94f4398519d` | ✅ |
| 3.e | Canvas UI Playwright: load `/conversations/{id}`, verify `echo hello from smoke` rendered in DOM | `73792f58-1e59-4c33-8897-a94f4398519d` | ✅ |
| 3.f | HTTP: blocked action created + resumed via API confirmation | `dce29b59-6df2-41e2-942c-98963111f639` | ✅ |
| 3.f | Canvas UI Playwright: load `/conversations/{id}`, verify rendering | `dce29b59-6df2-41e2-942c-98963111f639` | ✅ |
| Bonus | Canvas UI Playwright: fresh conversation created live via onboarding → agent called terminal (echo, exit 0) → finish | `d49697e9-224e-4093-bbdb-0f3c0183fd67` | ✅ |

## Live conversation evidence (`d49697e9-...`)

11 events on disk at `~/.openhands/agent-canvas/dev_conversations/d49697e9224e4093bbdb0f3c0183fd67/events/`:

```
event-00000 ConversationStateUpdateEvent
event-00001 SystemPromptEvent
event-00002 MessageEvent
event-00003 ConversationStateUpdateEvent
event-00004 ConversationStateUpdateEvent
event-00005 ActionEvent      terminal
event-00006 ActionEvent      finish
event-00007 ObservationEvent terminal   → content="hello from playwright live", exit_code=0
event-00008 ObservationEvent finish
event-00009 ConversationStateUpdateEvent
event-00010 ConversationStateUpdateEvent
```

Stats: 1 turn, 19053 prompt tokens, 60 completion tokens, 1.94 s latency, `execution_status=finished`.

## Key findings

- **Basic-tab LLM step uses combobox inputs that hang Playwright's synthetic click.** Advanced tab (`sdk-section-advanced-toggle`) exposes plain text inputs — `llm-custom-model-input`, `base-url-input`, `llm-api-key-input` — usable via `page.fill()`. The custom-model field accepts the full litellm-style prefix (e.g. `hosted_vllm/qwen3-coder-30b-a3b-instruct-awq-4bit`).
- **`PATCH /api/settings` requires diff field names.** Body must be `{"agent_settings_diff": {"llm": {...}}}`, not `{"agent_settings": {...}}` — the latter returns 400 "At least one of agent_settings_diff, conversation_settings_diff, misc_settings_diff must be provided".
- **`~/.openhands/settings.json` is Fernet-encrypted with the Canvas session API key.** Rotating the session key (Canvas restart with new key) makes the settings file unreadable and PATCH returns 500 "Settings file is corrupted or encrypted with a different key". Fix: `rm settings.json`, then re-onboard or re-PATCH.

## Playwright driver

`/tmp/oh-smoke-3ef/pw/flow_c.py` (v6, off-repo) drives: onboarding (Advanced tab) → settings verification → Part B (past conversations) → Part A (fresh live conversation). Not committed to repo (temp scratch; captured here for reproducibility).

Screenshots archive: `~/.forge-oh/bench_smoke_phase_3_item_3ef/pw_20260811_2110/` (30+ frames).

## Related

- DEBUG_LOG entries 2026-08-11 21:11 EDT (3 entries: combobox hang, settings encryption reset, PATCH diff field name)
- BUILD_LOG entry 2026-08-11 21:11 EDT
- verification-matrix.md rows 3.e and 3.f flipped ✅
