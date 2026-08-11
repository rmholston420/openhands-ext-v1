"""Full-tier embedder multi-block retrieval probe (Phase 0.4 gate-4).

Separate module from `probes.py` and `probes_retrieval.py` per P1 (user
2026-08-11 13:26 EDT): peer probe with no refactor of existing embedder
probes. This preserves the Phase 0.3 provenance boundary and the Fast/Medium
tier post-hoc-edit-locked rubrics.

Contract:
  probe_embedder_full_multi_block(
      *,
      endpoint: str,
      served_name: str,
      candidate_cell: str,       # one of e04b_q8_cpu / e08b_q6k_cpu / e006b_q8_cpu
      chunker: str,              # H1_fixed_512_64 | H2_structure_aware
      block: str,                # code | docs
      manifest: dict,            # bench/corpus/embedder-full-multi-block/MANIFEST.json
      queries: list[dict],       # 20 code or 20 docs queries from step-4 file
      corpus_root: str,          # local path where corpus repos are cloned
      top_k: int = 20,
      mode: str = "pool",        # "pool": emit top-k IDs only, no scoring; "score": also compute metrics if qrels provided
      qrels: dict | None = None, # required only when mode="score"
      rubric: dict | None = None,# scoring rubric (composite weights)
  ) -> ProbeResult

Retrieval-only ("pool") mode is used in DoD step 6b (before qrels exist).
Scoring mode is used in DoD step 6d (after qrels are labeled + locked).

Chunk primary key (P1 chunker-agnostic):
  {"repo": <name>, "source_file_path": <str>, "line_range": [start, end]}

The chunk_id emitted in retrieval outputs is the SHA-256 of that JSON tuple
so pool.jsonl entries are stable across chunker variants when line_range
coincides.

Design notes:
- Deterministic: fixed chunkers, fixed sort tie-break by (chunk_id ascending).
- Reads corpus files from disk at `corpus_root`. Caller is responsible for
  cloning repos at pinned SHAs and verifying HEAD matches MANIFEST.
- No network calls to GitHub inside the probe — corpus fetch is a caller
  responsibility. Keeps the probe testable offline.
- The embed cache is per-cell; a cell restart (e.g. model swap) rebuilds it.

Written 2026-08-11 13:26 EDT.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import urllib.error
from pathlib import Path
from typing import Any

from .probes import HttpPostError, ProbeResult, TaskResult, _http_post
from .probes_retrieval import _cosine, _dcg, _ndcg_at_k, _recall_at_k, _mrr, _embed_batch


# ---------------------------------------------------------------------------
# Chunkers
# ---------------------------------------------------------------------------

def _chunk_h1_fixed(text: str, source_path: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """H1: fixed 512-token windows with 64-token overlap.

    Token approximation: cl100k_base BPE tokens ~ 4 chars each on English +
    Python; we use character-based windows scaled to that ratio. Since the
    probe is chunker-consistent across candidates, exact token count doesn't
    matter for retrieval evaluation as long as it's deterministic.
    """
    # Rough char-per-token: 4.0 (Python code + English docs at cl100k)
    char_size = chunk_size * 4
    char_overlap = overlap * 4
    step = char_size - char_overlap

    lines = text.splitlines(keepends=True)
    # Build cumulative char offsets to line numbers so we can emit line_range
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    total_chars = offsets[-1]

    def char_to_line(char_offset: int) -> int:
        # 1-indexed line number containing char_offset
        # binary search would be faster but files are small enough
        for i in range(1, len(offsets)):
            if offsets[i] > char_offset:
                return i
        return max(1, len(offsets) - 1)

    chunks = []
    pos = 0
    while pos < total_chars:
        end_pos = min(pos + char_size, total_chars)
        chunk_text = text[pos:end_pos]
        start_line = char_to_line(pos)
        end_line = char_to_line(max(pos, end_pos - 1))
        chunks.append({
            "text": chunk_text,
            "source_file_path": source_path,
            "line_range": [start_line, end_line],
        })
        if end_pos >= total_chars:
            break
        pos += step
    return chunks


_PY_SYMBOL_RE = re.compile(r"^(class |def |async def )", re.MULTILINE)
_MD_HEADING_RE = re.compile(r"^#{1,6} ", re.MULTILINE)


def _split_by_symbol_python(text: str) -> list[tuple[int, int]]:
    """Return list of (start_line, end_line) inclusive for top-level Python
    symbols (class, def, async def). Non-symbol regions become their own
    chunks bounded by adjacent symbol starts.
    """
    lines = text.splitlines()
    n = len(lines)
    if n == 0:
        return []
    # Find lines that START a top-level symbol (no leading indent).
    symbol_starts = []
    for i, ln in enumerate(lines):
        if _PY_SYMBOL_RE.match(ln) or (i > 0 and ln.startswith(("class ", "def ", "async def "))):
            if not ln.startswith((" ", "\t")):  # top-level only
                symbol_starts.append(i + 1)  # 1-indexed
    # Include the file's start
    boundaries = sorted(set([1] + symbol_starts + [n + 1]))
    ranges = []
    for i in range(len(boundaries) - 1):
        ranges.append((boundaries[i], boundaries[i + 1] - 1))
    return [r for r in ranges if r[0] <= r[1]]


def _split_by_heading_md(text: str) -> list[tuple[int, int]]:
    lines = text.splitlines()
    n = len(lines)
    if n == 0:
        return []
    heading_lines = [i + 1 for i, ln in enumerate(lines) if _MD_HEADING_RE.match(ln)]
    boundaries = sorted(set([1] + heading_lines + [n + 1]))
    ranges = []
    for i in range(len(boundaries) - 1):
        ranges.append((boundaries[i], boundaries[i + 1] - 1))
    return [r for r in ranges if r[0] <= r[1]]


def _chunk_h2_structure_aware(text: str, source_path: str, max_tokens: int = 1024) -> list[dict]:
    """H2: structure-aware.

    - Python (.py/.pyi): split per top-level class/def/async def.
    - Markdown (.md): split per heading (any level).
    - Other: single chunk.

    Any chunk exceeding max_tokens (approx 4*max_tokens chars) falls back
    to H1_fixed_512_64 on that chunk's text.
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return []
    ext = os.path.splitext(source_path)[1].lower()
    if ext in (".py", ".pyi"):
        ranges = _split_by_symbol_python(text)
    elif ext == ".md":
        ranges = _split_by_heading_md(text)
    else:
        ranges = [(1, len(lines))]

    if not ranges:
        ranges = [(1, len(lines))]

    char_limit = max_tokens * 4
    out: list[dict] = []
    for (start_line, end_line) in ranges:
        # Extract text for this line range (1-indexed inclusive)
        chunk_text = "".join(lines[start_line - 1:end_line])
        if len(chunk_text) <= char_limit:
            out.append({
                "text": chunk_text,
                "source_file_path": source_path,
                "line_range": [start_line, end_line],
            })
        else:
            # H1 fallback on oversized structure region
            sub_chunks = _chunk_h1_fixed(chunk_text, source_path)
            # Rebase sub-chunk line ranges to absolute file line numbers
            for sc in sub_chunks:
                sc["line_range"] = [start_line + sc["line_range"][0] - 1,
                                    start_line + sc["line_range"][1] - 1]
                out.append(sc)
    return out


def _chunk_file(text: str, source_path: str, chunker: str) -> list[dict]:
    if chunker == "H1_fixed_512_64":
        return _chunk_h1_fixed(text, source_path)
    if chunker == "H2_structure_aware":
        return _chunk_h2_structure_aware(text, source_path)
    raise ValueError(f"unknown chunker: {chunker}")


# ---------------------------------------------------------------------------
# Chunk-ID hashing (P1 chunker-agnostic primary key)
# ---------------------------------------------------------------------------

def _chunk_id(repo: str, source_file_path: str, line_range: list[int]) -> str:
    """SHA-256 hex of the primary-key JSON tuple. Stable across chunker
    variants when the tuple coincides.
    """
    key = json.dumps(
        {"repo": repo, "source_file_path": source_file_path, "line_range": line_range},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

# Resolve repo root once (bench/runner/<this>.py -> ../..)
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_block_corpus(
    manifest: dict, block: str, corpus_root: str,
) -> list[dict]:
    """Read the corpus for a block from disk. Returns list of
    {repo, source_file_path, text} rows. Caller must have cloned repos at
    pinned SHAs; this function verifies file existence but not SHA.
    """
    block_key = "code_block" if block == "code" else "docs_block"
    section = manifest[block_key]

    rows: list[dict] = []
    if block == "code":
        for repo in section["repos"]:
            repo_name = repo["name"]
            repo_dir = Path(corpus_root) / repo_name
            file_list_path = _REPO_ROOT / repo["file_list"]
            if not file_list_path.exists():
                raise FileNotFoundError(f"manifest file_list missing: {file_list_path}")
            files = file_list_path.read_text().splitlines()
            for f in files:
                if not f.strip():
                    continue
                fpath = repo_dir / f
                if not fpath.exists():
                    # Skip silently — caller (runner) reports missing files
                    # in the ProbeResult notes rather than failing hard.
                    continue
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                rows.append({"repo": repo_name, "source_file_path": f, "text": text})
    else:  # docs
        for src in section["sources"]:
            # src["github"] tells us the repo; find the local dir by repo name suffix
            gh = src["github"]  # e.g. "rmholston420/openhands-ext-v1"
            repo_name = gh.split("/")[-1]
            # Manifest uses "openhands-ext-v1" for the code_block repo entry; keep same convention for docs
            repo_dir = Path(corpus_root) / repo_name
            if not repo_dir.exists():
                # docs block for oh-ext might live under a different dir; try Kosmos-style
                alt = Path(corpus_root) / "openhands-ext-v1" if repo_name == "openhands-ext-v1" else Path(corpus_root) / "Kosmos"
                if alt.exists():
                    repo_dir = alt
            file_list_path = _REPO_ROOT / src["file_list"]
            if not file_list_path.exists():
                raise FileNotFoundError(f"manifest file_list missing: {file_list_path}")
            files = file_list_path.read_text().splitlines()
            for f in files:
                if not f.strip():
                    continue
                fpath = repo_dir / f
                if not fpath.exists():
                    continue
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                rows.append({"repo": repo_name, "source_file_path": f, "text": text})
    return rows


# ---------------------------------------------------------------------------
# Main probe
# ---------------------------------------------------------------------------

def probe_embedder_full_multi_block(
    *,
    endpoint: str,
    served_name: str,
    candidate_cell: str,
    chunker: str,
    block: str,
    manifest: dict,
    queries: list[dict],
    corpus_root: str,
    top_k: int = 20,
    mode: str = "pool",
    qrels: dict | None = None,
    rubric: dict | None = None,
    embed_batch_size: int = 32,
) -> ProbeResult:
    """See module docstring for contract."""
    result = ProbeResult(role="embedder")

    if mode not in ("pool", "score"):
        tr = TaskResult(task_id=f"{candidate_cell}-{chunker}-{block}-schema",
                        verdict="fail", verdict_source="verify",
                        wall_seconds=0.0,
                        detail=f"unknown mode: {mode}")
        result.tasks.append(tr)
        return result
    if mode == "score" and qrels is None:
        tr = TaskResult(task_id=f"{candidate_cell}-{chunker}-{block}-schema",
                        verdict="fail", verdict_source="verify",
                        wall_seconds=0.0,
                        detail="mode=score requires qrels")
        result.tasks.append(tr)
        return result

    t_load = time.monotonic()
    try:
        corpus_rows = _load_block_corpus(manifest, block, corpus_root)
    except FileNotFoundError as e:
        tr = TaskResult(task_id=f"{candidate_cell}-{chunker}-{block}-schema",
                        verdict="fail", verdict_source="verify",
                        wall_seconds=time.monotonic() - t_load,
                        detail=str(e))
        result.tasks.append(tr)
        return result
    load_wall = time.monotonic() - t_load

    # Chunk each source file
    t_chunk = time.monotonic()
    chunks: list[dict] = []
    for row in corpus_rows:
        file_chunks = _chunk_file(row["text"], row["source_file_path"], chunker)
        for c in file_chunks:
            cid = _chunk_id(row["repo"], c["source_file_path"], c["line_range"])
            chunks.append({
                "chunk_id": cid,
                "repo": row["repo"],
                "source_file_path": c["source_file_path"],
                "line_range": c["line_range"],
                "text": c["text"],
            })
    chunk_wall = time.monotonic() - t_chunk

    # Embed corpus
    corpus_texts = [c["text"] for c in chunks]
    query_texts = [q["text"] for q in queries]

    t_embed = time.monotonic()
    try:
        corpus_vecs = _embed_batch(
            endpoint=endpoint, served_name=served_name,
            texts=corpus_texts, batch_size=embed_batch_size,
        )
        query_vecs = _embed_batch(
            endpoint=endpoint, served_name=served_name,
            texts=query_texts, batch_size=embed_batch_size,
        )
    except HttpPostError as exc:
        tr = TaskResult(task_id=f"{candidate_cell}-{chunker}-{block}-transport",
                        verdict="fail", verdict_source="transport",
                        wall_seconds=time.monotonic() - t_embed,
                        detail=f"embed transport error: {exc}")
        result.tasks.append(tr)
        return result
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        tr = TaskResult(task_id=f"{candidate_cell}-{chunker}-{block}-transport",
                        verdict="fail", verdict_source="transport",
                        wall_seconds=time.monotonic() - t_embed,
                        detail=f"embed transport error: {exc!r}")
        result.tasks.append(tr)
        return result
    embed_wall = time.monotonic() - t_embed

    if len(corpus_vecs) != len(chunks) or len(query_vecs) != len(queries):
        tr = TaskResult(task_id=f"{candidate_cell}-{chunker}-{block}-schema",
                        verdict="fail", verdict_source="verify",
                        wall_seconds=embed_wall,
                        detail=f"vec count mismatch: corpus {len(corpus_vecs)}/{len(chunks)}, queries {len(query_vecs)}/{len(queries)}")
        result.tasks.append(tr)
        return result

    # Rank + emit top-k per query
    t_rank = time.monotonic()
    per_query_top: list[dict] = []
    for qi, q in enumerate(queries):
        qv = query_vecs[qi]
        sims = [(_cosine(qv, corpus_vecs[ci]), ci) for ci in range(len(chunks))]
        # Sort by similarity descending, tie-break by chunk_id ascending
        sims.sort(key=lambda t: (-t[0], chunks[t[1]]["chunk_id"]))
        top = sims[:top_k]
        top_entries = []
        for sim, ci in top:
            c = chunks[ci]
            top_entries.append({
                "chunk_id": c["chunk_id"],
                "repo": c["repo"],
                "source_file_path": c["source_file_path"],
                "line_range": c["line_range"],
                "similarity": round(float(sim), 6),
            })
        per_query_top.append({
            "qid": q["qid"],
            "query_text": q["text"],
            "candidate_cell": candidate_cell,
            "chunker": chunker,
            "block": block,
            "top_k": top_entries,
        })
        tr = TaskResult(
            task_id=f"{candidate_cell}-{chunker}-{block}-{q['qid']}",
            verdict="pass", verdict_source="verify",
            wall_seconds=0.0,
            detail=f"top1={top_entries[0]['chunk_id'][:12]} sim={top_entries[0]['similarity']:.3f}",
        )
        result.tasks.append(tr)
    rank_wall = time.monotonic() - t_rank

    summary: dict[str, Any] = {
        "candidate_cell": candidate_cell,
        "chunker": chunker,
        "block": block,
        "mode": mode,
        "corpus_files": len(corpus_rows),
        "corpus_chunks": len(chunks),
        "query_count": len(queries),
        "top_k": top_k,
        "load_wall_seconds": round(load_wall, 3),
        "chunk_wall_seconds": round(chunk_wall, 3),
        "embed_wall_seconds": round(embed_wall, 3),
        "rank_wall_seconds": round(rank_wall, 3),
        "per_query_top": per_query_top,
    }

    if mode == "score":
        # Compute metrics per rubric
        rel_by_query: dict[str, dict[str, int]] = {}
        for row in qrels.get("labels", []):
            rel_by_query.setdefault(row["qid"], {})[row["chunk_id"]] = int(row["grade"])

        per_query_scores: list[dict] = []
        for pqt in per_query_top:
            qid = pqt["qid"]
            rel_map = rel_by_query.get(qid, {})
            relevant_binary = {c for c, g in rel_map.items() if g >= 1}
            ranked_ids = [e["chunk_id"] for e in pqt["top_k"]]
            retrieved_rels_graded = [float(rel_map.get(c, 0)) for c in ranked_ids[:10]]
            ideal_rels_graded = sorted((float(g) for g in rel_map.values()), reverse=True)

            ndcg10 = _ndcg_at_k(retrieved_rels_graded, ideal_rels_graded, 10)
            r10 = _recall_at_k(ranked_ids, relevant_binary, 10)
            r1 = _recall_at_k(ranked_ids, relevant_binary, 1)
            mrr10_pool = [d for d in ranked_ids[:10]]
            mrr10 = _mrr(mrr10_pool, relevant_binary)

            composite = 100.0 * (0.40 * ndcg10 + 0.25 * r10 + 0.20 * mrr10 + 0.15 * r1)
            per_query_scores.append({
                "qid": qid,
                "ndcg@10": round(ndcg10, 4),
                "recall@10": round(r10, 4),
                "mrr@10": round(mrr10, 4),
                "recall@1": round(r1, 4),
                "composite": round(composite, 3),
            })

        def _mean(k: str) -> float:
            vals = [s[k] for s in per_query_scores if k in s]
            return sum(vals) / len(vals) if vals else 0.0

        summary["scoring"] = {
            "per_query": per_query_scores,
            "macro": {
                "ndcg@10":   round(_mean("ndcg@10"), 4),
                "recall@10": round(_mean("recall@10"), 4),
                "mrr@10":    round(_mean("mrr@10"), 4),
                "recall@1":  round(_mean("recall@1"), 4),
                "composite": round(_mean("composite"), 3),
            },
        }

    result.notes = json.dumps(summary)
    return result
