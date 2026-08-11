"""Medium-tier embedder retrieval probe.

Separate module from `probes.py` so the Fast-tier `probe_embedder` remains
byte-for-byte untouched (Fast rubric is post-hoc-edit-locked; changing its
probe would violate §0.0a bullet 3 in spirit).

Contract:
  probe_embedder_retrieval(endpoint, served_name, task_set) -> ProbeResult

  task_set must have the Medium-tier embedder shape (ADR-0016):
    - `corpus`: list of {doc_id, text}
    - `queries`: list of {query_id, text}
    - `qrels`:   list of {query_id, doc_id, relevance}
    - `metrics.primary`: list of metric IDs to record (recall@k, mrr, ndcg@k)

  Returns a ProbeResult with one TaskResult per query (verdict=pass on
  successful retrieval; fail on transport/malformed). Per-metric scores
  are stored in ProbeResult.notes as a JSON string keyed by metric_id, and
  also embedded in each TaskResult.detail for human-readable logs.

  The runner writes the per-query TaskResult array plus the metric summary
  into the probe sidecar; the main BenchRun captures the summary in a
  free-form notes field (schema category_6 slot reserved but not yet
  wired — landing here without a schema bump keeps this ADR-0016 change
  additive and reversible).
"""
from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
from typing import Any

from .probes import HttpPostError, ProbeResult, TaskResult, _http_post


def _cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _dcg(rels: list[float]) -> float:
    """Standard log-2 discounted cumulative gain (position 1-indexed)."""
    s = 0.0
    for i, r in enumerate(rels, start=1):
        s += (2 ** r - 1) / math.log2(i + 1)
    return s


def _ndcg_at_k(retrieved_rels: list[float], ideal_rels: list[float], k: int) -> float:
    dcg = _dcg(retrieved_rels[:k])
    idcg = _dcg(sorted(ideal_rels, reverse=True)[:k])
    return dcg / idcg if idcg > 0 else 0.0


def _recall_at_k(retrieved_doc_ids: list[str], relevant_doc_ids: set[str], k: int) -> float:
    if not relevant_doc_ids:
        return 0.0
    hit = sum(1 for d in retrieved_doc_ids[:k] if d in relevant_doc_ids)
    return hit / len(relevant_doc_ids)


def _mrr(retrieved_doc_ids: list[str], relevant_doc_ids: set[str]) -> float:
    for rank, d in enumerate(retrieved_doc_ids, start=1):
        if d in relevant_doc_ids:
            return 1.0 / rank
    return 0.0


def _embed_batch(
    *,
    endpoint: str,
    served_name: str,
    texts: list[str],
    batch_size: int = 64,
    timeout: int = 300,
) -> list[list[float]]:
    """POST /v1/embeddings in batches. Preserves input order."""
    out: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        chunk = texts[start:start + batch_size]
        payload = {"model": served_name, "input": chunk}
        resp, _wall = _http_post(f"{endpoint}/v1/embeddings", payload, timeout=timeout)
        # Sort by index (OpenAI-spec response order preservation).
        rows = sorted(resp["data"], key=lambda r: r.get("index", 0))
        out.extend(row["embedding"] for row in rows)
    return out


def probe_embedder_retrieval(
    *,
    endpoint: str,
    served_name: str,
    task_set: dict,
) -> ProbeResult:
    """Medium-tier embedder retrieval probe.

    Steps:
      1. Embed corpus (batched).
      2. Embed queries (batched).
      3. For each query, compute cosine similarity to every corpus vector,
         sort descending, take the retrieved doc_id ranking.
      4. Score against qrels: recall@k, MRR, nDCG@k.
      5. Macro-average across queries.
    """
    result = ProbeResult(role="embedder")

    corpus = task_set.get("corpus")
    queries = task_set.get("queries")
    qrels = task_set.get("qrels")
    if not (isinstance(corpus, list) and isinstance(queries, list) and isinstance(qrels, list)):
        # Malformed task set — return a single-task fail so the outer
        # rubric handling can see it as a schema issue not a model issue.
        tr = TaskResult(
            task_id="embedder-medium-schema",
            verdict="fail",
            verdict_source="verify",
            wall_seconds=0.0,
            detail="task_set missing required keys: corpus/queries/qrels",
        )
        result.tasks.append(tr)
        return result

    metrics_cfg = task_set.get("metrics", {})
    ks = sorted({
        int(m.split("@")[1])
        for m in list(metrics_cfg.get("primary", [])) + list(metrics_cfg.get("secondary", []))
        if isinstance(m, str) and "@" in m
    })
    if not ks:
        ks = [1, 5, 10]

    # 1 + 2. Embed corpus and queries.
    corpus_ids = [d["doc_id"] for d in corpus]
    corpus_texts = [d["text"] for d in corpus]
    query_ids = [q["query_id"] for q in queries]
    query_texts = [q["text"] for q in queries]

    t0 = time.monotonic()
    try:
        corpus_vecs = _embed_batch(
            endpoint=endpoint, served_name=served_name, texts=corpus_texts,
        )
        query_vecs = _embed_batch(
            endpoint=endpoint, served_name=served_name, texts=query_texts,
        )
    except HttpPostError as exc:
        tr = TaskResult(
            task_id="embedder-medium-transport",
            verdict="fail",
            verdict_source="transport",
            wall_seconds=time.monotonic() - t0,
            detail=f"transport error during embed batch: {exc}",
        )
        result.tasks.append(tr)
        return result
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        tr = TaskResult(
            task_id="embedder-medium-transport",
            verdict="fail",
            verdict_source="transport",
            wall_seconds=time.monotonic() - t0,
            detail=f"transport error during embed batch: {exc!r}",
        )
        result.tasks.append(tr)
        return result

    embed_wall = time.monotonic() - t0

    # Guard: vector counts match.
    if len(corpus_vecs) != len(corpus_ids) or len(query_vecs) != len(query_ids):
        tr = TaskResult(
            task_id="embedder-medium-schema",
            verdict="fail",
            verdict_source="verify",
            wall_seconds=embed_wall,
            detail=(
                f"vector count mismatch: corpus {len(corpus_vecs)}/{len(corpus_ids)}, "
                f"queries {len(query_vecs)}/{len(query_ids)}"
            ),
        )
        result.tasks.append(tr)
        return result

    # 3. Build query -> relevant docs map (binary-collapsed for recall/MRR;
    # graded kept for nDCG).
    rel_by_query: dict[str, dict[str, int]] = {}
    for row in qrels:
        rel_by_query.setdefault(row["query_id"], {})[row["doc_id"]] = int(row["relevance"])

    # 4. Score each query.
    per_query_scores: list[dict[str, Any]] = []
    max_k = max(ks) if ks else 10

    for qi, qid in enumerate(query_ids):
        qv = query_vecs[qi]
        # Rank corpus by cosine similarity descending.
        sims = [(_cosine(qv, corpus_vecs[ci]), corpus_ids[ci]) for ci in range(len(corpus_ids))]
        sims.sort(key=lambda t: t[0], reverse=True)
        ranked_ids = [doc_id for _sim, doc_id in sims]

        rel_map = rel_by_query.get(qid, {})
        relevant_docs_binary = {d for d, r in rel_map.items() if r > 0}
        retrieved_rels_graded = [float(rel_map.get(d, 0)) for d in ranked_ids[:max_k]]
        ideal_rels_graded = sorted((float(r) for r in rel_map.values()), reverse=True)

        row: dict[str, Any] = {"query_id": qid, "top": ranked_ids[:max_k]}
        for k in ks:
            row[f"recall@{k}"] = _recall_at_k(ranked_ids, relevant_docs_binary, k)
        row["mrr"] = _mrr(ranked_ids, relevant_docs_binary)
        row[f"ndcg@{max_k}"] = _ndcg_at_k(retrieved_rels_graded, ideal_rels_graded, max_k)
        per_query_scores.append(row)

        tr = TaskResult(
            task_id=f"embedder-medium-{qid}",
            verdict="pass",
            verdict_source="verify",
            wall_seconds=0.0,  # per-query wall not separated; embed_wall is aggregate
            detail=(
                f"recall@{max_k}={row[f'recall@{max_k}']:.3f} mrr={row['mrr']:.3f} "
                f"ndcg@{max_k}={row[f'ndcg@{max_k}']:.3f}"
            ),
        )
        result.tasks.append(tr)

    # 5. Macro-averages.
    def _mean(key: str) -> float:
        vals = [r[key] for r in per_query_scores if key in r]
        return sum(vals) / len(vals) if vals else 0.0

    summary: dict[str, Any] = {
        "arm": task_set.get("arm"),
        "task_id": task_set.get("task_id"),
        "corpus_size": len(corpus_ids),
        "query_count": len(query_ids),
        "embed_wall_seconds": round(embed_wall, 3),
        "macro_average": {},
        "per_query": per_query_scores,
    }
    for k in ks:
        summary["macro_average"][f"recall@{k}"] = round(_mean(f"recall@{k}"), 4)
    summary["macro_average"]["mrr"] = round(_mean("mrr"), 4)
    summary["macro_average"][f"ndcg@{max_k}"] = round(_mean(f"ndcg@{max_k}"), 4)

    result.notes = json.dumps(summary)

    # Record the aggregate on the last task's detail for quick eyeballing.
    if result.tasks:
        agg = summary["macro_average"]
        result.tasks[-1].detail += (
            f" || macro: recall@{max_k}={agg[f'recall@{max_k}']:.3f} "
            f"mrr={agg['mrr']:.3f} ndcg@{max_k}={agg[f'ndcg@{max_k}']:.3f}"
        )

    return result
