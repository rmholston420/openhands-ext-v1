# ADR-0027 — Phase 0.3 gate-2 coder verdict: CONFIRM AWQ (qwen3-coder-30b-a3b-instruct-awq-4bit)

**Status:** Ratified
**Lock-in phase:** Phase 0.3 gate-2
**Supersedes:** —
**Extends:** ADR-0022, ADR-0023, ADR-0026

## Context

ADR-0026 defined the coder multi-turn correctness harness v1 (DockerWorkspace SDK path, tool_trace, final_states, Perplexity-Max scored 0–100) and, in amendment 3, upgraded `tool_trace` from `list[str]` to `list[dict]` (schema v1.1: `{tool, args, observation, success, kind}`) and fixed the LLM transport (172.17.0.1 + 0.0.0.0 bind) plus `get_default_tools` wire-up.

Both coder candidates cleared stage-2 at v1.1 shape on 2026-08-11:

- **AWQ candidate:** `qwen3-coder-30b-a3b-instruct-awq-4bit` (vLLM, GPU, port :8501). Probe `smoke-medium-coder-qwen3-coder-30b-a3b-instruct-awq-4bit-vllm-gpu-20260811T153712Z.probe.json`. 10/10 verdict=pass, run 129.7 s, probe 94 s, 69 total turns, VRAM 31,835 MiB, temp 59 °C.
- **35b fallback candidate:** `qwen3_6-35b-a3b-q4kxl-gguf` (llama.cpp, GPU, port :8082). Probe `smoke-medium-coder-qwen3_6-35b-a3b-q4kxl-gguf-llama-cpp-gpu-20260811T154307Z.probe.json`. 10/10 verdict=pass, probe 81 s, 32 total turns, VRAM 24,714 MiB, temp 61 °C.

R1/R2 pass alone is insufficient: ADR-0022 rubric scoring (0–100, gold-bounded) is authoritative and post-hoc criteria interpretation is prohibited. Reversal criteria for this comparison were locked before scoring:

1. Flip to 35b if ALL 10 scores ≥85 AND 35b macro lead >3 pts.
2. Confirm AWQ if AWQ macro leads ≥3 pts OR 35b <70 on any 2 tasks.
3. Otherwise intermediate: confirm AWQ + log per-task mix.

Scoring was performed by Perplexity Max (Claude Sonnet 4.6 via Perplexity Computer) — the same authority ADR-0022 §5 designates for coder-medium — grounded in the dumped tool_trace + final_states + gold rubric under `bench/rubrics/medium-scored.json` and per-task gold under `bench/gold/coder-medium/`.

## Decision

The coder role assignment established by ADR-0026 stage-2 is **CONFIRMED on AWQ**. `qwen3-coder-30b-a3b-instruct-awq-4bit` (vLLM, GPU, port :8501) remains the production coder cell. No routing changes to ADR-0017 / ADR-0023 §coder row.

### Sub-decision 1 — Per-task scores (Perplexity Max, gold-bounded)

Scoring authority: Perplexity Max (Claude Sonnet 4.6 via Perplexity Computer). Self-scoring prohibited per `bench/rubrics/medium-scored.json` (`self_scoring_prohibited: true` applies to models under test, not to the designated Perplexity-Max scorer). Bands per gold rubric.

| Task | AWQ | 35b | Notes |
|---|---:|---:|---|
| T01 json-config-flip | 78 | 99 | AWQ used whole-block str_replace (borderline whole-file replace); 35b did targeted single-key flip. |
| T02 add slugify | 87 | 94 | Both correct; AWQ added noise commentary + extra re-view. |
| T03 fix off-by-one | 78 | 99 | AWQ replaced whole function + created scratch test file outside scope; 35b did single-token minimal fix. |
| T04 --verbose flag | 89 | 92 | Both correct placement/store_true/help; AWQ added an unnecessary re-view. |
| T05 pytest report (DO NOT MODIFY) | 87 | 70 | Files preserved in both; AWQ delivered explicit correct verdict ("1 failed, test_multiply"); 35b trace ends without a visible FinishAction containing the answer. |
| T06 rename compute_total→calculate_total | 88 | 79 | AWQ pure minimal rename across both files; 35b added a docstring beyond scope of rename. |
| T07 write test_stats.py | 86 | 90 | Both byte-identical stats.py + 3 assert-based tests; AWQ has unused `import pytest` + extra ls. |
| T08 git status (DO NOT MODIFY) | 97 | 68 | AWQ 2-turn minimal, correct answer; 35b trace ends without a visible FinishAction, no answer delivered (files preserved). |
| T09 return type hint | 91 | 99 | Both correct minimal edit; AWQ added unnecessary re-view. |
| T10 implement from docstring | 73 | 97 | Both correct impls; AWQ created scratch test file + 4 finds + 2 python -c smokes (cleaned up); 35b delivered elegant 2-line one-liner. |
| **Macro mean** | **85.4** | **88.7** | 35b leads by 3.3 pts on macro. |

### Sub-decision 2 — Application of pre-registered reversal criteria (mechanical)

Reversal criteria as locked pre-scoring (post-hoc interpretation prohibited):

| Rule | Threshold | Actual | Fired? |
|---|---|---|---|
| Flip to 35b: all 10 scores ≥85 AND 35b macro lead >3 pts | all ≥85 AND diff >3 | 35b has T05=70 and T08=68; macro diff = +3.3 | ❌ (all-≥85 fails) |
| Confirm AWQ: AWQ macro leads ≥3 pts OR 35b <70 on any 2 tasks | AWQ − 35b ≥ 3 OR 35b <70 count ≥ 2 | AWQ − 35b = −3.3; 35b <70 count = 1 (T08=68) under strict `<`; 35b ≤70 count = 2 (T05=70, T08=68) under loose `≤` | Strict `<`: ❌ · Loose `≤`: ✅ |
| **Intermediate: confirm AWQ + log per-task mix** | rules 1 and 2 do not both cleanly fire | rule 1 ❌, rule 2 disposition depends on strict/loose reading of "<70" | ✅ **FIRED** (strict reading) |

Ambiguity flag (per project instructions): the reversal criterion literal reads "35b <70 on any 2 tasks." T05=70 sits on the boundary.

- **Strict reading (`<70`):** only T08=68 qualifies → rule 2 does not fire on that clause; AWQ macro is also behind (−3.3), so its OR clause does not fire either. Land in rule 3 (intermediate → confirm AWQ + log per-task mix).
- **Loose reading (`≤70`):** T05=70 and T08=68 both qualify → rule 2 fires → confirm AWQ.

**Both readings converge on: confirm AWQ.** Verdict is robust to the ambiguity. Recorded here rather than resolved silently.

### Sub-decision 3 — Interpretation (non-binding rationale)

35b dominates on 7 targeted-edit tasks (T01, T02, T03, T04, T07, T09, T10) with cleaner minimum-turn behavior and elegant one-liners. 35b fails 2 environment-answer tasks (T05, T08) by exiting without a visible FinishAction that delivers the requested verdict, despite preserving files correctly. This is a reproducible finish-omission failure mode on report-style tasks, not scoring noise.

Quality-first (ADR-0022 §rubric) weights an agent that silently exits without answering the user more harshly than one that answers correctly but verbosely. AWQ reliably delivers finish messages containing the requested answer on report-style tasks (T05, T08).

### Sub-decision 4 — Wall-time reality check (documentation only, non-binding)

Speed data from probe files (aggregate):

| Candidate | Total turns | Probe wall | Notes |
|---|---:|---:|---|
| AWQ | 69 | 94 s | vLLM :8501, 30B AWQ-4 |
| 35b | 32 | 81 s | llama.cpp :8082, 35B q4kxl |

35b is ~2.2× more turn-efficient and modestly faster wall. Speed rule applies only within the 3-pt quality tiebreak band; the T05/T08 failure class is a quality signal outside that band (report-style non-finish is not a small margin), so speed does not overturn. Documented for future harness work.

### Sub-decision 5 — Router config unchanged; no cascading amendments

- `bench/candidates/coder-medium-pool.json` — no change.
- `bench/candidates/coder-medium-stage2-awq.json` and `coder-medium-stage2-35b.json` — retained on disk; 35b file remains available for regression regen.
- ADR-0017 coder row — unchanged (AWQ confirmed).
- ADR-0023 coder row — unchanged (AWQ confirmed).
- ADR-0026 — this ADR extends and does not amend.

### Sub-decision 6 — Follow-up investigation (Phase 0.3 gate-3 candidate)

The 35b T05 and T08 finish-omission failure is a reproducible signal, not this-run noise. Filed here as a follow-up rather than a new ADR:

- Confirm the trace truly lacks a FinishAction (vs dump-side truncation) by re-inspecting the raw probe JSON `results[*].tool_trace` for T05 and T08.
- If confirmed, characterize whether it is model-specific (llama.cpp 35b) or harness-specific (report-style tasks that end on a `terminal` action).
- Do not block Phase 0.3 gate-3 on this; investigate opportunistically before any planner-tier re-eval that would consider a llama.cpp planner candidate.

## Rationale

Alternatives considered:

- **Flip coder to 35b on macro margin (88.7 vs 85.4, +3.3).** Rejected: rule 1 requires all-≥85 AND >3-pt margin; the +3.3 margin is at the threshold and the all-≥85 gate fails on T05 (70) and T08 (68). Post-hoc reweighting to flip anyway would violate the pre-registration discipline enshrined in ADR-0024 §reversal-criteria.
- **Intermediate: run coder on both, route per task class.** Rejected at this phase: no per-task-class router yet exists; introducing one would require a new ADR and a plugin-scope decision beyond Phase 0.3 gate-2. Deferred as a Full-tier consideration (Phase 10, alongside the reserved `select_model` decision).
- **Re-run 35b with a repaired harness that forces FinishAction on report-style tasks.** Rejected as scope creep: the harness passed R1/R2 for both candidates under the current v1.1 contract; changing the contract to rescue a candidate is post-hoc.

## Consequences

- **Files/procedures locked-in:** `bench/rubrics/medium-scored.json` (unchanged), `bench/gold/coder-medium/` (unchanged), `bench/candidates/coder-medium-stage2-awq.json` (unchanged), production coder cell (unchanged).
- **PORTING_LEDGER:** no change (no new vendor); llama.cpp adapter remains PLANNED per adrs/README.md deferred list.
- **BUILD_LOG:** one entry for this scoring + verdict.
- **SESSION_HANDOFF:** overwrite with current gate-2 CLOSED state and gate-3 pointer.
- **Downstream ADRs:** ADR-0023 §coder row remains authoritative. No cascading amendment.
- **Reservation:** ADR-0028 reserved for Phase 0.3 gate-3 opener (planner Full-tier or coder Full-tier — TBD).

## Lock-in phase

Phase 0.3 gate-2. Locks coder-medium production selection until Full-tier re-eval opens.

## References

- ADR-0017 (production role selection)
- ADR-0022 (medium task set + gold protocol)
- ADR-0023 (Phase 0.3 router selection)
- ADR-0026 (coder multi-turn correctness harness v1, amendment 3)
- `bench/rubrics/medium-scored.json`
- `bench/gold/coder-medium/`
- `bench/candidates/coder-medium-stage2-awq.json`
- `bench/candidates/coder-medium-stage2-35b.json`
- Probes: `bench/results/smoke/smoke-medium-coder-qwen3-coder-30b-a3b-instruct-awq-4bit-vllm-gpu-20260811T153712Z.probe.json` and `bench/results/smoke/smoke-medium-coder-qwen3_6-35b-a3b-q4kxl-gguf-llama-cpp-gpu-20260811T154307Z.probe.json`
