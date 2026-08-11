# Phase 0.4 gate-4 · step 6d · 4-query calibration scoring results

**Date:** 2026-08-11 16:36 EDT
**Scorer:** `bench/scoring/embedder-full-multi-block-calibration/score_offline.py`
**Qrels:** `bench/gold/embedder-full-multi-block/qrels.jsonl` (SHA256 `f7137c7bebbf9b10da14091488c185921f4cda2e071880c838eefff4aaca48f8`)
**Queries labeled (N=4):** q-c01, q-c40 (code) + q-d18, q-d29 (docs)
**Corpus SHAs:** openhands-ext-v1 `a9d5bd6`, Kosmos `1f33519a`, Rigpa-LMS `55b55539`

## Composite formula

`100 * (0.40*nDCG@10 + 0.25*Recall@10 + 0.20*MRR@10 + 0.15*Recall@1)` per `bench/rubrics/full-embedder-scored.json`.

## Per-sub-cell (16 rows, 2 queries each — code or docs half of the 4-query set)

| cell | chunker | block | N | nDCG@10 | R@10 | MRR@10 | R@1 | composite |
|---|---|---|---|---|---|---|---|---|
| e006b_q8_cpu | H1_fixed_512_64 | code | 2 | 0.1177 | 0.0909 | 0.7500 | 0.0227 | 22.32 |
| e006b_q8_cpu | H1_fixed_512_64 | docs | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.00 |
| e006b_q8_cpu | H2_structure_aware | code | 2 | 0.2830 | 0.0682 | 1.0000 | 0.0455 | 33.71 |
| e006b_q8_cpu | H2_structure_aware | docs | 2 | 0.1012 | 0.0427 | 0.2250 | 0.0000 | 9.62 |
| e04b_q8_cpu | H1_fixed_512_64 | code | 2 | 0.2051 | 0.1364 | 1.0000 | 0.0455 | 32.30 |
| e04b_q8_cpu | H1_fixed_512_64 | docs | 2 | 0.3015 | 0.2309 | 0.7500 | 0.0200 | 33.13 |
| e04b_q8_cpu | H2_structure_aware | code | 2 | 0.3692 | 0.1136 | 1.0000 | 0.0455 | 38.29 |
| e04b_q8_cpu | H2_structure_aware | docs | 2 | 0.1391 | 0.0855 | 0.2500 | 0.0000 | 12.70 |
| e08b_q6k_cpu | H1_fixed_512_64 | code | 2 | 0.3026 | 0.2273 | 1.0000 | 0.0455 | 38.47 |
| e08b_q6k_cpu | H1_fixed_512_64 | docs | 2 | 0.2850 | 0.1709 | 0.4167 | 0.0000 | 24.01 |
| e08b_q6k_cpu | H2_structure_aware | code | 2 | 0.4684 | 0.2500 | 1.0000 | 0.0455 | 45.67 |
| e08b_q6k_cpu | H2_structure_aware | docs | 2 | 0.2296 | 0.1764 | 0.3214 | 0.0000 | 20.02 |
| enomicc_q6k_gpu | H1_fixed_512_64 | code | 2 | 0.2585 | 0.1591 | 0.6250 | 0.0227 | 27.16 |
| enomicc_q6k_gpu | H1_fixed_512_64 | docs | 2 | 0.2275 | 0.1227 | 0.5833 | 0.0200 | 24.13 |
| enomicc_q6k_gpu | H2_structure_aware | code | 2 | 0.4345 | 0.1591 | 1.0000 | 0.0455 | 42.04 |
| enomicc_q6k_gpu | H2_structure_aware | docs | 2 | 0.2126 | 0.0627 | 0.6000 | 0.0227 | 22.41 |

## Macro per cell (H1+H2 × code+docs, 4 sub-cells averaged)

| cell | role | nDCG@10 | R@10 | MRR@10 | R@1 | composite |
|---|---|---|---|---|---|---|
| e006b_q8_cpu | 0.6B Q8 (downsize candidate) | 0.1255 | 0.0505 | 0.4938 | 0.0170 | **16.41** |
| e04b_q8_cpu | 4B Q8 (incumbent) | 0.2537 | 0.1416 | 0.7500 | 0.0277 | **29.11** |
| e08b_q6k_cpu | 8B Q6_K (upsize candidate) | 0.3214 | 0.2061 | 0.6845 | 0.0227 | **32.04** |
| enomicc_q6k_gpu | nomic-embed-code Q6_K (informational only) | 0.2833 | 0.1259 | 0.7021 | 0.0277 | **28.94** |

## Notes (facts only — NO reversal-criteria interpretation)

- **N=2 queries per sub-cell, N=4 per cell macro.** This is calibration signal (~20% of a rubric-defensible sample), not a defensible V3/W3 verdict. ADR-0030 requires 20 queries/block for stable macro metrics.
- 0.6B has an all-zero sub-cell (H1 docs): retrieved zero relevant chunks at k=10 across {q-d18, q-d29}.
- 8B is highest across every macro metric except MRR@10 (where 4B leads).
- nomic-embed-code sits between 4B and 8B on composite — cross-family sanity check reported informationally only, out of Qwen reversal scope.
- Recall@1 is near-zero across all cells: at this pool depth × chunker split, the g3 primary rarely appears in the top-1 position.
- All 4 candidates are within a narrow band on top-1 correctness (Recall@1 max 0.028); the composite spread is driven by nDCG@10 and R@10.

## Reproducibility

```
python3 bench/scoring/embedder-full-multi-block-calibration/score_offline.py
```

Reads `~/.forge-oh/bench_embedder_full_multi_block/pool_*.jsonl` (16 files from step 6b, one per cell × chunker × block) + `bench/gold/embedder-full-multi-block/qrels.jsonl`. Emits stdout table + JSON at `~/.forge-oh/bench_embedder_full_multi_block/scored_4query_calibration.json`.
