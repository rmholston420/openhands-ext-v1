"""bench.schema — Phase 0 benchmark record dataclasses + JSON schema.

Source of truth: docs/specs/integration-execution-plan-v16.md §0.0c.
JSON schema at bench/schema/run.schema.json is authoritative on-disk shape.
"""
from .run import (
    BenchRun,
    RunMetadata,
    Candidate,
    TaskSet,
    Rubric,
    ToolCallBehavior,
    TaskOutcome,
    GpuEnvelope,
    CpuEnvelope,
    Latency,
    CrossCandidateContention,
    Tier,
    Role,
    Runtime,
    Device,
    Verdict,
    VerdictSource,
    Format,
    SCHEMA_VERSION,
    load_schema,
    validate_dict,
)

__all__ = [
    "BenchRun",
    "RunMetadata",
    "Candidate",
    "TaskSet",
    "Rubric",
    "ToolCallBehavior",
    "TaskOutcome",
    "GpuEnvelope",
    "CpuEnvelope",
    "Latency",
    "CrossCandidateContention",
    "Tier",
    "Role",
    "Runtime",
    "Device",
    "Verdict",
    "VerdictSource",
    "Format",
    "SCHEMA_VERSION",
    "load_schema",
    "validate_dict",
]
