"""
Headed live UI smoke v2 — WATCH REAL STREAMING IN REAL TIME.

Canonical live-UI test. Improvements over v1:
  - Task is a multi-step coding job (write file, run it, show output)
    so the agent takes 15-40s and streaming is visibly incremental
  - Prints body_chars + vLLM generation_tokens every 1s so you can see
    growth in the terminal alongside the browser window
  - Screenshots every 3s during streaming (stream_00.png ... stream_27.png)
  - Auto-clicks the terminal tab and editor tab at the end so screenshots
    capture what the agent did (file written, commands run)
  - Stops when both body-chars and gen-tokens have been stable for 10s

Baseline run 2026-08-11 08:30 EDT on Colossus (DISPLAY=:0):
  prompt_tokens delta:     +74565
  generation_tokens delta: +931
  body_chars: 838 → 3598 in visible steps
  natural stop at t+28.5s
  terminal + editor tab screenshots captured

Prerequisites:
  - openhands-app on :3000
  - coder vLLM on :8100
  - X display available for headless=False (or use xvfb-run)
"""
from __future__ import annotations

import json, re, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:3000"
VLLM_METRICS = "http://127.0.0.1:8100/metrics"
ART = Path("/tmp/oh-live-ui-headed-v2"); ART.mkdir(exist_ok=True)

def _vllm_metric(name):
    try:
        with urllib.request.urlopen(VLLM_METRICS, timeout=5) as r:
            for line in r.read().decode().splitlines():
                if line.startswith(f"vllm:{name}"):
                    m = re.search(r"\}\s+([\d.]+)$", line)
                    if m: return float(m.group(1))
    except Exception: pass
    return -1.0

def vllm_prompt_tokens(): return _vllm_metric("prompt_tokens_total")
def vllm_gen_tokens():    return _vllm_metric("generation_tokens_total")

def ensure_settings():
    p = {"agent_settings_diff": {"agent": "CodeActAgent",
        "llm": {"model": "openai/qwen3-coder-30b-a3b-instruct-awq-4bit",
                "base_url": "http://host.docker.internal:8100/v1",
                "api_key": "none", "auth_type": "api_key"}}}
    req = urllib.request.Request(BASE + "/api/v1/settings",
        data=json.dumps(p).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=10).read()

def banner(m): print(f"\n{'='*60}\n>>> {m}\n{'='*60}")

def main():
    ensure_settings()
    p0 = vllm_prompt_tokens(); g0 = vllm_gen_tokens()
    print(f"vLLM baseline  prompt={p0}  generation={g0}")

    task = ("Write a Python file at /workspace/fizzbuzz_extended.py that defines "
            "a function fizzbuzz_extended(n) which for i in range(1, n+1) prints: "
            "'FizzBuzz' if divisible by both 3 and 5, 'Fizz' if by 3, 'Buzz' if by 5, "
            "'Prime' if i is prime, otherwise the number itself. Include a docstring, "
            "type hints, and a __main__ block that calls fizzbuzz_extended(30). "
            "After creating the file, run it and show me the output.")

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=False, slow_mo=300,
                               args=["--window-position=100,100", "--window-size=1440,900"])
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        banner("UI1 — load home")
        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        page.screenshot(path=str(ART / "01_home.png"), full_page=True)

        banner("UI2 — dismiss consent")
        c = page.locator('[data-testid="confirm-preferences"]')
        if c.count() > 0: c.first.click(); page.wait_for_timeout(2000)

        banner("UI3 — new conversation")
        page.locator('[data-testid="launch-new-conversation-button"]').first.click()
        for _ in range(30):
            page.wait_for_timeout(500)
            if "/conversations/" in page.url: break
        page.wait_for_timeout(3000)
        print(f"    URL: {page.url}")
        page.screenshot(path=str(ART / "03_conversation.png"), full_page=True)

        banner("UI4 — type task")
        chat = page.locator('[data-testid="chat-input"]')
        expect(chat).to_be_visible(timeout=10000)
        chat.click(); page.wait_for_timeout(1000)
        page.keyboard.type(task, delay=25)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(ART / "04_typed.png"), full_page=True)

        banner("UI5 — submit")
        page.locator('[data-testid="submit-button"]').click()
        submit_time = time.time()
        page.wait_for_timeout(1000)
        page.screenshot(path=str(ART / "05_submitted.png"), full_page=True)

        banner("UI6 — WATCH STREAMING (60s max, screenshot every 3s)")
        prev_len = 0
        prev_gen = g0
        stable = 0
        for i in range(60):
            elapsed = time.time() - submit_time
            body = page.locator("body").inner_text()
            cur_len = len(body)
            cur_gen = vllm_gen_tokens()
            growth = cur_len - prev_len
            gen_delta = cur_gen - prev_gen
            print(f"    t+{elapsed:5.1f}s  body_chars={cur_len:6d} (+{growth:4d})  gen_tokens={cur_gen:.0f} (+{gen_delta:.0f})")
            if i % 3 == 0:
                page.screenshot(path=str(ART / f"stream_{i:02d}.png"), full_page=True)
            if growth == 0 and gen_delta == 0:
                stable += 1
                if stable >= 10:
                    print(f"    stable for 10s at t+{elapsed:.1f}s — done")
                    break
            else:
                stable = 0
            prev_len = cur_len
            prev_gen = cur_gen
            page.wait_for_timeout(1000)

        page.screenshot(path=str(ART / "final.png"), full_page=True)
        p1 = vllm_prompt_tokens(); g1 = vllm_gen_tokens()
        print(f"\n=== TOTALS ===")
        print(f"prompt_tokens_delta:     {p1-p0:+.0f}")
        print(f"generation_tokens_delta: {g1-g0:+.0f}")

        banner("UI7 — terminal tab")
        try:
            page.locator('[data-testid="conversation-tab-terminal"]').click()
            page.wait_for_timeout(3000)
            page.screenshot(path=str(ART / "07_terminal_tab.png"), full_page=True)
        except Exception as e:
            print(f"    terminal tab error: {e}")

        banner("UI8 — editor tab")
        try:
            page.locator('[data-testid="conversation-tab-editor"]').click()
            page.wait_for_timeout(3000)
            page.screenshot(path=str(ART / "08_editor_tab.png"), full_page=True)
        except Exception as e:
            print(f"    editor tab error: {e}")

        banner("holding window open for 15s")
        time.sleep(15)
        b.close()

    print(f"\nartifacts in {ART}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
