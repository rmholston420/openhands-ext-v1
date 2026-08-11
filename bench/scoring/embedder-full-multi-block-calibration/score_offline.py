#!/usr/bin/env python3
"""Offline scorer for Phase 0.4 gate-4 step 6d (calibration).

Reads step-6b per-cell top-20 files at ~/.forge-oh/bench_embedder_full_multi_block/
plus locked qrels.jsonl. Computes nDCG@10, Recall@10, MRR@10, Recall@1, composite
per (cell, chunker, block). No embedder / no LLM required — pure Python metric
computation over cached retrieval output.

Rationale: the runner's `score` subcommand re-runs embeddings against a live
endpoint, which is unnecessary because step-6b already wrote per-query top-20
ranked lists to disk. This scorer reuses them.

Composite = 100 * (0.40*nDCG@10 + 0.25*R@10 + 0.20*MRR@10 + 0.15*R@1)
per rubric bench/rubrics/full-embedder-scored.json.

Usage:
    python3 bench/scoring/embedder-full-multi-block-calibration/score_offline.py

Outputs:
    - stdout: per-sub-cell table + per-cell macro table
    - ~/.forge-oh/bench_embedder_full_multi_block/scored_4query_calibration.json
"""
import json
import math
from pathlib import Path
from collections import defaultdict

POOL_DIR = Path.home() / ".forge-oh/bench_embedder_full_multi_block"
QRELS = Path.home() / "dev/openhands-ext-v1/bench/gold/embedder-full-multi-block/qrels.jsonl"
OUT = POOL_DIR / "scored_4query_calibration.json"


def ndcg_at_k(retrieved_grades, ideal_grades, k=10):
    def dcg(g):
        return sum((2 ** gr - 1) / math.log2(i + 2) for i, gr in enumerate(g[:k]))
    d = dcg(retrieved_grades)
    idcg = dcg(sorted(ideal_grades, reverse=True))
    return d / idcg if idcg > 0 else 0.0


def recall_at_k(ranked_ids, rel_set, k):
    if not rel_set:
        return 0.0
    hit = sum(1 for c in ranked_ids[:k] if c in rel_set)
    return hit / len(rel_set)


def mrr(ranked_ids, rel_set):
    for i, c in enumerate(ranked_ids):
        if c in rel_set:
            return 1.0 / (i + 1)
    return 0.0


def parse_pool_filename(stem: str):
    """pool_<cell>_<chunker>_<block> -> (cell, chunker, block) or None."""
    stem = stem.replace("pool_", "", 1)
    for block in ("code", "docs"):
        suffix = "_" + block
        if stem.endswith(suffix):
            rest = stem[: -len(suffix)]
            for chunker in ("H1_fixed_512_64", "H2_structure_aware"):
                marker = "_" + chunker
                if rest.endswith(marker):
                    cell = rest[: -len(marker)]
                    return cell, chunker, block
    return None


def main():
    qrels = defaultdict(dict)
    with open(QRELS) as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("$type") == "qrels_header":
                continue
            qrels[r["qid"]][r["chunk_id"]] = int(r["grade"])
    target_qids = set(qrels.keys())

    results = []
    for f in sorted(POOL_DIR.glob("pool_*.jsonl")):
        parsed = parse_pool_filename(f.stem)
        if parsed is None:
            continue
        cell, chunker, block = parsed

        per_query = []
        with open(f) as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("$type") != "pool_row":
                    continue
                qid = r["qid"]
                if qid not in target_qids:
                    continue
                ranked = [e["chunk_id"] for e in r["top_k"]]
                rel_map = qrels[qid]
                rel_binary = {c for c, g in rel_map.items() if g >= 1}
                retrieved_grades = [float(rel_map.get(c, 0)) for c in ranked[:10]]
                ideal_grades = sorted((float(g) for g in rel_map.values()), reverse=True)
                per_query.append({
                    "qid": qid,
                    "ndcg@10": ndcg_at_k(retrieved_grades, ideal_grades, 10),
                    "recall@10": recall_at_k(ranked, rel_binary, 10),
                    "mrr@10": mrr(ranked[:10], rel_binary),
                    "recall@1": recall_at_k(ranked, rel_binary, 1),
                })

        if not per_query:
            continue

        def mean(k):
            return sum(p[k] for p in per_query) / len(per_query)

        ndcg = mean("ndcg@10")
        r10 = mean("recall@10")
        mrr_v = mean("mrr@10")
        r1 = mean("recall@1")
        comp = 100 * (0.40 * ndcg + 0.25 * r10 + 0.20 * mrr_v + 0.15 * r1)
        results.append({
            "cell": cell, "chunker": chunker, "block": block,
            "n_queries": len(per_query),
            "ndcg@10": ndcg, "recall@10": r10, "mrr@10": mrr_v, "recall@1": r1,
            "composite": comp,
            "per_query": per_query,
        })

    print(f"{'cell':18s} {'chunker':22s} {'block':6s} {'N':3s}  nDCG@10  R@10    MRR@10  R@1     composite")
    for r in sorted(results, key=lambda x: (x["cell"], x["chunker"], x["block"])):
        print(f"{r['cell']:18s} {r['chunker']:22s} {r['block']:6s} {r['n_queries']:3d}  "
              f"{r['ndcg@10']:.4f}  {r['recall@10']:.4f}  {r['mrr@10']:.4f}  "
              f"{r['recall@1']:.4f}  {r['composite']:6.2f}")

    print()
    print(f"{'cell (macro across H1+H2 x code+docs)':40s}  nDCG@10  R@10    MRR@10  R@1     composite")
    by_cell = defaultdict(list)
    for r in results:
        by_cell[r["cell"]].append(r)
    macro_rows = []
    for cell in sorted(by_cell.keys()):
        subs = by_cell[cell]

        def m(k):
            return sum(s[k] for s in subs) / len(subs)

        ndcg = m("ndcg@10")
        r10 = m("recall@10")
        mrr_v = m("mrr@10")
        r1 = m("recall@1")
        comp = 100 * (0.40 * ndcg + 0.25 * r10 + 0.20 * mrr_v + 0.15 * r1)
        macro_rows.append({
            "cell": cell,
            "ndcg@10": ndcg, "recall@10": r10, "mrr@10": mrr_v, "recall@1": r1,
            "composite": comp,
        })
        print(f"{cell:40s}  {ndcg:.4f}  {r10:.4f}  {mrr_v:.4f}  {r1:.4f}  {comp:6.2f}")

    OUT.write_text(json.dumps({
        "qids": sorted(target_qids),
        "sub_cells": results,
        "macro_per_cell": macro_rows,
    }, indent=2))
    print(f"\nfull results saved to: {OUT}")


if __name__ == "__main__":
    main()
