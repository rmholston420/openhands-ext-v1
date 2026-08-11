"""Phase 0 benchmark record dataclasses (v16 §0.0c).

Every benchmark cell emits one `BenchRun` instance, serialized to JSON via
`BenchRun.to_dict()` and validated against `run.schema.json`.

Design choices:

- Dataclasses, not pydantic — keep dependency surface minimal (jsonschema only).
- Enums for every categorical field so schema drift is caught at construction.
- Categories that don't apply to a role are `None`, not missing keys. This
  matches `run.schema.json` which requires all seven keys to be present.
- `datetime` fields are stored as tz-aware `datetime`; serialized as ISO-8601
  UTC strings.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = "1.0.0"
_SCHEMA_PATH = Path(__file__).with_name("run.schema.json")


# --- Enums --------------------------------------------------------------------


class Tier(str, Enum):
    FAST = "fast"
    MEDIUM = "medium"
    FULL = "full"


class Role(str, Enum):
    CODER = "coder"
    PLANNER = "planner"
    EMBEDDER = "embedder"


class Runtime(str, Enum):
    LLAMA_CPP = "llama.cpp"
    VLLM = "vllm"


class Device(str, Enum):
    CPU = "cpu"
    GPU = "gpu"


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class VerdictSource(str, Enum):
    TIMEOUT = "timeout"
    VERIFY = "verify"
    TRAJECTORY = "trajectory"
    TRANSPORT = "transport"


class Format(str, Enum):
    GGUF = "gguf"
    SAFETENSORS = "safetensors"
    AWQ = "awq"
    GPTQ = "gptq"
    AUTOROUND = "autoround"
    OTHER = "other"


# --- Sub-dataclasses ----------------------------------------------------------


@dataclass
class Candidate:
    model: str
    quant: str
    format: Format
    runtime: Runtime
    device: Device


@dataclass
class TaskSet:
    identity: str
    version: str
    task_count: int


@dataclass
class Rubric:
    identity: str
    version: str
    locked_at_utc: datetime


@dataclass
class RunMetadata:
    tier: Tier
    role: Role
    candidate: Candidate
    task_set: TaskSet
    started_at_utc: datetime
    ended_at_utc: datetime
    duration_seconds: float
    harness_commit_sha: str
    llama_cpp_build_tag: Optional[str]
    vllm_release_tag: Optional[str]
    harness_version: Optional[str] = None
    openhands_sdk_version: Optional[str] = None
    docker_image: Optional[str] = None
    rubric: Optional[Rubric] = None
    notes: Optional[str] = None


@dataclass
class ToolCallBehavior:
    attempts: int
    successes: int
    malformed: int
    missing_tool_call: int
    wrong_tool_selected: int
    argument_errors: int
    loop_repetitions: int
    retries: int


@dataclass
class TaskOutcome:
    verdict: Verdict
    verdict_source: VerdictSource
    context_budget_skip: bool
    truncated: bool
    rubric_score: Optional[float] = None


@dataclass
class GpuEnvelope:
    vram_peak_mib: float
    vram_avg_mib: float
    vram_usable_mib: float
    temp_peak_c: float
    temp_avg_c: float
    power_peak_w: float
    power_avg_w: float
    util_avg_pct: float
    nvml_coverage_pct: float
    throttle_events: int
    cuda_oom_events: int
    throttle_ceiling_c: Optional[float] = None


@dataclass
class CpuEnvelope:
    proc_cpu_pct_avg: float
    system_ram_peak_mib: float
    avx512_confirmed: bool


@dataclass
class Latency:
    per_call_warm_ms_p50: float
    per_call_warm_ms_p95: float
    cold_start_ms: float
    per_task_wall_seconds_p50: float
    repeats: int
    per_call_warm_ms_max: Optional[float] = None
    per_task_wall_seconds_p95: Optional[float] = None
    variance_note: Optional[str] = None


@dataclass
class CrossCandidateContention:
    latency_delta_with_embedder_ms: float
    error_rate_delta_with_embedder: float
    swap_cost_ms: float


# --- Top-level record ---------------------------------------------------------


@dataclass
class BenchRun:
    """One record per benchmark cell. Every category key MUST be present in
    serialized output — populate with None when the category is not applicable
    to the role/tier per §0.0c.
    """
    run_metadata: RunMetadata
    tool_call_behavior: Optional[ToolCallBehavior]
    task_outcome: Optional[TaskOutcome]
    gpu_envelope: Optional[GpuEnvelope]
    cpu_envelope: Optional[CpuEnvelope]
    latency: Latency
    cross_candidate_contention: Optional[CrossCandidateContention]
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _to_json_safe(asdict(self))

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

    def write(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json() + "\n", encoding="utf-8")
        return p


# --- (De)serialization helpers ------------------------------------------------


def _to_json_safe(obj: Any) -> Any:
    """Convert dataclass-asdict output to JSON-serializable primitives.

    - Enum -> its .value
    - datetime -> ISO-8601 with 'Z' if UTC
    - dict -> recurse (None values preserved so schema sees explicit null)
    - list/tuple -> recurse

    Nulls are preserved intentionally: the schema requires all seven top-level
    category keys to be present. Optional nested fields (rubric, notes,
    variance_note, throttle_ceiling_c, per_call_warm_ms_max, per_task_wall_seconds_p95)
    are declared nullable in the schema.
    """
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            raise ValueError("datetime must be tz-aware")
        return obj.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    return obj


def load_schema() -> dict[str, Any]:
    """Load the JSON schema from disk."""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_dict(record: dict[str, Any]) -> None:
    """Validate a record dict against run.schema.json.

    Raises `jsonschema.ValidationError` on failure. Deferred import so bench
    code that only constructs records without validating doesn't need
    jsonschema installed.
    """
    from jsonschema import Draft202012Validator

    Draft202012Validator(load_schema()).validate(record)
