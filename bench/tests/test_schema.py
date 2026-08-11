"""Smoke tests for bench/schema — verifies round-trip and guards.

Run: python -m pytest bench/tests/test_schema.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from bench.schema import (
    BenchRun,
    Candidate,
    CpuEnvelope,
    CrossCandidateContention,
    Device,
    Format,
    GpuEnvelope,
    Latency,
    Role,
    Rubric,
    Runtime,
    RunMetadata,
    SCHEMA_VERSION,
    TaskOutcome,
    TaskSet,
    Tier,
    ToolCallBehavior,
    Verdict,
    VerdictSource,
    load_schema,
    validate_dict,
)


def _base_run(
    role: Role = Role.CODER,
    tier: Tier = Tier.FAST,
    with_contention: bool = False,
) -> BenchRun:
    started = datetime(2026, 8, 11, 4, 30, tzinfo=timezone.utc)
    ended = datetime(2026, 8, 11, 4, 45, tzinfo=timezone.utc)
    tcb: ToolCallBehavior | None
    outcome: TaskOutcome | None
    if role == Role.EMBEDDER:
        tcb = None
        outcome = None
    else:
        tcb = ToolCallBehavior(
            attempts=10,
            successes=8,
            malformed=1,
            missing_tool_call=0,
            wrong_tool_selected=1,
            argument_errors=0,
            loop_repetitions=0,
            retries=1,
        )
        outcome = TaskOutcome(
            verdict=Verdict.PASS,
            verdict_source=VerdictSource.VERIFY,
            context_budget_skip=False,
            truncated=False,
            rubric_score=None,
        )
    return BenchRun(
        run_metadata=RunMetadata(
            tier=tier,
            role=role,
            candidate=Candidate(
                model="Qwen3.6-27B",
                quant="Q6_K",
                format=Format.GGUF,
                runtime=Runtime.LLAMA_CPP,
                device=Device.GPU,
            ),
            task_set=TaskSet(identity=f"{role.value}-{tier.value}", version="0.1.0", task_count=5),
            started_at_utc=started,
            ended_at_utc=ended,
            duration_seconds=900.0,
            harness_commit_sha="deadbee",
            llama_cpp_build_tag="b10356",
            vllm_release_tag=None,
        ),
        tool_call_behavior=tcb,
        task_outcome=outcome,
        gpu_envelope=GpuEnvelope(
            vram_peak_mib=18000.0,
            vram_avg_mib=17500.0,
            vram_usable_mib=32607.0,
            temp_peak_c=72.0,
            temp_avg_c=68.0,
            power_peak_w=380.0,
            power_avg_w=320.0,
            util_avg_pct=85.0,
            nvml_coverage_pct=99.5,
            throttle_events=0,
            cuda_oom_events=0,
        ),
        cpu_envelope=None,
        latency=Latency(
            per_call_warm_ms_p50=420.0,
            per_call_warm_ms_p95=780.0,
            cold_start_ms=6200.0,
            per_task_wall_seconds_p50=45.0,
            repeats=3,
        ),
        cross_candidate_contention=(
            CrossCandidateContention(
                latency_delta_with_embedder_ms=15.0,
                error_rate_delta_with_embedder=0.01,
                swap_cost_ms=2500.0,
            ) if with_contention else None
        ),
    )


def test_schema_loads():
    schema = load_schema()
    assert schema["title"].startswith("OpenHands-Ext v1")


def test_valid_coder_run_validates():
    validate_dict(_base_run().to_dict())


def test_valid_embedder_run_validates():
    validate_dict(_base_run(role=Role.EMBEDDER).to_dict())


def test_schema_version_matches_constant():
    assert _base_run().to_dict()["schema_version"] == SCHEMA_VERSION


def test_full_tier_may_include_contention():
    validate_dict(_base_run(tier=Tier.FULL, with_contention=True).to_dict())


def test_datetime_serialized_as_utc_z():
    d = _base_run().to_dict()
    assert d["run_metadata"]["started_at_utc"].endswith("Z")


def test_missing_required_key_fails():
    from jsonschema import ValidationError
    d = _base_run().to_dict()
    del d["latency"]
    with pytest.raises(ValidationError):
        validate_dict(d)
