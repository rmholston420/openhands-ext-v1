"""Line-buffered timestamped progress printer (ADR-0007 §7).

Contract:
- Every meaningful step emits one line with:
    [YYYY-MM-DD HH:MM:SS TZ] [<i>/<N>] <phase>: <detail>
- Any phase expected to run > ~15s must emit a heartbeat every 5s with
  elapsed seconds.
- All output is flushed immediately (no buffering).
- No `subprocess.run(..., capture_output=True)` without a tee.
"""
from __future__ import annotations

import contextlib
import os
import sys
import threading
import time
from datetime import datetime
from typing import Iterator, Optional

# America/Detroit per project instructions. Use system tzdata when available;
# fall back to fixed EDT/EST offset only if zoneinfo is unavailable.
try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("America/Detroit")
except Exception:  # pragma: no cover
    _TZ = None


def _now_stamp() -> str:
    if _TZ is not None:
        return datetime.now(tz=_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Progress:
    """Progress printer with [i/N] counters and heartbeat threads."""

    def __init__(self, *, total_cells: int, stream=sys.stdout) -> None:
        self.total = total_cells
        self.stream = stream
        self._cell_i = 0

    # --- Cell counter ---------------------------------------------------

    def start_cell(self, label: str) -> None:
        self._cell_i += 1
        self.log("CELL", f"[{self._cell_i}/{self.total}] START {label}")

    def end_cell(self, label: str, *, verdict: str) -> None:
        self.log("CELL", f"[{self._cell_i}/{self.total}] END   {label} verdict={verdict}")

    # --- Generic log line ----------------------------------------------

    def log(self, phase: str, detail: str) -> None:
        line = f"[{_now_stamp()}] {phase}: {detail}"
        print(line, file=self.stream, flush=True)

    # --- Heartbeat context manager -------------------------------------

    @contextlib.contextmanager
    def phase(self, phase: str, detail: str, *, heartbeat_seconds: int = 5,
              expected_seconds: Optional[int] = None) -> Iterator[None]:
        """Wrap a long phase with an entry/exit line and a heartbeat thread.

        If `expected_seconds` is provided, includes it in the entry line so
        the user sees the expected duration up front.
        """
        entry = detail
        if expected_seconds is not None:
            entry = f"{detail} (expected ~{expected_seconds}s)"
        self.log(phase, f"START {entry}")

        stop = threading.Event()
        started = time.monotonic()

        def _tick() -> None:
            # First heartbeat delayed by heartbeat_seconds so quick phases stay quiet.
            while not stop.wait(heartbeat_seconds):
                elapsed = int(time.monotonic() - started)
                self.log(phase, f"... still running, elapsed={elapsed}s")

        t = threading.Thread(target=_tick, name=f"hb-{phase}", daemon=True)
        t.start()
        try:
            yield
        finally:
            stop.set()
            t.join(timeout=2)
            total = int(time.monotonic() - started)
            self.log(phase, f"END   {entry} elapsed={total}s")


def enforce_unbuffered_env() -> None:
    """Set PYTHONUNBUFFERED=1 for any Python subprocess we spawn."""
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
