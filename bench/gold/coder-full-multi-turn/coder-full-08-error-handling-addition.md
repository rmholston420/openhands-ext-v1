# Gold rubric — coder-full-08-error-handling-addition

**Task prompt (verbatim):**
> In /workspace/repo/src/net/fetch.py, the function fetch_json(url) currently returns the parsed JSON. Wrap the URL parsing with a try/except that catches json.JSONDecodeError and re-raises it as a FetchError(url, original_exc) — a new exception class you must define at module top. The happy path (valid JSON) MUST be byte-identical in behavior and return value. Do not change fetch_json's signature. After your edits, `python -m pytest tests/ -q` must exit 0.

**Scoring model:** Perplexity-Max
**Range:** 0-100
**Locked:** post_hoc_edit_locked per ADR-0028

## Correctness criteria

- `FetchError` MUST be defined at module top (before `fetch_json`).
- `FetchError` MUST expose `.url` and `.original_exc` attributes.
- `fetch_json` signature MUST remain `fetch_json(url: str)` (or with unchanged param name).
- Happy path: `fetch_json('{"a": 1}')` MUST return `{"a": 1}` (byte-identical to original behavior).
- Error path: `fetch_json("not json")` MUST raise `FetchError` whose `.url == "not json"` and `.original_exc.__class__.__name__ == "JSONDecodeError"`.
- Smoke: `python -m pytest tests/ -q` MUST exit 0.

## Reference implementation

```python
import json


class FetchError(Exception):
    def __init__(self, url, original_exc):
        super().__init__(f"failed to parse JSON from {url}: {original_exc}")
        self.url = url
        self.original_exc = original_exc


def fetch_json(url: str):
    try:
        return json.loads(url)
    except json.JSONDecodeError as e:
        raise FetchError(url, e) from e
```

## Scoring bands

### 90-100 — Exemplary
- Both tests pass. `FetchError` class correct. Signature preserved.
- Uses `raise ... from e` for exception chaining (good practice).

### 75-89 — Correct with minor process flaws
- Tests pass but `raise FetchError(url, e)` without `from e` (missing chaining nicety).
- Extra reads or one extra smoke run.

### 60-74 — Partially correct
- `FetchError` has `.url` and `.original_exc` but is defined AFTER `fetch_json` (test still passes on import).
- OR error message wording awkward but attributes correct.

### 40-59 — Substantially incorrect
- Signature changed (added kwargs, changed param name).
- OR happy path broken (returns something wrapped).

### 20-39 — Mostly failed
- `FetchError` catches too broadly (bare `except:` re-raise as FetchError) — `.original_exc` may be wrong class.

### 0-19 — Failed
- No exception class defined.
- OR tests fail on import.

## Deductions
- −5 hit max_iter=20
- −3 dispreferred tool

## Bonuses
- +2 minimum turn count
- +2 exception chaining with `from e`
