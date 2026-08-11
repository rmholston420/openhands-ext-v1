"""
OpenHands live UI smoke test — 2026-08-11.

Drives the real browser UI end-to-end:
  UI1. Load home screen, screenshot
  UI2. Dismiss consent form (idempotent — skip if already dismissed)
  UI3. Click New Conversation (uses the settings already stored via API)
  UI4. Type task into contenteditable chat-input
  UI5. Click submit-button
  UI6. Wait for agent-loading-spinner to appear (agent started) — SOFT
       (spinner can be missed if response is very fast; UI7 is the
       real functional check)
  UI7. Wait until expected token appears in page DOM
  UI8. Verify Canvas GUI tabs present (planner/editor/vscode/terminal/browser)

Baseline (2026-08-11 08:22 EDT):
  7/8 PASS. UI6 SOFT fail on very-fast responses (agent finished before
  the polling loop caught the transient spinner). All other steps PASS
  including UI7 (expected token visible in DOM) and UI8 (Canvas tabs).

Prerequisites:
  - Full-suite smoke v3 already PASSED (settings stored, UFW rule active).
  - openhands-app on :3000, coder on :8100.
  - Playwright chromium installed in project venv.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, expect

BASE = "http://127.0.0.1:3000"
VLLM_METRICS = "http://127.0.0.1:8100/metrics"
ART = Path("/tmp/oh-live-ui")
ART.mkdir(exist_ok=True)


def vllm_prompt_tokens() -> float:
    try:
        with urllib.request.urlopen(VLLM_METRICS, timeout=5) as r:
            for line in r.read().decode().splitlines():
                if line.startswith("vllm:prompt_tokens_total"):
                    m = re.search(r"\}\s+([\d.]+)$", line)
                    if m:
                        return float(m.group(1))
    except Exception:
        pass
    return -1.0


def ensure_settings_via_api() -> None:
    payload = {
        "agent_settings_diff": {
            "agent": "CodeActAgent",
            "llm": {
                "model": "openai/qwen3-coder-30b-a3b-instruct-awq-4bit",
                "base_url": "http://host.docker.internal:8100/v1",
                "api_key": "none",
                "auth_type": "api_key",
            },
        }
    }
    req = urllib.request.Request(
        BASE + "/api/v1/settings",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        assert r.status == 200, f"settings POST returned {r.status}"


def snap(page: Page, name: str) -> None:
    p = ART / name
    page.screenshot(path=str(p), full_page=True)
    print(f"    screenshot: {p}")


def main() -> int:
    print("=" * 60)
    print("OpenHands live UI smoke — 2026-08-11")
    print("=" * 60)

    ensure_settings_via_api()
    baseline = vllm_prompt_tokens()
    print(f"vLLM baseline prompt_tokens_total = {baseline}")

    task_text = "Reply with exactly the string OK-LIVE-UI-2026 and stop."
    steps = []

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # UI1
        print("\n[UI1] load home")
        resp = page.goto(BASE + "/", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        snap(page, "01_home.png")
        steps.append({"step": "UI1_load_home", "http": resp.status if resp else 0,
                      "title": page.title(),
                      "pass": (resp is not None and resp.status == 200 and page.title() == "OpenHands")})

        # UI2
        print("\n[UI2] dismiss consent")
        consent = page.locator('[data-testid="confirm-preferences"]')
        if consent.count() > 0:
            consent.first.click()
            page.wait_for_timeout(1500)
            snap(page, "02_after_consent.png")
            steps.append({"step": "UI2_dismiss_consent", "consent_present": True, "pass": True})
        else:
            steps.append({"step": "UI2_dismiss_consent", "consent_present": False, "pass": True})

        # UI3
        print("\n[UI3] new conversation")
        new_conv = page.locator('[data-testid="launch-new-conversation-button"]')
        if new_conv.count() == 0:
            steps.append({"step": "UI3_new_conversation", "pass": False, "reason": "button not found"})
            snap(page, "03_error_no_new_conv.png")
            b.close(); print(json.dumps(steps, indent=2)); return 1
        new_conv.first.click()
        for _ in range(30):
            page.wait_for_timeout(500)
            if "/conversations/" in page.url:
                break
        page.wait_for_timeout(3000)
        snap(page, "03_conversation_ready.png")
        conv_url = page.url
        print(f"    conversation URL: {conv_url}")
        steps.append({"step": "UI3_new_conversation", "url": conv_url,
                      "pass": "/conversations/" in conv_url})

        # UI4
        print("\n[UI4] type task")
        chat_input = page.locator('[data-testid="chat-input"]')
        expect(chat_input).to_be_visible(timeout=10000)
        chat_input.click()
        page.keyboard.type(task_text, delay=15)
        page.wait_for_timeout(500)
        snap(page, "04_task_typed.png")
        entered = chat_input.inner_text()[:120]
        steps.append({"step": "UI4_type_task", "entered_text": entered,
                      "pass": task_text[:20] in entered})

        # UI5
        print("\n[UI5] submit")
        submit = page.locator('[data-testid="submit-button"]')
        expect(submit).to_be_visible(timeout=5000)
        submit.click()
        page.wait_for_timeout(2000)
        snap(page, "05_submitted.png")
        steps.append({"step": "UI5_submit", "pass": True})

        # UI6 — SOFT: spinner may be transient
        print("\n[UI6] poll for agent-loading-spinner (SOFT)")
        spinner = page.locator('[data-testid="agent-loading-spinner"]')
        appeared = False
        for i in range(30):  # up to 30s
            if spinner.count() > 0 and spinner.first.is_visible():
                appeared = True
                print(f"    spinner appeared at t+{i*0.2:.1f}s")
                break
            # Also check if the response already came in — if so, spinner missed
            body_snippet = page.locator("body").inner_text()
            if "OK-LIVE-UI-2026" in body_snippet:
                print(f"    response already in DOM by t+{i*0.2:.1f}s (spinner missed)")
                break
            page.wait_for_timeout(200)
        snap(page, "06_spinner.png")
        steps.append({"step": "UI6_spinner_appeared", "pass": appeared, "note": "SOFT — spinner is a transient UX element"})

        # UI7 — REAL functional check: expected token in DOM
        print("\n[UI7] wait for expected response token in DOM (up to 120s)")
        got_response = False
        first_seen_at = None
        for i in range(120):
            body_text = page.locator("body").inner_text()
            if "OK-LIVE-UI-2026" in body_text:
                got_response = True
                first_seen_at = i
                print(f"    expected token found at t+{i}s")
                break
            page.wait_for_timeout(1000)
        snap(page, "07_final.png")
        final_tokens = vllm_prompt_tokens()
        steps.append({
            "step": "UI7_agent_response",
            "expected_token_visible": got_response,
            "first_seen_at_s": first_seen_at,
            "vllm_baseline": baseline,
            "vllm_final": final_tokens,
            "vllm_delta": final_tokens - baseline if final_tokens >= 0 else None,
            "pass": got_response and (final_tokens > baseline + 500),
        })

        # UI8
        print("\n[UI8] verify Canvas GUI tabs")
        tabs = {}
        for name in ("planner", "editor", "vscode", "terminal", "browser"):
            tabs[name] = page.locator(f'[data-testid="conversation-tab-{name}"]').count() > 0
        snap(page, "08_canvas_tabs.png")
        steps.append({"step": "UI8_canvas_tabs", "tabs_found": tabs,
                      "pass": all(tabs.values())})

        b.close()

    (ART / "results.json").write_text(json.dumps(steps, indent=2))
    print("\n" + "=" * 60)
    print(json.dumps(steps, indent=2))
    hard_passed = sum(1 for s in steps if s.get("pass") and s.get("step") != "UI6_spinner_appeared")
    hard_total = sum(1 for s in steps if s.get("step") != "UI6_spinner_appeared")
    soft_passed = sum(1 for s in steps if s.get("pass"))
    total = len(steps)
    print(f"\n===== LIVE UI SMOKE (hard checks): {hard_passed}/{hard_total} PASS =====")
    print(f"===== LIVE UI SMOKE (including SOFT UI6): {soft_passed}/{total} =====")
    return 0 if hard_passed == hard_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
