#!/usr/bin/env python3
"""One-shot BEIR SciDocs subset materializer for embedder-medium portability arm.

Reads bench/tasks/embedder-medium-beir-scidocs.json (config only), downloads
the BEIR SciDocs dataset if not cached, materializes a deterministic 5000-doc
+ 100-query subset by SHA-256(id) hash rank, filters qrels to the sampled
subset, and writes a materialized inline-corpus task file at:

  bench/tasks/embedder-medium-beir-scidocs-materialized.json

This inline file has the same shape as the domain-arm task file (corpus,
queries, qrels all inline) so the harness `probe_embedder_retrieval` can
consume it without needing a network fetch at run time.

Run once per Colossus workstation. Requires network access on first run;
cached under ~/.cache/beir/scidocs afterward.

Post-hoc note: the materialized file is derived, not authored — it is
regenerable from the config file at any time. It is NOT post-hoc-edit-locked
per ADR-0016, but its content IS deterministic given the config file's
sampling parameters (SHA-256 rank sort). Changing the sampling parameters
in the config file requires a superseding ADR.

Usage:
  python3 scripts/materialize-beir-scidocs-subset.py \\
    [--config bench/tasks/embedder-medium-beir-scidocs.json] \\
    [--output bench/tasks/embedder-medium-beir-scidocs-materialized.json] \\
    [--force]

Dependencies:
  pip install beir
  (Uses beir.datasets.data_loader.GenericDataLoader + beir.util.download_and_unzip)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _hash_rank(id_str: str) -> str:
    """Return SHA-256 hex digest; sort ascending on this string to pick subset."""
    return hashlib.sha256(id_str.encode("utf-8")).hexdigest()


def _load_beir_scidocs(cache_dir: Path, download_url: str) -> tuple[dict, dict, dict]:
    """Load full BEIR SciDocs. Returns (corpus, queries, qrels).

    corpus[doc_id] = {"title": ..., "text": ...}
    queries[query_id] = "query text"
    qrels[query_id] = {doc_id: relevance_int}
    """
    try:
        from beir import util as beir_util
        from beir.datasets.data_loader import GenericDataLoader
    except ImportError as exc:
        print(
            "ERROR: `beir` package not installed. Install with:\n"
            "  pip install beir\n"
            f"(underlying import error: {exc})",
            file=sys.stderr,
        )
        raise SystemExit(2)

    cache_dir.mkdir(parents=True, exist_ok=True)
    data_path = cache_dir / "scidocs"
    if not data_path.exists():
        print(f"Downloading BEIR SciDocs to {cache_dir} ...", file=sys.stderr)
        beir_util.download_and_unzip(download_url, str(cache_dir))

    loader = GenericDataLoader(data_folder=str(data_path))
    corpus, queries, qrels = loader.load(split="test")
    return corpus, queries, qrels


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    default_config = Path(__file__).resolve().parent.parent / "bench/tasks/embedder-medium-beir-scidocs.json"
    default_output = default_config.with_name("embedder-medium-beir-scidocs-materialized.json")
    ap.add_argument("--config", default=str(default_config), help="config file path")
    ap.add_argument("--output", default=str(default_output), help="materialized output file path")
    ap.add_argument("--force", action="store_true", help="overwrite existing materialized file")
    args = ap.parse_args()

    config_path = Path(args.config)
    output_path = Path(args.output)

    if output_path.exists() and not args.force:
        print(f"REFUSE: {output_path} exists. Pass --force to regenerate.", file=sys.stderr)
        return 3

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    subset_docs_n = int(cfg["corpus"]["subset"]["docs"])
    subset_queries_n = int(cfg["corpus"]["subset"]["queries"])
    download_url = cfg["corpus"]["download_url"]
    cache_dir = Path(cfg["corpus"]["cache_dir"]).expanduser()

    corpus, queries, qrels_raw = _load_beir_scidocs(cache_dir, download_url)

    # Deterministic subset selection.
    all_doc_ids = sorted(corpus.keys(), key=_hash_rank)[:subset_docs_n]
    all_query_ids = sorted(queries.keys(), key=_hash_rank)[:subset_queries_n]
    doc_id_set = set(all_doc_ids)
    query_id_set = set(all_query_ids)

    # Materialize inline corpus.
    corpus_inline = []
    for doc_id in all_doc_ids:
        doc = corpus[doc_id]
        text = doc.get("title", "") + " " + doc.get("text", "")
        corpus_inline.append({"doc_id": doc_id, "text": text.strip()})

    # Materialize inline queries.
    queries_inline = [
        {"query_id": qid, "text": queries[qid]}
        for qid in all_query_ids
    ]

    # Filter qrels to the sampled subset.
    qrels_inline = []
    for qid, doc_rel_map in qrels_raw.items():
        if qid not in query_id_set:
            continue
        for doc_id, rel in doc_rel_map.items():
            if doc_id not in doc_id_set:
                continue
            qrels_inline.append({"query_id": qid, "doc_id": doc_id, "relevance": int(rel)})

    materialized = {
        "$comment": (
            "MATERIALIZED artifact — do NOT hand-edit. Regenerate from "
            "bench/tasks/embedder-medium-beir-scidocs.json via scripts/"
            "materialize-beir-scidocs-subset.py. Determinism guaranteed by "
            "SHA-256 hash-rank sampling defined in the config file."
        ),
        "schema_version": cfg.get("schema_version", "1.0.0"),
        "tier": cfg.get("tier"),
        "role": cfg.get("role"),
        "arm": cfg.get("arm"),
        "task_id": cfg.get("task_id"),
        "config_source": str(config_path.relative_to(config_path.resolve().parent.parent)),
        "corpus": corpus_inline,
        "queries": queries_inline,
        "qrels": qrels_inline,
        "metrics": cfg.get("metrics"),
        "runtime_expectations": cfg.get("runtime_expectations"),
        "qrels_notes": {
            "relevance_scale": "BEIR SciDocs test qrels — 0/1 binary at source",
            "total_qrels_rows": len(qrels_inline),
            "total_labeled_docs": len({row["doc_id"] for row in qrels_inline}),
        },
    }

    output_path.write_text(json.dumps(materialized, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: materialized {len(corpus_inline)} docs, {len(queries_inline)} queries, "
        f"{len(qrels_inline)} qrels rows -> {output_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
