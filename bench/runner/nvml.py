"""Background NVML GPU-envelope sampler for Category 3 (§0.0c).

Contract:
  Sampler(gpu_index=0, interval_ms=250).start(); ... .stop().result() -> GpuEnvelope

Coverage tracking:
  Every sample tick that succeeds increments `samples`. Every tick that fails
  (NVML transient error, driver hiccup) increments `failed_samples`. Final
  `nvml_coverage_pct = 100 * samples / (samples + failed_samples)`.

Throttle detection:
  Reads `nvmlDeviceGetCurrentClocksThrottleReasons`. Any bit set other than
  `nvmlClocksThrottleReasonGpuIdle`/`nvmlClocksThrottleReasonNone` counts as a
  throttle event (edge-triggered — count transitions into a throttled state,
  not sustained throttling).

Graceful degradation:
  If `pynvml` is not importable, the sampler runs in a no-op mode that returns
  a GpuEnvelope with `nvml_coverage_pct=0.0` and zeros elsewhere. The runner
  logs a warning; per spec §0.0c category 3, downstream Medium-tier scoring
  must refuse to accept envelopes with <95% coverage.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from bench.schema import GpuEnvelope


try:
    import pynvml  # type: ignore
    _NVML_AVAILABLE = True
except ImportError:  # pragma: no cover
    pynvml = None  # type: ignore
    _NVML_AVAILABLE = False


@dataclass
class _Samples:
    vram_mib: list[float] = field(default_factory=list)
    temp_c: list[float] = field(default_factory=list)
    power_w: list[float] = field(default_factory=list)
    util_pct: list[float] = field(default_factory=list)
    samples: int = 0
    failed_samples: int = 0
    throttle_events: int = 0
    vram_usable_mib: float = 0.0
    throttle_ceiling_c: Optional[float] = None


class NvmlSampler:
    def __init__(self, *, gpu_index: int = 0, interval_ms: int = 250) -> None:
        self.gpu_index = gpu_index
        self.interval = interval_ms / 1000.0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._samples = _Samples()
        self._handle = None
        self._in_throttle = False

    def start(self) -> None:
        if not _NVML_AVAILABLE:
            return
        try:
            pynvml.nvmlInit()
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(self.gpu_index)
            mem = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
            self._samples.vram_usable_mib = mem.total / (1024 * 1024)
            try:
                self._samples.throttle_ceiling_c = float(
                    pynvml.nvmlDeviceGetTemperatureThreshold(
                        self._handle, pynvml.NVML_TEMPERATURE_THRESHOLD_SLOWDOWN
                    )
                )
            except Exception:
                pass
        except Exception:
            self._handle = None
            return

        self._thread = threading.Thread(target=self._loop, name="nvml-sampler", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        assert self._handle is not None
        NONE = pynvml.nvmlClocksThrottleReasonNone
        IDLE = pynvml.nvmlClocksThrottleReasonGpuIdle
        BENIGN = NONE | IDLE
        while not self._stop.is_set():
            try:
                mem = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
                temp = pynvml.nvmlDeviceGetTemperature(self._handle, pynvml.NVML_TEMPERATURE_GPU)
                # Power is in mW.
                power_mw = pynvml.nvmlDeviceGetPowerUsage(self._handle)
                util = pynvml.nvmlDeviceGetUtilizationRates(self._handle).gpu
                reasons = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(self._handle)

                self._samples.vram_mib.append(mem.used / (1024 * 1024))
                self._samples.temp_c.append(float(temp))
                self._samples.power_w.append(power_mw / 1000.0)
                self._samples.util_pct.append(float(util))
                self._samples.samples += 1

                throttled = (reasons & ~BENIGN) != 0
                if throttled and not self._in_throttle:
                    self._samples.throttle_events += 1
                    self._in_throttle = True
                elif not throttled and self._in_throttle:
                    self._in_throttle = False
            except Exception:
                self._samples.failed_samples += 1
            time.sleep(self.interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        if _NVML_AVAILABLE and self._handle is not None:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass

    def result(self) -> GpuEnvelope:
        s = self._samples
        total = s.samples + s.failed_samples
        cov = (100.0 * s.samples / total) if total > 0 else 0.0

        def _peak(v: list[float]) -> float: return max(v) if v else 0.0
        def _avg(v: list[float]) -> float: return (sum(v) / len(v)) if v else 0.0

        return GpuEnvelope(
            vram_peak_mib=_peak(s.vram_mib),
            vram_avg_mib=_avg(s.vram_mib),
            vram_usable_mib=s.vram_usable_mib,
            temp_peak_c=_peak(s.temp_c),
            temp_avg_c=_avg(s.temp_c),
            power_peak_w=_peak(s.power_w),
            power_avg_w=_avg(s.power_w),
            util_avg_pct=_avg(s.util_pct),
            nvml_coverage_pct=cov,
            throttle_events=s.throttle_events,
            cuda_oom_events=0,  # runner increments this if it observes CUDA OOM
            throttle_ceiling_c=s.throttle_ceiling_c,
        )


def nvml_available() -> bool:
    return _NVML_AVAILABLE
