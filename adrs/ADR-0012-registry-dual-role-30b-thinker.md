# ADR-0012 — Registry amendment: `qwen3-30b-a3b-thinking-2507-awq` is dual-role (coder + planner)

**Status:** Ratified
**Lock-in phase:** Phase 0.1 · Fast tier
**Supersedes:** —

## Context

The candidate registry `bench/candidates/registry.json` (§0.0b Phase 0 pool
manifest) originally listed `qwen3-30b-a3b-thinking-2507-awq` under the
`planner` role only, with `role_pool: ["planner"]`. The note stated that "the
235B thinking variant does NOT fit 32 GiB VRAM" and framed the 30B thinker as
the planner cell that survived VRAM elimination at model-choice time.

Empirical evidence 2026-08-11 03:18 EDT: the same 30B-A3B thinker was smoked as
the coder role under `bench/tasks/coder-fast.json` + `bench/rubrics/fast-elimination.json`
and passed 5/5 tasks with populated `tool_calls`, `finish_reason=stop`, wall
1.08–6.22 s per task, VRAM peak 30753 MiB, temp peak 51 °C, NVML coverage 100 %
(see `bench/results/smoke-fast-coder-qwen3-30b-a3b-thinking-2507-awq-vllm-gpu-20260811T071736Z.probe.json`
and `BUILD_LOG.md` 2026-08-11 03:18 EDT).

That result was obtained via a `/tmp/single-coder.json` isolation candidate
file, not via the registry. To gate the full coder pool in a single smoke run
that draws its candidates from the registry (as §0.0b requires), the registry
must reflect the model's real dual-role status.

## Decision

Amend `bench/candidates/registry.json`:

- Set `roles.coder[<new_entry>].slug = "qwen3-30b-a3b-thinking-2507-awq"` with
  the same `hf_repo`, `hf_files`, `format`, `runtime`, `approx_size_gib`, and
  updated `role_pool: ["coder", "planner"]`.
- Set `roles.planner[<existing_entry>].role_pool = ["coder", "planner"]` on the
  existing planner entry so it is a single canonical dual-role membership,
  not two divergent copies.
- Update the note to reflect the dual-role verification date.

The registry becomes the single source of truth for which candidates enter
the coder-fast pool. `pull-models.sh` behavior is unchanged (the model was
already pulled under the planner listing).

## Rationale

- **Alternative A (do not amend, treat 30B as diagnostic-only).** Would leave
  the 03:18 EDT smoke result outside the coder pool's audit trail, forcing a
  separate ad-hoc candidate file for every coder-pool smoke that wants to
  include the thinker. Duplicates state.
- **Alternative B (create a second entry under `roles.coder`).** Two entries
  with the same slug is a schema smell: `pull-models.sh` dedupes by slug and
  the tier runner picks the first hit. Silent divergence risk.
- **Chosen (this ADR):** amend the existing entry's `role_pool` to declare
  dual-role membership, and add a `roles.coder` entry that reuses the same
  slug for tier-runner enumeration. Registry stays consistent.

## Consequences

- **Files touched:**
  - `bench/candidates/registry.json` (add entry to `roles.coder`; update
    `role_pool` on the planner entry to `["coder","planner"]`; refresh note).
  - `adrs/README.md` (index row).
  - `BUILD_LOG.md` (append entry).
- **Runner behavior:** `benchmark-tier-runner.py --tier fast --role coder` now
  enumerates 3 vLLM coder candidates from the registry (qwen3-30b-a3b-thinking-
  2507-awq, qwen3_6-27b-int4-autoround, qwen3_6-35b-a3b-awq) plus 2 llama.cpp
  candidates (qwen3_6-27b-q6k-gguf, qwen3_6-35b-a3b-q4kxl-gguf, gated by
  on-disk presence).
- **VRAM policy for `qwen3_6-27b-bf16`:** unchanged. Registry note already
  self-declares OOM; runner must gate at load time (existing R1 elimination
  path). No amendment needed.
- **VRAM policy for `qwen3_6-35b-a3b-awq`:** weights 23.71 GiB → KV budget
  ~6 GiB. Coder-fast prompts are small (input ≤ 2k, output ≤ 4k). Reduced
  `max_model_len=16384` is safe. Runner uses candidate-level `extra_flags` to
  set this per-cell; ROLE_FLAGS itself is not amended.

## Lock-in phase

Phase 0.1 fast-tier coder-pool smoke.

## References

- `bench/candidates/registry.json`
- ADR-0007 (fast-tier methodology), ADR-0010 (vLLM ROLE_FLAGS), ADR-0011
  (coder parser=hermes).
- `BUILD_LOG.md` 2026-08-11 03:18 EDT (empirical dual-role evidence).
- `DEBUG_LOG.md` 2026-08-11 03:18 EDT.
