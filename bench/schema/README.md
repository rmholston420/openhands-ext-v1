# bench/schema — Phase 0 benchmark record schema

Source of truth: `docs/specs/integration-execution-plan-v16.md` §0.0c.

## Files

| File | Purpose |
|---|---|
| `run.schema.json` | JSON Schema (Draft 2020-12). On-disk shape is authoritative. |
| `run.py` | Python dataclasses that serialize to that shape. |
| `__init__.py` | Re-exports. |

## The 7 categories (v16 §0.0c)

Every `BenchRun` has all seven keys. Categories that don't apply to a
role/tier are serialized as `null` — never omitted.

| # | Category | Roles | Notes |
|---|---|---|---|
| 1 | `tool_call_behavior` | coder, planner | Captured from SDK `ActionEvent`/`ObservationEvent` stream, not re-parsed text. `null` for embedder. |
| 2 | `task_outcome` | coder, planner | Verdict via deterministic ordered reduction: `timeout > verify > trajectory > transport`. `null` for embedder. |
| 3 | `gpu_envelope` | all GPU-resident cells | Reuse existing NVML sampler. `null` for CPU cells. |
| 4 | `cpu_envelope` | CPU-resident embedder cells | Isolated process CPU%, not systemwide. `null` for GPU cells. |
| 5 | `latency` | all roles, all tiers | **Every value measured, never estimated** (§0.0a). |
| 6 | `cross_candidate_contention` | all roles | Populated **only** at Phase 0.3 (Full tier). `null` for Fast/Medium. |
| 7 | `run_metadata` | every run | Must include `llama_cpp_build_tag` and `vllm_release_tag`. |

## Denominator-exclusion guard (§0.0a)

`tool_call_behavior.malformed` **must remain in rate-metric denominators**.
Consumers of these records that compute success rates must divide by
`attempts`, not by `attempts - malformed`.

## Latency measurement guard (§0.0a)

Every latency field is measured. A prior "24.2s/call" estimate was later
measured at 0.32–1.30s/call — a 40× error. If a value cannot be measured,
use `null` and record why in `variance_note`, never a guess.

## Rubric lock (§0.0a)

`RunMetadata.rubric.locked_at_utc` must precede `RunMetadata.started_at_utc`
for the first scored run in a rubric's lifetime. The harness will refuse to
run a scored cell whose rubric was modified after the first scored output.

## Usage

```python
from datetime import datetime, timezone
from bench.schema import (
    BenchRun, RunMetadata, Candidate, TaskSet, Latency,
    Tier, Role, Runtime, Device, Format,
)

run = BenchRun(
    run_metadata=RunMetadata(
        tier=Tier.FAST,
        role=Role.CODER,
        candidate=Candidate(
            model="Qwen3.6-27B",
            quant="Q6_K",
            format=Format.GGUF,
            runtime=Runtime.LLAMA_CPP,
            device=Device.GPU,
        ),
        task_set=TaskSet(identity="coder-fast", version="0.1.0", task_count=5),
        started_at_utc=datetime(2026, 8, 11, 4, 30, tzinfo=timezone.utc),
        ended_at_utc=datetime(2026, 8, 11, 4, 45, tzinfo=timezone.utc),
        duration_seconds=900.0,
        harness_commit_sha="deadbee",
        llama_cpp_build_tag="b10356",
        vllm_release_tag=None,
    ),
    tool_call_behavior=None,  # populate for coder/planner
    task_outcome=None,
    gpu_envelope=None,
    cpu_envelope=None,
    latency=Latency(
        per_call_warm_ms_p50=420.0,
        per_call_warm_ms_p95=780.0,
        cold_start_ms=6200.0,
        per_task_wall_seconds_p50=45.0,
        repeats=1,
    ),
    cross_candidate_contention=None,  # null except at Phase 0.3
)

run.write("bench/results/phase-0-fast-coder-qwen27b-gguf-q6_k-llamacpp-gpu-20260811T043000Z.json")
```
