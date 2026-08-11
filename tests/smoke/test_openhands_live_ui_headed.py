"""
Headed live UI smoke — WATCH IN REAL TIME.

Same 8 steps as test_openhands_live_ui.py, but:
  - headless=False  → real chromium window opens on your display
  - slow_mo=400ms   → every action visibly paced
  - explicit sleeps between phases so you can see what's happening
  - keystroke delay=80ms so typing is visible
  - browser stays open 10s after final step before closing

Superseded by test_openhands_live_ui_headed_v2.py which uses a longer
task so the streaming is actually visible. Kept for reference.
"""
from __future__ import annotations

import json, re, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:3000"
VLLM_METRICS = "http://127.0.0.1:8100/metrics"
ART = Path("/tmp/oh-live-ui-headed"); ART.mkdir(exist_ok=True)

def vllm_prompt_tokens():
    try:
        with urllib.request.urlopen(VLLM_METRICS, timeout=5) as r:
            for line in r.read().decode().splitlines():
                if line.startswith("vllm:prompt_tokens_total"):
                    m = re.search(r"\}\s+([\d.]+)$", line)
                    if m: return float(m.group(1))
    except Exception: pass
    return -1.0

def ensure_settings():
    payload = {"agent_settings_diff": {"agent": "CodeActAgent",
        "llm": {"model": "openai/qwen3-coder-30b-a3b-instruct-awq-4bit",
                "base_url": "http://host.docker.internal:8100/v1",
                "api_key": "none", "auth_type": "api_key"}}}
    req = urllib.request.Request(BASE + "/api/v1/settings",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=10).read()

def banner(msg):
    print(f"\n{'='*60}\n>>> {msg}\n{'='*60}")

def main():
    ensure_settings()
    baseline = vllm_prompt_tokens()
    print(f"vLLM baseline = {baseline}")
    task = "Reply with exactly the string OK-LIVE-UI-HEADED and stop."

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=False, slow_mo=400,
                               args=["--window-position=100,100", "--window-size=1440,900"])
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        banner("UI1 — load home")
        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(4000)
        page.screenshot(path=str(ART / "01_home.png"), full_page=True)

        banner("UI2 — dismiss consent if visible")
        consent = page.locator('[data-testid="confirm-preferences"]')
        if consent.count() > 0:
            consent.first.click(); page.wait_for_timeout(2000)
        page.screenshot(path=str(ART / "02_consent.png"), full_page=True)

        banner("UI3 — click New Conversation")
        page.locator('[data-testid="launch-new-conversation-button"]').first.click()
        for _ in range(30):
            page.wait_for_timeout(500)
            if "/conversations/" in page.url: break
        page.wait_for_timeout(4000)
        print(f"    URL: {page.url}")
        page.screenshot(path=str(ART / "03_conversation.png"), full_page=True)

        banner("UI4 — type task (keystrokes visibly)")
        chat = page.locator('[data-testid="chat-input"]')
        expect(chat).to_be_visible(timeout=10000)
        chat.click(); page.wait_for_timeout(1000)
        page.keyboard.type(task, delay=80)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(ART / "04_typed.png"), full_page=True)

        banner("UI5 — click submit")
        page.locator('[data-testid="submit-button"]').click()
        page.wait_for_timeout(3000)
        page.screenshot(path=str(ART / "05_submitted.png"), full_page=True)

        banner("UI6 — poll for spinner (up to 30s)")
        spinner = page.locator('[data-testid="agent-loading-spinner"]')
        for i in range(150):
            if spinner.count() > 0 and spinner.first.is_visible():
                print(f"    spinner at t+{i*0.2:.1f}s"); break
            if "OK-LIVE-UI-HEADED" in page.locator("body").inner_text():
                print("    response already in DOM, spinner missed"); break
            page.wait_for_timeout(200)
        page.screenshot(path=str(ART / "06_spinner.png"), full_page=True)

        banner("UI7 — wait for response text (up to 120s)")
        for i in range(120):
            if "OK-LIVE-UI-HEADED" in page.locator("body").inner_text():
                print(f"    ★ response found at t+{i}s"); break
            if i % 5 == 0:
                cur = vllm_prompt_tokens()
                print(f"    t+{i}s  vLLM={cur} (delta {cur-baseline:+.0f})")
            page.wait_for_timeout(1000)
        page.screenshot(path=str(ART / "07_final.png"), full_page=True)
        final = vllm_prompt_tokens()
        print(f"    FINAL delta = {final-baseline:+.0f}")

        banner("UI8 — Canvas GUI tabs")
        for name in ("planner","editor","vscode","terminal","browser"):
            found = page.locator(f'[data-testid="conversation-tab-{name}"]').count() > 0
            print(f"    tab {name:8s} : {'YES' if found else 'no'}")
        page.screenshot(path=str(ART / "08_canvas.png"), full_page=True)

        banner("holding window open for 10s")
        time.sleep(10)
        b.close()

    print(f"\nartifacts: {ART}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
