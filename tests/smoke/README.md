# tests/smoke — OpenHands full-suite smoke

## test_openhands_suite_v3.py

Live end-to-end proof that OpenHands + coder + embedder are wired up correctly on Colossus.

### 5 test cases

| # | Name | Check |
|---|------|-------|
| T1 | frontend_loads | GET :3000 returns 200 with title "OpenHands" |
| T2 | backend_json | 3 API probes all return `application/json` |
| T3 | configure_and_launch | POST settings + POST stream-start return 2xx |
| T4 | coder_delta | vLLM `prompt_tokens_total` increases after conversation start |
| T5 | events_produced | conversation has > 0 events after 60s |

### Prerequisites

1. openhands-app container up on :3000, isolated mount (see BUILD_LOG 2026-08-11 07:47 EDT).
2. coder vLLM bound `0.0.0.0:8100`, embedder on `:8090`.
3. UFW rule allowing docker bridge → host: `sudo ufw allow from 172.17.0.0/16 to any`. Without it, sandbox health-check fails and T4/T5 error (see DEBUG_LOG 2026-08-11 08:11 EDT).
4. Playwright installed in project venv: `pip install playwright && playwright install chromium`.

### Run

```bash
cd ~/dev/openhands-ext-v1
source .venv/bin/activate
python tests/smoke/test_openhands_suite_v3.py
```

Artifacts: `/tmp/oh-smoke-artifacts-v3/`.

### Baseline (2026-08-11 08:12 EDT)

5/5 PASS · T4 delta = 18113 prompt tokens · T5 event_count = 20.
