"""Process supervisors for vLLM and llama.cpp servers.

Each server class:
  - Owns a `subprocess.Popen` for the server process.
  - Runs a stdout-reader thread that tees the server's output to:
      1. a per-cell log file at $REPO_ROOT/bench/results/server-logs/<cell_id>-<epoch>.log
      2. the runner's stdout with `[<cell_id>] ` prefix (line-buffered).
  - `wait_ready(timeout)` polls /health with a 5s heartbeat.
  - `terminate()` sends SIGTERM, waits up to 15s, escalates to SIGKILL.
  - Registers atexit + SIGINT/SIGTERM handlers so orphan processes are killed
    on any exit path.

Health-wait failures produce structured `ServerLaunchError` with:
  - reason enum: MISSING_BINARY | PORT_IN_USE | INSUFFICIENT_VRAM | STARTUP_TIMEOUT | EARLY_EXIT
  - tail of server log
so the runner can flag `runtime_version_regression` correctly per §0.1.
"""
from __future__ import annotations

import atexit
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence

from .progress import Progress

# --- Repo root ----------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# --- Exception ---------------------------------------------------------------


class LaunchFailReason(str, Enum):
    MISSING_BINARY = "missing_binary"
    MISSING_MODEL = "missing_model"
    PORT_IN_USE = "port_in_use"
    INSUFFICIENT_VRAM = "insufficient_vram"
    STARTUP_TIMEOUT = "startup_timeout"
    EARLY_EXIT = "early_exit"


@dataclass
class ServerLaunchError(Exception):
    reason: LaunchFailReason
    detail: str
    server_log_tail: str = ""

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.reason.value}] {self.detail}"


# --- Global process registry (for atexit cleanup) ----------------------------

_LIVE: list["BaseServer"] = []


def _cleanup_all(*_a) -> None:
    for srv in list(_LIVE):
        try:
            srv.terminate(silent=True)
        except Exception:
            pass


atexit.register(_cleanup_all)
signal.signal(signal.SIGINT, lambda *a: (_cleanup_all(), sys.exit(130)))
signal.signal(signal.SIGTERM, lambda *a: (_cleanup_all(), sys.exit(143)))


# --- Preflight helpers -------------------------------------------------------


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect((host, port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False


def nvidia_free_gib() -> Optional[float]:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=10,
        )
        mib = int(out.decode().strip().splitlines()[0].strip())
        return mib / 1024.0
    except (subprocess.CalledProcessError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


# --- Base server -------------------------------------------------------------


class BaseServer:
    """Common tee'd Popen + ready-wait supervisor."""

    def __init__(
        self,
        *,
        cell_id: str,
        cmd: Sequence[str],
        env: Optional[dict] = None,
        cwd: Optional[Path] = None,
        health_url: str,
        log_dir: Path,
        progress: Progress,
        min_free_vram_gib: float = 20.0,
        port: Optional[int] = None,
    ) -> None:
        self.cell_id = cell_id
        self.cmd = list(cmd)
        self.env = env
        self.cwd = cwd
        self.health_url = health_url
        self.progress = progress
        self.min_free_vram_gib = min_free_vram_gib
        self.port = port

        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = log_dir / f"{cell_id}-{int(time.time())}.log"

        self._proc: Optional[subprocess.Popen] = None
        self._tee_thread: Optional[threading.Thread] = None
        self._tee_stop = threading.Event()
        self._log_lines: list[str] = []
        self._log_lines_lock = threading.Lock()

    # -- Preflight ---------------------------------------------------------

    def _preflight_vram(self) -> None:
        free = nvidia_free_gib()
        if free is None:
            self.progress.log("PREFLIGHT",
                              f"{self.cell_id} nvidia-smi unavailable — skipping VRAM check")
            return
        self.progress.log("PREFLIGHT",
                          f"{self.cell_id} gpu_free={free:.2f} GiB "
                          f"(min={self.min_free_vram_gib:.1f})")
        if free < self.min_free_vram_gib:
            raise ServerLaunchError(
                reason=LaunchFailReason.INSUFFICIENT_VRAM,
                detail=f"gpu_free={free:.2f} GiB < min={self.min_free_vram_gib:.1f} GiB",
            )

    def _preflight_port(self) -> None:
        if self.port is not None and port_in_use(self.port):
            raise ServerLaunchError(
                reason=LaunchFailReason.PORT_IN_USE,
                detail=f"port {self.port} is already bound",
            )

    def _preflight_binary(self, path: Path, hint: str) -> None:
        if not path.exists() or not os.access(path, os.X_OK):
            raise ServerLaunchError(
                reason=LaunchFailReason.MISSING_BINARY,
                detail=f"{path} not found or not executable — {hint}",
            )

    def _preflight_path(self, path: Path, kind: str, hint: str) -> None:
        if not path.exists():
            raise ServerLaunchError(
                reason=LaunchFailReason.MISSING_MODEL,
                detail=f"{kind} not found at {path} — {hint}",
            )

    # -- Popen + tee -------------------------------------------------------

    def _spawn(self) -> None:
        self.progress.log("LAUNCH",
                          f"{self.cell_id} cmd={' '.join(shlex.quote(a) for a in self.cmd)}")
        self.progress.log("LAUNCH", f"{self.cell_id} server_log={self.log_path}")

        env = dict(os.environ)
        if self.env:
            env.update(self.env)
        env.setdefault("PYTHONUNBUFFERED", "1")

        self._proc = subprocess.Popen(
            self.cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            env=env,
            cwd=str(self.cwd) if self.cwd else None,
        )
        _LIVE.append(self)

        self._tee_thread = threading.Thread(
            target=self._tee_loop, name=f"tee-{self.cell_id}", daemon=True,
        )
        self._tee_thread.start()

    def _tee_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        try:
            with self.log_path.open("w", encoding="utf-8", buffering=1) as fh:
                for line in self._proc.stdout:
                    if self._tee_stop.is_set():
                        break
                    fh.write(line)
                    with self._log_lines_lock:
                        self._log_lines.append(line.rstrip("\n"))
                        if len(self._log_lines) > 400:
                            del self._log_lines[:200]
                    # Prefix with cell id so multi-cell interleaved output stays readable.
                    print(f"[{self.cell_id}] {line}", end="", flush=True)
        except Exception as exc:  # pragma: no cover
            self.progress.log("TEE", f"{self.cell_id} tee thread error: {exc}")

    def _log_tail(self, n: int = 60) -> str:
        with self._log_lines_lock:
            return "\n".join(self._log_lines[-n:])

    # -- Ready wait --------------------------------------------------------

    def wait_ready(self, timeout: int) -> float:
        """Poll /health until 200 or timeout. Returns elapsed cold-start seconds."""
        assert self._proc is not None
        start = time.monotonic()
        last_beat = start
        with self.progress.phase("READY", f"{self.cell_id} awaiting {self.health_url}",
                                 heartbeat_seconds=5, expected_seconds=timeout):
            while True:
                elapsed = time.monotonic() - start
                if elapsed > timeout:
                    raise ServerLaunchError(
                        reason=LaunchFailReason.STARTUP_TIMEOUT,
                        detail=f"{self.health_url} did not respond in {timeout}s",
                        server_log_tail=self._log_tail(),
                    )
                # Died mid-startup?
                rc = self._proc.poll()
                if rc is not None:
                    raise ServerLaunchError(
                        reason=LaunchFailReason.EARLY_EXIT,
                        detail=f"server exited with returncode={rc} during startup",
                        server_log_tail=self._log_tail(),
                    )
                if self._health_ok():
                    return elapsed
                # heartbeat is handled by progress.phase; sleep and retry
                time.sleep(1)

    def _health_ok(self) -> bool:
        try:
            with urllib.request.urlopen(self.health_url, timeout=2) as resp:
                return 200 <= resp.status < 300
        except (urllib.error.URLError, socket.timeout, ConnectionResetError, OSError):
            return False

    # -- Teardown ----------------------------------------------------------

    def terminate(self, *, silent: bool = False) -> None:
        if self._proc is None:
            return
        proc = self._proc
        if proc.poll() is not None:
            if not silent:
                self.progress.log("TEARDOWN",
                                  f"{self.cell_id} already exited rc={proc.returncode}")
            self._cleanup()
            return
        if not silent:
            self.progress.log("TEARDOWN", f"{self.cell_id} SIGTERM pid={proc.pid}")
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            if not silent:
                self.progress.log("TEARDOWN",
                                  f"{self.cell_id} SIGTERM ignored — escalating to SIGKILL")
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)
        self._cleanup()
        if not silent:
            self.progress.log("TEARDOWN", f"{self.cell_id} rc={proc.returncode}")

    def _cleanup(self) -> None:
        self._tee_stop.set()
        if self._tee_thread is not None:
            self._tee_thread.join(timeout=2)
        if self in _LIVE:
            _LIVE.remove(self)


# --- Concrete servers --------------------------------------------------------


class VLLMServer(BaseServer):
    """`.venv/bin/vllm serve <model_dir> --port N ...` with per-role parser flags.

    Role-flag policy per ADR-0010:
      - coder:    OpenAI-compatible tool-call API is only enabled when the
                  server is launched with `--enable-auto-tool-choice` +
                  a `--tool-call-parser` matching the model's on-the-wire
                  tool-call format. Qwen3-Thinking-2507 emits Hermes-style
                  `<tool_call>{json}</tool_call>` blocks, so we use
                  `--tool-call-parser hermes`. (The `qwen3_coder` parser
                  in vLLM 0.27 targets Qwen3-Coder's XML `<function=…>`
                  wire format and does NOT match Hermes blocks — using it
                  causes msg.tool_calls to be empty even when the model
                  emitted a well-formed call. Observed 2026-08-11.)
                  Qwen3-Thinking family additionally needs
                  `--reasoning-parser qwen3` for vLLM 0.27 to accept
                  `tool_choice="auto"` requests (otherwise every
                  /v1/chat/completions call returns HTTP 400 at
                  API-validation before touching the model).
      - planner:  `--reasoning-parser qwen3` so vLLM strips <think> blocks
                  server-side and structured-output (guided decoding) works
                  in cooperation with thinking mode.
      - embedder: no parser flags.

    Progress-visibility notes:
      - launched with `python -u -m ...`-equivalent line buffering via bufsize=1.
      - Emits `[<cell>] ` prefixed lines for every vLLM log line in real time.
    """

    # Per-role vLLM launch flags. Prepended to the caller's `extra_flags`
    # (caller flags win on any conflict via later position). See ADR-0010.
    # ADR-0011 amend 2 (2026-08-11 04:26 EDT): --reasoning-parser is no longer
    # a role default; it is per-cell via cand.reasoning_parser. Applying
    # --reasoning-parser qwen3 to a non-thinking model (Qwen3-Coder-Instruct)
    # routes its XML function-call block into the OpenAI `reasoning` field and
    # strands tool_calls empty. Thinking models must set reasoning_parser="qwen3"
    # explicitly in registry.json / candidate-file rows.
    ROLE_FLAGS: dict[str, list[str]] = {
        "coder": [
            "--enable-auto-tool-choice",
            "--tool-call-parser", "hermes",
        ],
        "planner": [
        ],
        "embedder": [],
    }

    def __init__(
        self,
        *,
        cell_id: str,
        model_dir: Path,
        port: int,
        served_name: str,
        role: str,
        progress: Progress,
        log_dir: Path,
        max_model_len: int = 32768,
        gpu_memory_utilization: float = 0.90,
        extra_flags: Optional[Sequence[str]] = None,
        min_free_vram_gib: float = 20.0,
        env: Optional[dict] = None,
    ) -> None:
        if role not in self.ROLE_FLAGS:
            raise ValueError(
                f"VLLMServer: unknown role {role!r}; "
                f"expected one of {sorted(self.ROLE_FLAGS)}"
            )
        vllm_bin = REPO_ROOT / ".venv" / "bin" / "vllm"
        cmd = [
            str(vllm_bin), "serve", str(model_dir),
            "--host", "127.0.0.1",
            "--port", str(port),
            "--max-model-len", str(max_model_len),
            "--gpu-memory-utilization", f"{gpu_memory_utilization}",
            "--served-model-name", served_name,
            "--trust-remote-code",
        ]
        # Role flags first (defaults); caller extras appended after so caller
        # can override on collision by re-specifying the same flag.
        cmd.extend(self.ROLE_FLAGS[role])
        if extra_flags:
            cmd.extend(extra_flags)

        super().__init__(
            cell_id=cell_id,
            cmd=cmd,
            env=env,
            health_url=f"http://127.0.0.1:{port}/health",
            log_dir=log_dir,
            progress=progress,
            min_free_vram_gib=min_free_vram_gib,
            port=port,
        )
        self._vllm_bin = vllm_bin
        self._model_dir = model_dir
        self.port = port
        self.served_name = served_name
        self.role = role

    def start(self) -> None:
        self._preflight_binary(self._vllm_bin,
                               "run scripts/install-vllm.sh to create .venv with vllm")
        self._preflight_path(self._model_dir / "config.json", "vLLM model dir",
                             "run scripts/pull-models.sh")
        self._preflight_port()
        self._preflight_vram()
        self._spawn()


class LlamaCppServer(BaseServer):
    """`vendor/llama.cpp/build/bin/llama-server -m <gguf> ...` with per-role flags.

    Role-flag policy per ADR-0007 §3:
      - coder/planner: uniform Qwen planner sampling preset on launch
        (`--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0`), plus KV-cache
        Q8_0 quantization and 32K ctx per spec §0.1.
      - embedder: `--embedding` mode, 4K ctx, no sampling flags.
    """

    ROLE_FLAGS = {
        "coder": [
            "-c", "32768",
            "-fa", "on",
            "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
            "--temp", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0",
        ],
        "planner": [
            "-c", "32768",
            "-fa", "on",
            "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
            "--temp", "0.6", "--top-p", "0.95", "--top-k", "20", "--min-p", "0",
        ],
        "embedder": [
            "--embedding",
            "-c", "4096",
        ],
    }

    def __init__(
        self,
        *,
        cell_id: str,
        gguf_path: Path,
        port: int,
        served_name: str,
        role: str,
        progress: Progress,
        log_dir: Path,
        ngl: int = 999,
        extra_flags: Optional[Sequence[str]] = None,
        min_free_vram_gib: float = 20.0,
    ) -> None:
        server_bin = REPO_ROOT / "vendor" / "llama.cpp" / "build" / "bin" / "llama-server"
        if role not in self.ROLE_FLAGS:
            raise ValueError(f"unknown role: {role}")
        cmd = [
            str(server_bin),
            "-m", str(gguf_path),
            "--host", "127.0.0.1",
            "--port", str(port),
            "--alias", served_name,
            "-ngl", str(ngl),
            "--jinja",
            *self.ROLE_FLAGS[role],
        ]
        if extra_flags:
            cmd.extend(extra_flags)

        super().__init__(
            cell_id=cell_id,
            cmd=cmd,
            health_url=f"http://127.0.0.1:{port}/health",
            log_dir=log_dir,
            progress=progress,
            min_free_vram_gib=min_free_vram_gib,
            port=port,
        )
        self._server_bin = server_bin
        self._gguf_path = gguf_path
        self.port = port
        self.served_name = served_name
        self.role = role

    def start(self) -> None:
        self._preflight_binary(self._server_bin,
                               "run scripts/build-llama-cpp.sh")
        self._preflight_path(self._gguf_path, "GGUF file", "run scripts/pull-models.sh")
        self._preflight_port()
        self._preflight_vram()
        self._spawn()
