"""Driver for Phase 0.4 gate-4 DoD step 6b (pool-only) and step 6d (score).

Usage:
    # Step 6b (build pool for ONE cell)
    python -m bench.runner.run_embedder_full_multi_block pool \\
        --candidate e04b_q8_cpu \\
        --chunker H1_fixed_512_64 \\
        --block code \\
        --endpoint http://localhost:8085 \\
        --served-name qwen3-embedding-4B-Q8_0 \\
        --corpus-root /tmp/pool-corpus \\
        --out ~/.forge-oh/bench_embedder_full_multi_block/pool_$(date -u +%Y%m%dT%H%M%SZ).jsonl

    # Step 6b (build pool for ALL 12 cells serially — enforces co-residency)
    python -m bench.runner.run_embedder_full_multi_block pool-all \\
        --corpus-root /tmp/pool-corpus \\
        --out-dir ~/.forge-oh/bench_embedder_full_multi_block

    # Step 6d (score one cell against locked qrels)
    python -m bench.runner.run_embedder_full_multi_block score \\
        --candidate e04b_q8_cpu --chunker H1_fixed_512_64 --block code \\
        --endpoint http://localhost:8085 \\
        --served-name qwen3-embedding-4B-Q8_0 \\
        --corpus-root /tmp/pool-corpus \\
        --qrels /tmp/oh-ext/bench/gold/embedder-full-multi-block/qrels.jsonl \\
        --out ~/.forge-oh/bench_embedder_full_multi_block/score_...

Written 2026-08-11 13:26 EDT.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Resolve REPO_ROOT from this file's location: bench/runner/<this>.py -> ../..
REPO_ROOT = Path(__file__).resolve().parents[2]

# Import the probe (respect module boundary)
sys.path.insert(0, str(REPO_ROOT))
from bench.runner.probes_embedder_multi_block import probe_embedder_full_multi_block  # noqa: E402


MANIFEST_PATH = REPO_ROOT / "bench/corpus/embedder-full-multi-block/MANIFEST.json"
QUERIES_PATH = REPO_ROOT / "bench/tasks/embedder-full-multi-block.queries.json"
RUBRIC_PATH = REPO_ROOT / "bench/rubrics/full-embedder-scored.json"

# Cell registry: (candidate_cell, model_gguf_basename, expected_size_gib)
CELLS = {
    "e04b_q8_cpu":   ("qwen3-embedding-4B-Q8_0.gguf",   3.99),
    "e08b_q6k_cpu":  ("qwen3-embedding-8B-Q6_K.gguf",   5.79),
    "e006b_q8_cpu":  ("qwen3-embedding-0.6B-Q8_0.gguf", 0.60),
}
CHUNKERS = ["H1_fixed_512_64", "H2_structure_aware"]
BLOCKS = ["code", "docs"]


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def _load_queries_block(block: str) -> list[dict]:
    qfile = json.loads(QUERIES_PATH.read_text())
    selected = qfile["final_selected_query_ids"]
    pool = {q["qid"]: q for q in qfile["code_block_queries"]} if block == "code" else {q["qid"]: q for q in qfile["docs_block_queries"]}
    prefix = "q-c" if block == "code" else "q-d"
    return [pool[qid] for qid in selected if qid.startswith(prefix) and qid in pool]


def _ensure_corpus(corpus_root: str, manifest: dict) -> None:
    """Clone (or verify) each repo at its pinned SHA under corpus_root.

    Idempotent: skips a repo if the pinned SHA is already checked out.
    """
    corpus_root_p = Path(corpus_root)
    corpus_root_p.mkdir(parents=True, exist_ok=True)

    # Code block repos (superset)
    for repo in manifest["code_block"]["repos"]:
        name = repo["name"]
        gh = repo["github"]
        sha = repo["snapshot_commit_sha"]
        target = corpus_root_p / name
        if target.exists():
            # Verify HEAD
            try:
                head = subprocess.check_output(
                    ["git", "-C", str(target), "rev-parse", "HEAD"], text=True
                ).strip()
                if head == sha:
                    print(f"[corpus] {name} already at {sha[:12]} — skip", file=sys.stderr)
                    continue
                else:
                    print(f"[corpus] {name} at {head[:12]}, expected {sha[:12]} — refetching", file=sys.stderr)
            except subprocess.CalledProcessError:
                pass
        # Clone (fresh)
        if target.exists():
            subprocess.run(["rm", "-rf", str(target)], check=True)
        url = f"https://github.com/{gh}.git"
        # Full clone (shallow doesn't allow arbitrary SHA checkout on all providers)
        subprocess.run(["git", "clone", url, str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", sha], check=True)
        head = subprocess.check_output(
            ["git", "-C", str(target), "rev-parse", "HEAD"], text=True
        ).strip()
        if head != sha:
            raise RuntimeError(f"corpus SHA mismatch for {name}: expected {sha}, got {head}")
        print(f"[corpus] {name} @ {sha[:12]} ready ({repo['file_count']} files pinned)", file=sys.stderr)


def cmd_pool(args) -> None:
    manifest = _load_manifest()
    _ensure_corpus(args.corpus_root, manifest)
    queries = _load_queries_block(args.block)

    print(f"[probe] cell={args.candidate} chunker={args.chunker} block={args.block} queries={len(queries)}", file=sys.stderr)
    t0 = time.monotonic()
    result = probe_embedder_full_multi_block(
        endpoint=args.endpoint,
        served_name=args.served_name,
        candidate_cell=args.candidate,
        chunker=args.chunker,
        block=args.block,
        manifest=manifest,
        queries=queries,
        corpus_root=args.corpus_root,
        top_k=20,
        mode="pool",
    )
    wall = time.monotonic() - t0
    print(f"[probe] done in {wall:.1f}s", file=sys.stderr)

    if not result.notes:
        print("[probe] EMPTY notes — probe failed. Task details:", file=sys.stderr)
        for tr in result.tasks:
            print(f"  {tr.task_id}: {tr.verdict} — {tr.detail}", file=sys.stderr)
        sys.exit(1)
    summary = json.loads(result.notes)

    # Emit pool as JSONL: one entry per query with its top-20
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        # Header row: metadata
        f.write(json.dumps({
            "$type": "pool_header",
            "candidate_cell": args.candidate,
            "chunker": args.chunker,
            "block": args.block,
            "corpus_chunks": summary["corpus_chunks"],
            "corpus_files": summary["corpus_files"],
            "query_count": summary["query_count"],
            "top_k": summary["top_k"],
            "wall_seconds": round(wall, 2),
            "load_wall_seconds": summary["load_wall_seconds"],
            "chunk_wall_seconds": summary["chunk_wall_seconds"],
            "embed_wall_seconds": summary["embed_wall_seconds"],
            "rank_wall_seconds": summary["rank_wall_seconds"],
        }) + "\n")
        for pqt in summary["per_query_top"]:
            f.write(json.dumps({
                "$type": "pool_row",
                "candidate_cell": args.candidate,
                "chunker": args.chunker,
                "block": args.block,
                **pqt,
            }) + "\n")
    print(f"[probe] pool written: {out_path} ({summary['corpus_chunks']} chunks, {summary['query_count']} queries)", file=sys.stderr)


def cmd_pool_all(args) -> None:
    """Iterate all 12 cells. Enforces co-residency: prompts for cell-swap
    between candidates (a llama.cpp server restart is required).

    In interactive mode, waits for user to signal readiness after each cell
    swap. In --auto mode, expects a wrapper script to handle server swaps.
    """
    manifest = _load_manifest()
    _ensure_corpus(args.corpus_root, manifest)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    session_dir = out_dir / f"pool_session_{ts}"
    session_dir.mkdir()

    cells_ordered: list[tuple[str, str, str]] = []
    for cand in ["e04b_q8_cpu", "e08b_q6k_cpu", "e006b_q8_cpu"]:
        for ch in CHUNKERS:
            for bl in BLOCKS:
                cells_ordered.append((cand, ch, bl))

    print(f"[all] running {len(cells_ordered)} cells. Session dir: {session_dir}", file=sys.stderr)
    print(f"[all] CO-RESIDENCY CONTRACT: caller must stop coder vLLM and planner llama.cpp GPU before starting embedder server for each candidate.", file=sys.stderr)

    manifest_out = session_dir / "session_manifest.json"
    session_meta = {"session_ts_utc": ts, "cells_planned": len(cells_ordered), "cells_completed": [], "cells_failed": []}
    manifest_out.write_text(json.dumps(session_meta, indent=2))

    current_candidate = None
    for i, (cand, ch, bl) in enumerate(cells_ordered):
        if cand != current_candidate:
            if not args.auto:
                print(f"\n[all] cell {i + 1}/{len(cells_ordered)} needs candidate swap to {cand} ({CELLS[cand][0]}).", file=sys.stderr)
                print(f"[all] 1) docker rm -f vllm-coder  (stop coder if running)", file=sys.stderr)
                print(f"[all] 2) stop planner llama.cpp GPU server", file=sys.stderr)
                print(f"[all] 3) start llama-server with -ngl 0 --model models/{CELLS[cand][0]} on port {args.embedder_port}", file=sys.stderr)
                print(f"[all] 4) verify: curl -sf http://localhost:{args.embedder_port}/v1/models", file=sys.stderr)
                input(f"[all] press ENTER when {cand} is serving on {args.endpoint}...")
            current_candidate = cand

        queries = _load_queries_block(bl)
        cell_out = session_dir / f"pool_{cand}_{ch}_{bl}.jsonl"
        print(f"[all] cell {i + 1}/{len(cells_ordered)}: {cand} / {ch} / {bl} -> {cell_out.name}", file=sys.stderr)
        t0 = time.monotonic()
        try:
            result = probe_embedder_full_multi_block(
                endpoint=args.endpoint,
                served_name=args.served_name_pattern.format(candidate=cand),
                candidate_cell=cand,
                chunker=ch,
                block=bl,
                manifest=manifest,
                queries=queries,
                corpus_root=args.corpus_root,
                top_k=20,
                mode="pool",
            )
            wall = time.monotonic() - t0
            if not result.notes:
                fail_reasons = [f"{tr.task_id}: {tr.detail}" for tr in result.tasks[:5]]
                session_meta["cells_failed"].append({"cell": f"{cand}/{ch}/{bl}", "wall_seconds": round(wall, 1), "reasons": fail_reasons})
                print(f"[all] FAIL: {cand}/{ch}/{bl} — {fail_reasons}", file=sys.stderr)
                continue
            summary = json.loads(result.notes)
            with cell_out.open("w") as f:
                f.write(json.dumps({
                    "$type": "pool_header",
                    "candidate_cell": cand, "chunker": ch, "block": bl,
                    **{k: summary[k] for k in ["corpus_chunks", "corpus_files", "query_count", "top_k", "load_wall_seconds", "chunk_wall_seconds", "embed_wall_seconds", "rank_wall_seconds"]},
                    "wall_seconds": round(wall, 2),
                }) + "\n")
                for pqt in summary["per_query_top"]:
                    f.write(json.dumps({"$type": "pool_row", **pqt}) + "\n")
            session_meta["cells_completed"].append({"cell": f"{cand}/{ch}/{bl}", "wall_seconds": round(wall, 1), "corpus_chunks": summary["corpus_chunks"]})
            manifest_out.write_text(json.dumps(session_meta, indent=2))
            print(f"[all] OK: {cand}/{ch}/{bl} in {wall:.1f}s ({summary['corpus_chunks']} chunks)", file=sys.stderr)
        except Exception as e:
            session_meta["cells_failed"].append({"cell": f"{cand}/{ch}/{bl}", "reason": str(e)})
            manifest_out.write_text(json.dumps(session_meta, indent=2))
            print(f"[all] EXCEPTION: {cand}/{ch}/{bl} — {e}", file=sys.stderr)

    print(f"\n[all] SESSION COMPLETE. {len(session_meta['cells_completed'])}/{len(cells_ordered)} cells OK.", file=sys.stderr)
    print(f"[all] session manifest: {manifest_out}", file=sys.stderr)


def cmd_dedupe_pool(args) -> None:
    """Aggregate all 12 per-cell pool files into a single deduplicated
    pool.jsonl for labeling. Each row is one unique (query, chunk) pair.
    """
    session_dir = Path(args.session_dir)
    seen: set[tuple[str, str]] = set()
    unique_rows: list[dict] = []
    for cell_file in sorted(session_dir.glob("pool_*.jsonl")):
        with cell_file.open() as f:
            for line in f:
                row = json.loads(line)
                if row.get("$type") != "pool_row":
                    continue
                qid = row["qid"]
                for entry in row["top_k"]:
                    key = (qid, entry["chunk_id"])
                    if key in seen:
                        continue
                    seen.add(key)
                    # Retain retrieval context for the labeler (chunk path, line range)
                    unique_rows.append({
                        "qid": qid,
                        "query_text": row["query_text"],
                        "chunk_id": entry["chunk_id"],
                        "repo": entry["repo"],
                        "source_file_path": entry["source_file_path"],
                        "line_range": entry["line_range"],
                        "block": row["block"],
                    })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        f.write(json.dumps({"$type": "pool_dedup_header", "unique_pairs": len(unique_rows), "session_dir": str(session_dir)}) + "\n")
        for r in unique_rows:
            f.write(json.dumps(r) + "\n")
    print(f"[dedupe] {len(unique_rows)} unique (query, chunk) pairs -> {out}", file=sys.stderr)


def cmd_score(args) -> None:
    manifest = _load_manifest()
    _ensure_corpus(args.corpus_root, manifest)
    queries = _load_queries_block(args.block)
    qrels_raw = [json.loads(l) for l in Path(args.qrels).read_text().splitlines() if l.strip()]
    qrels_obj = {"labels": [r for r in qrels_raw if r.get("$type") != "qrels_header"]}
    rubric = json.loads(RUBRIC_PATH.read_text())

    result = probe_embedder_full_multi_block(
        endpoint=args.endpoint,
        served_name=args.served_name,
        candidate_cell=args.candidate,
        chunker=args.chunker,
        block=args.block,
        manifest=manifest,
        queries=queries,
        corpus_root=args.corpus_root,
        top_k=20,
        mode="score",
        qrels=qrels_obj,
        rubric=rubric,
    )
    summary = json.loads(result.notes)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"[score] macro: {summary['scoring']['macro']}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_pool = sub.add_parser("pool", help="pool one cell")
    p_pool.add_argument("--candidate", required=True, choices=list(CELLS))
    p_pool.add_argument("--chunker", required=True, choices=CHUNKERS)
    p_pool.add_argument("--block", required=True, choices=BLOCKS)
    p_pool.add_argument("--endpoint", required=True)
    p_pool.add_argument("--served-name", required=True)
    p_pool.add_argument("--corpus-root", required=True)
    p_pool.add_argument("--out", required=True)
    p_pool.set_defaults(func=cmd_pool)

    p_all = sub.add_parser("pool-all", help="pool all 12 cells")
    p_all.add_argument("--endpoint", default="http://localhost:8085")
    p_all.add_argument("--embedder-port", type=int, default=8085)
    p_all.add_argument("--served-name-pattern", default="{candidate}")
    p_all.add_argument("--corpus-root", required=True)
    p_all.add_argument("--out-dir", required=True)
    p_all.add_argument("--auto", action="store_true", help="skip interactive prompts (caller manages server swaps)")
    p_all.set_defaults(func=cmd_pool_all)

    p_ded = sub.add_parser("dedupe-pool", help="merge 12 cell pool files -> single labelable pool.jsonl")
    p_ded.add_argument("--session-dir", required=True)
    p_ded.add_argument("--out", required=True)
    p_ded.set_defaults(func=cmd_dedupe_pool)

    p_score = sub.add_parser("score", help="score one cell against locked qrels")
    p_score.add_argument("--candidate", required=True, choices=list(CELLS))
    p_score.add_argument("--chunker", required=True, choices=CHUNKERS)
    p_score.add_argument("--block", required=True, choices=BLOCKS)
    p_score.add_argument("--endpoint", required=True)
    p_score.add_argument("--served-name", required=True)
    p_score.add_argument("--corpus-root", required=True)
    p_score.add_argument("--qrels", required=True)
    p_score.add_argument("--out", required=True)
    p_score.set_defaults(func=cmd_score)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
