"""
OpenHands full-suite smoke test v3 — 2026-08-11.

Changes vs v2:
  - T3 is now pure API: POST settings (agent_settings_diff), then POST
    /api/v1/app-conversations/stream-start with initial_message.
    Playwright is only used for T1 (frontend loads).
  - Adds T5: conversation actually produced an agent event.

Prerequisites (Colossus):
  - openhands-app container running on :3000 with isolated mount and
    `--add-host host.docker.internal:host-gateway`.
  - coder vLLM on host :8100 (bound 0.0.0.0), embedder on :8090.
  - UFW rule: `sudo ufw allow from 172.17.0.0/16 to any` — required so
    docker-bridge containers can reach host-published ports. Without it,
    the sandbox healthcheck from openhands-app to the child sandbox port
    (host.docker.internal:PUBLISHED) times out and the start-task ERRORs.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

BASE = "http://127.0.0.1:3000"
VLLM_METRICS = "http://127.0.0.1:8100/metrics"
ARTIFACTS = Path("/tmp/oh-smoke-artifacts-v3")
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def _http(url: str, method: str = "GET", data=None, timeout=30):
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace"), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace"), e.headers.get("Content-Type", "")
    except Exception as e:
        return 0, f"ERROR: {e}", ""


def _vllm_prompt_tokens() -> float:
    code, body, _ = _http(VLLM_METRICS)
    if code != 200:
        return -1.0
    for line in body.splitlines():
        if line.startswith("vllm:prompt_tokens_total"):
            m = re.search(r"\}\s+([\d.]+)$", line)
            if m:
                return float(m.group(1))
    return -1.0


def t1_frontend(page: Page) -> dict:
    resp = page.goto(BASE + "/", wait_until="domcontentloaded", timeout=15000)
    time.sleep(2)
    page.screenshot(path=str(ARTIFACTS / "T1_frontend.png"), full_page=True)
    return {
        "test": "T1_frontend_loads",
        "http_status": resp.status if resp else None,
        "title": page.title(),
        "pass": (resp is not None and resp.status == 200 and page.title() == "OpenHands"),
    }


def t2_backend_json() -> dict:
    probes = {}
    for path in ["/api/v1/settings", "/api/v1/app-conversations/search?limit=1", "/health"]:
        code, body, ct = _http(BASE + path)
        probes[path] = {
            "code": code,
            "content_type": ct,
            "is_json": "json" in ct.lower(),
            "body_prefix": body[:150],
        }
    return {
        "test": "T2_backend_json",
        "probes": probes,
        "pass": all(p["is_json"] for p in probes.values()),
    }


def t3_configure_and_launch() -> dict:
    """POST settings, POST stream-start, verify HTTP-level success."""
    result = {"test": "T3_configure_and_launch", "steps": [], "pass": False}

    settings_payload = {
        "agent_settings_diff": {
            "agent": "CodeActAgent",
            "llm": {
                "model": "openai/qwen3-coder-30b-a3b-instruct-awq-4bit",
                "base_url": "http://host.docker.internal:8100/v1",
                "api_key": "none",
                "auth_type": "api_key",
            }
        }
    }
    code, body, _ = _http(BASE + "/api/v1/settings", method="POST", data=settings_payload)
    result["steps"].append({"post_settings": {"code": code, "body": body[:200]}})
    if code >= 400:
        return result

    conv_id = str(uuid.uuid4())
    task_text = "Reply with exactly the string OK-SMOKE-2026 and nothing else."
    start_payload = {
        "conversation_id": conv_id,
        "initial_message": {
            "role": "user",
            "content": [{"type": "text", "text": task_text}],
            "run": True,
        },
        "title": "Smoke test 2026-08-11",
    }
    code, body, _ = _http(BASE + "/api/v1/app-conversations/stream-start", method="POST", data=start_payload)
    result["steps"].append({"post_stream_start": {"code": code, "body": body[:500]}})
    result["conversation_id"] = conv_id
    if code < 400:
        result["pass"] = True
    return result


def t4_coder_delta(baseline: float) -> dict:
    now = _vllm_prompt_tokens()
    return {
        "test": "T4_coder_delta",
        "baseline_prompt_tokens": baseline,
        "current_prompt_tokens": now,
        "delta": now - baseline if now >= 0 and baseline >= 0 else None,
        "pass": (now > baseline and baseline >= 0),
    }


def t5_conversation_produced_events(conversation_id: str) -> dict:
    """T5: The conversation should have produced at least one event."""
    if not conversation_id:
        return {"test": "T5_events_produced", "pass": False, "reason": "no conversation_id"}
    code, body, _ = _http(BASE + f"/api/v1/conversation/{conversation_id}/events/count")
    try:
        parsed = json.loads(body)
        count = parsed if isinstance(parsed, int) else parsed.get("count", 0)
    except Exception:
        count = 0
    return {
        "test": "T5_events_produced",
        "conversation_id": conversation_id,
        "http_code": code,
        "event_count": count,
        "response_body": body[:200],
        "pass": (code == 200 and count > 0),
    }


def main() -> int:
    baseline = _vllm_prompt_tokens()
    print(f"vLLM baseline prompt_tokens_total = {baseline}")

    results = []
    conv_id = None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        results.append(t1_frontend(page))
        browser.close()

    results.append(t2_backend_json())
    r3 = t3_configure_and_launch()
    results.append(r3)
    conv_id = r3.get("conversation_id")

    print("waiting 60s for agent to spin up sandbox + hit coder...")
    time.sleep(60)

    results.append(t4_coder_delta(baseline))
    results.append(t5_conversation_produced_events(conv_id))

    out = ARTIFACTS / "results.json"
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    passed = sum(1 for r in results if r.get("pass"))
    total = len(results)
    print(f"\n===== SMOKE v3 RESULT: {passed}/{total} PASS =====")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
