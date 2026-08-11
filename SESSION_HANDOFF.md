# Kosmos Session Handoff — 2026-08-11 16:30 EDT

## Current build-sequencing position
- **Project:** OpenHands-Ext v1 (this Space)
- **Stage / phase:** Phase 0.4 gate-4 (Full-tier embedder re-eval)
- **Component:** ADR-0030 fixture DoD, step 6c calibration set complete → step 6d scoring pending

## Completed this session
- q-c01 calibration slice labeled (15 g3 / 3 g2 / 4 g1 / 81 g0), committed & pushed
- q-c02 calibration slice labeled (11 g3 / 14 g2 / 11 g1 / 24 g0), retained (validates driver)
- q-c09 labeled UNANSWERABLE at pinned SHA (canonical `probes_embedder_multi_block.py` missing from all 4 candidates' pool — legitimate retrieval failure); all 115 pool rows grade 0
- q-c32 labeled UNANSWERABLE at pinned SHA (co-residency contract in .json + .sh + .md — non-.py, out of scope for code corpus); all 117 pool rows grade 0
- q-d29 labeled ANSWERABLE (2 g3 / 12 g2 / 8 g1 / 100 g0) — canonical: ADR-0030 L145 P1 primary key rule
- q-c40 labeled ANSWERABLE (6 g3 / 6 g2 / 10 g1 / 86 g0) — canonical: MemoryPort link_entities + TemporalIndex Protocol + adapter write path
- q-d18 labeled ANSWERABLE (3 g3 / 2 g2 / 20 g1 / 79 g0) — canonical: SESSION_HANDOFF.md L26-35 Exact next action
- Combined `qrels.jsonl` locked (437 rows, SHA256 `f7137c7bebbf9b10da14091488c185921f4cda2e071880c838eefff4aaca48f8`), 4-query calibration set: q-c01, q-d29, q-c40, q-d18 (2 code + 2 docs)
- `_calibration_driver.py` shared helper for line-range-overlap-≥0.5 matching against pool.jsonl

## Remaining before current Definition of Done
- **Step 6d execution (Colossus-side)**: agent CANNOT score — the score subcommand re-runs embeddings against a live embedder endpoint, so it must run on Colossus. See Exact next action below for the 16-cell sequence (12 Qwen scoring cells + 4 nomic informational cells).
- Step 7 ADR-0031 verdict decision (deferred until user has scored numbers)
- Full 40-query labeling remains open (this is a 4-query calibration set — NOT a defensible verdict per rubric)

## Open questions / awaiting user answer
- After scoring runs on Colossus, does the 4-query calibration signal suggest continuing to full 40-query labeling, or is signal too noisy to warrant it?

## Exact next action

On Colossus, from `~/dev/openhands-ext-v1/`:

```bash
cd ~/dev/openhands-ext-v1 && git pull origin main

# Verify locked qrels + sha
(cd bench/gold/embedder-full-multi-block && sha256sum -c QRELS.locked.sha256)

# Score all 16 cells (12 Qwen + 4 nomic). Uses same embedder-launch dance as step 6b —
# start each cell's embedder server, run 4 score invocations (2 chunkers × 2 blocks), teardown, next cell.
# --served-name must match how the embedder is launched (llama-server --alias=...).

OUT_DIR=~/.forge-oh/bench_embedder_full_multi_block/scored_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p $OUT_DIR

score_cell() {
  local CAND="$1" SERVED="$2" ENDPOINT="$3"
  for CHUNKER in H1_fixed_512_64 H2_structure_aware; do
    for BLOCK in code docs; do
      echo "=== $CAND / $CHUNKER / $BLOCK ==="
      python3 -m bench.runner.run_embedder_full_multi_block score \
        --candidate "$CAND" --chunker "$CHUNKER" --block "$BLOCK" \
        --endpoint "$ENDPOINT" --served-name "$SERVED" \
        --corpus-root /tmp/pool-corpus \
        --qrels bench/gold/embedder-full-multi-block/qrels.jsonl \
        --out "$OUT_DIR/scored_${CAND}_${CHUNKER}_${BLOCK}.json"
    done
  done
}

# 1) Launch 0.6B embedder → score → teardown
# 2) Launch 4B → score → teardown
# 3) Launch 8B → score → teardown
# 4) Launch nomic (GPU) → score → teardown
# (Use whichever launch scripts you used for step 6b. Replace endpoint + served-name below.)

score_cell e006b_q8_cpu    qwen3-embedding-0.6B-Q8_0 http://localhost:8085
score_cell e04b_q8_cpu     qwen3-embedding-4B-Q8_0   http://localhost:8085
score_cell e08b_q6k_cpu    qwen3-embedding-8B-Q6_K   http://localhost:8085
score_cell enomicc_q6k_gpu nomic-embed-code-Q6_K     http://localhost:8085

# Aggregate: macro composite per cell (Qwens scored, nomic informational)
python3 << 'PY'
import json, glob, os
from pathlib import Path
run = os.environ.get("OUT_DIR") or sorted(Path.home().glob(".forge-oh/bench_embedder_full_multi_block/scored_*"))[-1]
print(f"Run: {run}")
print(f"{'cell':60s}  nDCG@10  R@10    MRR@10  R@1     composite")
for f in sorted(Path(run).glob("scored_*.json")):
    d = json.loads(open(f).read())
    s = d.get("scoring", {}).get("macro", {}) or d.get("summary", {}).get("scoring", {}).get("macro", {})
    cell = f.stem.replace("scored_", "")
    ndcg = s.get("ndcg@10", 0); r10 = s.get("recall@10", 0); mrr = s.get("mrr@10", 0); r1 = s.get("recall@1", 0)
    comp = 100 * (0.40 * ndcg + 0.25 * r10 + 0.20 * mrr + 0.15 * r1)
    print(f"{cell:60s}  {ndcg:.4f}  {r10:.4f}  {mrr:.4f}  {r1:.4f}  {comp:6.2f}")
PY
```

Paste the aggregate table back into this session. Do NOT interpret reversal criteria (V3/W3) — 4 queries is calibration signal only, not defensible verdict.

## Reminders (binding)
- Rubric + gold `post_hoc_edit_locked=true` per ADR-0016 + ADR-0022
- 4-query calibration ≠ V3/W3 verdict; 20 queries/block needed for stable macro
- Nomic-embed-code reported informationally only (cross-family sanity check, out of Qwen reversal scope)
