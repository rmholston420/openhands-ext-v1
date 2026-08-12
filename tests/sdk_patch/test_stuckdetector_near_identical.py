"""ADR-0037 contract test — near-identical scenario in patched StuckDetector.

Verifies that the vendored+patched openhands-sdk `StuckDetector` correctly
flags near-identical tool-call sequences (whitespace/quoting/casing/
key-order/trailing-punctuation) that upstream's exact-equality
`action_observation` scenario would miss.

Runs against the installed (editable) `openhands-sdk` in the current venv,
which the vendor script keeps in sync with the sentinel-verified patched
sources under `vendor/openhands-sdk/`.
"""

from __future__ import annotations

import unittest
from typing import Any


class TestStuckDetectorNearIdentical(unittest.TestCase):
    """Contract test for ADR-0037 near-identical detection."""

    @classmethod
    def setUpClass(cls) -> None:
        # Late import so pytest collection doesn't fail if the SDK isn't
        # installed (e.g. running the wider test suite in a fresh clone).
        from openhands.sdk.conversation.stuck_detector import StuckDetector
        from openhands.sdk.conversation.types import StuckDetectionThresholds
        from openhands.sdk.event import ActionEvent
        from openhands.sdk.llm.message import MessageToolCall

        cls.StuckDetector = StuckDetector
        cls.StuckDetectionThresholds = StuckDetectionThresholds
        cls.ActionEvent = ActionEvent
        cls.MessageToolCall = MessageToolCall

    # -- sentinel: patched fields exist ------------------------------------

    def test_thresholds_has_near_identical_field(self) -> None:
        """ADR-0037 field is present with default 3."""
        thresholds = self.StuckDetectionThresholds()
        self.assertTrue(hasattr(thresholds, "near_identical"))
        self.assertEqual(thresholds.near_identical, 3)

    def test_detector_has_near_identical_threshold_property(self) -> None:
        det = self._make_detector()
        self.assertEqual(det.near_identical_threshold, 3)

    def test_detector_has_scenario_6_method(self) -> None:
        det = self._make_detector()
        self.assertTrue(hasattr(det, "_is_stuck_near_identical"))
        self.assertTrue(hasattr(det, "_adr0037_action_key"))

    # -- behavior: normalization ------------------------------------------

    def test_near_identical_whitespace_and_quotes(self) -> None:
        """Three ActionEvents with only whitespace/quote variance → stuck."""
        events = [
            self._make_action_event(
                tool_name="edit_file",
                arguments='{"path":"a.py","content":"hello"}',
            ),
            self._make_action_event(
                tool_name="edit_file",
                arguments='{"path": "a.py",  "content": "hello"}',  # spaces
            ),
            self._make_action_event(
                tool_name="EDIT_FILE",  # casing
                arguments='{"content":"HELLO","path":"a.py"}',  # key reorder + case
            ),
        ]
        det = self._make_detector()
        self.assertTrue(det._is_stuck_near_identical(events))

    def test_exact_equal_calls_also_trip(self) -> None:
        args = '{"path":"a.py","content":"hello"}'
        events = [
            self._make_action_event(tool_name="edit_file", arguments=args)
            for _ in range(3)
        ]
        det = self._make_detector()
        self.assertTrue(det._is_stuck_near_identical(events))

    def test_two_calls_do_not_trip(self) -> None:
        """Below-threshold sequences must not flag."""
        args = '{"path":"a.py","content":"hello"}'
        events = [
            self._make_action_event(tool_name="edit_file", arguments=args)
            for _ in range(2)
        ]
        det = self._make_detector()
        self.assertFalse(det._is_stuck_near_identical(events))

    def test_different_tools_do_not_trip(self) -> None:
        events = [
            self._make_action_event(
                tool_name="edit_file", arguments='{"path":"a.py"}'
            ),
            self._make_action_event(
                tool_name="read_file", arguments='{"path":"a.py"}'
            ),
            self._make_action_event(
                tool_name="run_shell", arguments='{"path":"a.py"}'
            ),
        ]
        det = self._make_detector()
        self.assertFalse(det._is_stuck_near_identical(events))

    def test_different_content_does_not_trip(self) -> None:
        events = [
            self._make_action_event(
                tool_name="edit_file", arguments='{"path":"a.py","content":"1"}'
            ),
            self._make_action_event(
                tool_name="edit_file", arguments='{"path":"a.py","content":"2"}'
            ),
            self._make_action_event(
                tool_name="edit_file", arguments='{"path":"a.py","content":"3"}'
            ),
        ]
        det = self._make_detector()
        self.assertFalse(det._is_stuck_near_identical(events))

    def test_trailing_punctuation_normalized(self) -> None:
        """Trailing punctuation on string scalars is stripped."""
        events = [
            self._make_action_event(
                tool_name="run_shell", arguments='{"cmd":"ls -la"}'
            ),
            self._make_action_event(
                tool_name="run_shell", arguments='{"cmd":"ls -la."}'
            ),
            self._make_action_event(
                tool_name="run_shell", arguments='{"cmd":"ls -la!"}'
            ),
        ]
        det = self._make_detector()
        self.assertTrue(det._is_stuck_near_identical(events))

    # -- helpers -----------------------------------------------------------

    def _make_detector(self):
        """Instantiate a StuckDetector against a minimal in-memory state.

        We can't easily build a real ConversationState in a unit test, so
        we bypass it: `_is_stuck_near_identical` and its helpers do not
        touch `self.state`, so a stub with just `thresholds` is enough.
        """
        det = self.StuckDetector.__new__(self.StuckDetector)
        det.state = None  # unused by the ADR-0037 code path
        det.thresholds = self.StuckDetectionThresholds()
        return det

    def _make_action_event(self, *, tool_name: str, arguments: str) -> Any:
        """Build a minimal ActionEvent carrying an SDK `MessageToolCall`
        with the given `arguments` JSON string.

        `MessageToolCall` is the SDK's transport-agnostic wrapper (flat
        `arguments: str` field), not litellm's `ChatCompletionMessageToolCall`
        (nested `.function.arguments`). ADR-0037 reads `tool_call.arguments`
        directly, matching every other consumer in the SDK
        (security/toolshield_llm_analyzer, defense_in_depth, grayswan).

        Uses Pydantic's `model_construct` on the ActionEvent to skip full
        validation for fields ADR-0037 does not touch (`action`, thought).
        """
        tool_call = self.MessageToolCall(
            id=f"call_{tool_name}_{abs(hash(arguments)) % 10_000}",
            name=tool_name,
            arguments=arguments,
            origin="completion",
        )
        evt = self.ActionEvent.model_construct(
            source="agent",
            tool_name=tool_name,
            tool_call=tool_call,
            action=None,  # unused by ADR-0037 code path
            thought=[],
            tool_call_id=tool_call.id,
        )
        return evt


if __name__ == "__main__":
    unittest.main()
