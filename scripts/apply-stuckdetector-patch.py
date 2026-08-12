#!/usr/bin/env python3
"""ADR-0037 — near-identical loop-guard patch for openhands-sdk StuckDetector.

Applies an idempotent transform on the vendored openhands-sdk tree at
`vendor/openhands-sdk/openhands-sdk/openhands/sdk/conversation/{types.py, stuck_detector.py}`.

This is a Python transformer rather than a unified diff (cf. ADR-0034
which used `patches/*.patch`) because the ADR-0037 change touches two
files at five anchor points; string-anchored edits are more robust than
line-anchored hunks.

Invariants:
- Idempotent: running twice is a no-op (all anchor edits check for the
  presence of ADR-0037 sentinels before applying).
- Fail-loud: if any anchor signature is missing (upstream drift), we exit
  non-zero rather than producing a partially-patched tree.
- Load-bearing sentinels ("ADR-0037" markers) are verified in
  `scripts/vendor-openhands-sdk.sh` after this script runs.

Usage:
    python3 scripts/apply-stuckdetector-patch.py <vendor_dir>

`vendor_dir` is the top-level vendored tree, e.g.
`vendor/openhands-sdk/`. This script resolves the nested
`openhands-sdk/openhands/sdk/conversation/` path itself.
"""

from __future__ import annotations

import sys
from pathlib import Path


ADR = "ADR-0037"
NEAR_IDENTICAL_FIELD_MARKER = "# ADR-0037: near-identical repetition (Phase 9 Loop Guard)"
SCENARIO_MARKER = "# scenario 6 (ADR-0037): near-identical repetition"
IMPORT_MARKER = "# ADR-0037 (Phase 9 Loop Guard): near-identical arg normalization"


# ---------------------------------------------------------------------------
# types.py transform: add `near_identical` field to StuckDetectionThresholds
# ---------------------------------------------------------------------------

TYPES_ANCHOR = (
    "    alternating_pattern: int = Field(\n"
    '        default=6, ge=1, description="Threshold for alternating pattern detection"\n'
    "    )\n"
)

TYPES_INSERTION = (
    "    alternating_pattern: int = Field(\n"
    '        default=6, ge=1, description="Threshold for alternating pattern detection"\n'
    "    )\n"
    f"    {NEAR_IDENTICAL_FIELD_MARKER}.\n"
    "    # Catches tool-call sequences whose arguments differ only in\n"
    "    # whitespace/quoting/casing/key-order/trailing-punctuation. Upstream's\n"
    "    # existing `action_observation` scenario uses exact `Action` equality via\n"
    "    # `_event_eq`, which misses these cases.\n"
    "    near_identical: int = Field(\n"
    "        default=3, ge=1,\n"
    '        description="Threshold for near-identical tool-call repetition detection (ADR-0037)",\n'
    "    )\n"
)


def patch_types_py(path: Path) -> str:
    """Return the new content for types.py after applying ADR-0037.

    Idempotent: if the marker is already present, return the original.
    """
    text = path.read_text()
    if NEAR_IDENTICAL_FIELD_MARKER in text:
        return text  # already patched
    if TYPES_ANCHOR not in text:
        raise SystemExit(
            f"FAIL: types.py anchor missing — upstream shape changed?\n"
            f"  file: {path}\n"
            f"  expected anchor:\n{TYPES_ANCHOR!r}"
        )
    return text.replace(TYPES_ANCHOR, TYPES_INSERTION, 1)


# ---------------------------------------------------------------------------
# stuck_detector.py transform: 5 anchored edits
# ---------------------------------------------------------------------------

# 1) Add imports at the top of the file, right after the existing SDK imports.
IMPORT_ANCHOR = "from openhands.sdk.conversation.state import ConversationState\n"

IMPORT_INSERTION = (
    "import json\n"
    "import re\n"
    "\n"
    "from openhands.sdk.conversation.state import ConversationState\n"
)

# 2) Add module-level regex constants right after the `logger =` line.
LOGGER_ANCHOR = "logger = get_logger(__name__)\n"

LOGGER_INSERTION = (
    "logger = get_logger(__name__)\n"
    "\n"
    "\n"
    f"{IMPORT_MARKER} regex.\n"
    "# Collapses whitespace runs so JSON-arg strings that differ only by\n"
    "# indentation/newlines/spacing normalize to the same token stream.\n"
    '_ADR0037_WHITESPACE_RE = re.compile(r"\\s+")\n'
    "# Strip trailing punctuation agents commonly toggle between retries.\n"
    "_ADR0037_TRAILING_PUNCT_RE = re.compile(r\"[.\\s,;:!?\\\"'`]+$\")\n"
)

# 3) Add the `near_identical_threshold` property right after
#    `alternating_pattern_threshold`.
PROPERTY_ANCHOR = (
    "    @property\n"
    "    def alternating_pattern_threshold(self) -> int:\n"
    "        return self.thresholds.alternating_pattern\n"
)

PROPERTY_INSERTION = (
    "    @property\n"
    "    def alternating_pattern_threshold(self) -> int:\n"
    "        return self.thresholds.alternating_pattern\n"
    "\n"
    "    # ADR-0037: near-identical repetition threshold.\n"
    "    @property\n"
    "    def near_identical_threshold(self) -> int:\n"
    "        return self.thresholds.near_identical\n"
)

# 4) Add the new scenario branch inside `is_stuck()`, right after the
#    action_error check and before the monologue check.
SCENARIO_ANCHOR = (
    "        # scenario 2: same action, errors\n"
    "        if self._is_stuck_repeating_action_error(last_actions, last_observations):\n"
    "            return True\n"
    "\n"
    "        # scenario 3: monologue\n"
)

SCENARIO_INSERTION = (
    "        # scenario 2: same action, errors\n"
    "        if self._is_stuck_repeating_action_error(last_actions, last_observations):\n"
    "            return True\n"
    "\n"
    f"        {SCENARIO_MARKER}\n"
    "        if self._is_stuck_near_identical(last_actions):\n"
    "            return True\n"
    "\n"
    "        # scenario 3: monologue\n"
)

# 5) Append the new `_is_stuck_near_identical` method + canonicalizer at
#    end of file. We anchor on the closing "return event1 == event2" of
#    `_event_eq` (last line of the class body).
TAIL_ANCHOR = "        # Default fallback\n        return event1 == event2\n"

TAIL_INSERTION = (
    "        # Default fallback\n"
    "        return event1 == event2\n"
    "\n"
    "    # ADR-0037: near-identical repetition detection (Phase 9 Loop Guard).\n"
    "    def _is_stuck_near_identical(self, last_actions: list) -> bool:\n"
    '        """Flag when N consecutive ActionEvents call the same tool with\n'
    "        near-identical arguments (whitespace/quoting/casing/key-order/trailing\n"
    "        punctuation collapsed).\n"
    "\n"
    "        Complements upstream's `_is_stuck_repeating_action_observation`, which\n"
    "        uses exact `Action` equality via `_event_eq` and misses agents that\n"
    "        retry with only cosmetic arg reformatting.\n"
    "\n"
    "        See ADR-0037.\n"
    '        """\n'
    "        threshold = self.near_identical_threshold\n"
    "        if len(last_actions) < threshold:\n"
    "            return False\n"
    "\n"
    "        window = last_actions[:threshold]\n"
    "        if not all(isinstance(a, ActionEvent) for a in window):\n"
    "            return False\n"
    "\n"
    "        first = window[0]\n"
    "        assert isinstance(first, ActionEvent)\n"
    "        first_key = self._adr0037_action_key(first)\n"
    "        if first_key is None:\n"
    "            return False\n"
    "\n"
    "        for a in window[1:]:\n"
    "            assert isinstance(a, ActionEvent)\n"
    "            if a.source != first.source:\n"
    "                return False\n"
    "            k = self._adr0037_action_key(a)\n"
    "            if k is None or k != first_key:\n"
    "                return False\n"
    "\n"
    "        logger.warning(\n"
    '            "Near-identical action loop detected (ADR-0037): tool=%s, n=%d",\n'
    "            first.tool_name,\n"
    "            threshold,\n"
    "        )\n"
    "        return True\n"
    "\n"
    "    @staticmethod\n"
    "    def _adr0037_action_key(event):\n"
    '        """Normalize (tool_name, arguments) into a comparable key.\n'
    "\n"
    "        Uses `tool_call.arguments` (the raw JSON string emitted by the LLM)\n"
    "        as the arg surface — this is where cosmetic variance actually lives.\n"
    "        Falls back to a whitespace-normalized string on unparseable JSON.\n"
    '        """\n'
    '        tool_name = (event.tool_name or "").strip().lower()\n'
    "        raw = event.tool_call.arguments if event.tool_call is not None else None\n"
    "        if raw is None:\n"
    "            return None\n"
    "        try:\n"
    "            parsed = json.loads(raw)\n"
    "        except (ValueError, TypeError):\n"
    '            norm = _ADR0037_WHITESPACE_RE.sub(" ", raw).strip().lower()\n'
    '            norm = _ADR0037_TRAILING_PUNCT_RE.sub("", norm)\n'
    '            return (tool_name, "raw:" + norm)\n'
    "        canonical = json.dumps(\n"
    "            _adr0037_canonicalize(parsed),\n"
    "            sort_keys=True,\n"
    '            separators=(",", ":"),\n'
    "        )\n"
    "        return (tool_name, canonical)\n"
    "\n"
    "\n"
    "# ADR-0037: deep string-scalar case-fold + whitespace/trailing-punct strip.\n"
    "def _adr0037_canonicalize(obj):\n"
    "    if isinstance(obj, str):\n"
    '        norm = _ADR0037_WHITESPACE_RE.sub(" ", obj).strip().lower()\n'
    '        norm = _ADR0037_TRAILING_PUNCT_RE.sub("", norm)\n'
    "        return norm\n"
    "    if isinstance(obj, list):\n"
    "        return [_adr0037_canonicalize(x) for x in obj]\n"
    "    if isinstance(obj, tuple):\n"
    "        return tuple(_adr0037_canonicalize(x) for x in obj)\n"
    "    if isinstance(obj, dict):\n"
    "        return {k: _adr0037_canonicalize(v) for k, v in obj.items()}\n"
    "    return obj\n"
)


def patch_stuck_detector_py(path: Path) -> str:
    """Return the new content for stuck_detector.py after applying ADR-0037.

    Idempotent: if the sentinel is already present, return the original.
    Fail-loud on missing anchors.
    """
    text = path.read_text()
    if SCENARIO_MARKER in text:
        return text  # already patched

    anchors = [
        ("import block", IMPORT_ANCHOR, IMPORT_INSERTION),
        ("logger + regex", LOGGER_ANCHOR, LOGGER_INSERTION),
        ("threshold property", PROPERTY_ANCHOR, PROPERTY_INSERTION),
        ("is_stuck scenario 6", SCENARIO_ANCHOR, SCENARIO_INSERTION),
        ("tail methods", TAIL_ANCHOR, TAIL_INSERTION),
    ]
    for label, anchor, insertion in anchors:
        if anchor not in text:
            raise SystemExit(
                f"FAIL: stuck_detector.py anchor missing — upstream shape changed?\n"
                f"  file: {path}\n"
                f"  anchor label: {label}\n"
                f"  expected:\n{anchor!r}"
            )
        text = text.replace(anchor, insertion, 1)
    return text


# ---------------------------------------------------------------------------


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <vendor_dir>", file=sys.stderr)
        return 2
    vendor_dir = Path(sys.argv[1]).resolve()
    if not vendor_dir.is_dir():
        print(f"FAIL: vendor_dir not found: {vendor_dir}", file=sys.stderr)
        return 2

    conv_dir = vendor_dir / "openhands-sdk" / "openhands" / "sdk" / "conversation"
    types_py = conv_dir / "types.py"
    stuck_py = conv_dir / "stuck_detector.py"

    for p in (types_py, stuck_py):
        if not p.is_file():
            print(f"FAIL: expected file missing: {p}", file=sys.stderr)
            return 2

    new_types = patch_types_py(types_py)
    new_stuck = patch_stuck_detector_py(stuck_py)

    if new_types != types_py.read_text():
        types_py.write_text(new_types)
        print(f"OK: patched {types_py.name} (ADR-0037: near_identical field)")
    else:
        print(f"OK: {types_py.name} already patched (idempotent no-op)")

    if new_stuck != stuck_py.read_text():
        stuck_py.write_text(new_stuck)
        print(f"OK: patched {stuck_py.name} (ADR-0037: scenario 6)")
    else:
        print(f"OK: {stuck_py.name} already patched (idempotent no-op)")

    print(f"OK: ADR-0037 patch applied to {vendor_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
