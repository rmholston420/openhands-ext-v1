# Perplexity-Max Qrels Labeling Prompt — Phase 0.4 Gate-4 Step 6c

## Setup (once per session)

You are labeling retrieval quality for a code+docs embedding benchmark.
Pinned corpus repos at `/tmp/pool-corpus/`:
- `openhands-ext-v1` @ 5489fb19 (26 py + 42 md)
- `Kosmos` @ 1f33519a on stage-3-13-tektos-intention (392 py + 97 md)
- `Rigpa-LMS` @ 55b55539 (551 py)

## Rubric G2 — Labeler Instructions (verbatim, from `bench/rubrics/full-embedder-scored.json`)

### Label schema
- **grade 0** — Not relevant. Chunk does not answer the query or is off-topic.
- **grade 1** — Marginally relevant. Chunk touches the query topic but doesn't answer it (e.g., mentions the concept in passing, refers to a related but distinct construct).
- **grade 2** — Relevant. Chunk substantively answers the query but is missing at least one meaningful detail the querent would want (e.g., mentions the port but not its adapter; describes the ADR title but not its decision).
- **grade 3** — Directly relevant. Chunk is the answer or a canonical component of the answer (e.g., contains the exact function definition asked about, or the ADR body whose title matches the query intent).

### Role schema
- **role=primary** — The canonical answer chunk(s). A query typically has 1-3 primary chunks. A code query's primary is the def/class or the specific method body being asked about. A docs query's primary is the ADR/section that directly resolves the query.
- **role=secondary** — Chunks that partially answer, provide context, or are near-duplicates of the primary. May have grade 2 or 3.

**Every query MUST have at least one primary chunk with grade 3.** Queries whose corpus has no grade-3 answer are excluded from the qrel set (logged separately as `unanswerable_at_pinned_snapshot`).

### Instructions (verbatim from rubric G2)
1. Read the query. Consider what a natural agent — coder for code queries, planner/PM for docs queries — would want to retrieve.
2. For each pooled candidate chunk (union of top-20 across all 16 cells), assign a grade 0-3 using the definitions above. **Do NOT peek at which cell retrieved it before grading** — labels must be independent of retrieval source to prevent bias. (This session file has `contributed_by` stripped so you cannot see it.)
3. Assign role=primary to the 1-3 chunks that are the query's canonical answer. Everything else that's non-zero grade is role=secondary.
4. If a chunk covers the answer but at a different granularity than another chunk (e.g., a whole file that contains the specific function), grade both, but pick the more specific one as primary.
5. If a chunk contains the answer AND a lot of noise, prefer grade 2 over grade 3 (the retrieval is fine but the presented context is bloated).
6. For docs queries asking "which ADR governs X": the ADR title-and-decision section is grade 3 primary; the ADR references in the spec §17 table are grade 2 secondary; unrelated ADRs are grade 0.
7. For code queries asking "where is X defined": the def line ± its body is grade 3 primary; import statements or references are grade 2 secondary; documentation of the same construct is grade 1 (unless the query explicitly asks about docs).
8. If a query is genuinely unanswerable from the pinned corpus, mark it `unanswerable_at_pinned_snapshot` in a separate field. Do NOT invent grade-3 labels to satisfy the 'at least one primary' constraint.
9. Labeling is done ACROSS the pooled union — same chunks may be pooled from multiple cells. Each unique (query, chunk) pair is labeled exactly once.

### Drift check (per session)
The first 10 labels of each session are re-labeled at session end. **If ANY label changes, halt labeling and file a drift-detection ADR.** Do not attempt to reconcile silently.

## Per-session workflow

You will be handed one JSONL session file at a time (e.g. `s01_code.jsonl`).

1. Read the session header line first (`$type=session_header`) to see which queries this session covers.
2. For each pool_row line, use the `chunk_id` + `repo` + `source_file_path` + `line_range` to open the chunk's source code from `/tmp/pool-corpus/<repo>/<source_file_path>`, lines `line_range[0]`–`line_range[1]`.
3. Read the chunk. Read the query. Assign grade + role.
4. Emit output JSONL row for each label:
   ```json
   {"$type":"qrel","block":"<block>","qid":"<qid>","chunk_id":"<chunk_id>","repo":"<repo>","source_file_path":"<source_file_path>","line_range":[<start>,<end>],"grade":<0-3>,"role":"<primary|secondary>","labeler_note":"<optional 1-line justification>"}
   ```
5. At end of session, re-label the first 10 rows silently and diff.
6. Emit session summary:
   ```json
   {"$type":"session_summary","session_id":"<s##_block>","labels_emitted":<N>,"unanswerable_queries":[<qid>,...],"drift_check_passed":<bool>,"drift_deltas":[<null or list of (chunk_id, old_grade, new_grade)>]}
   ```

## Output location

Save each session's output to `bench/gold/embedder-full-multi-block/labels/qrels_<session_id>.jsonl`.

## Primary key rule for downstream scoring
`(repo, source_file_path, line_range)` — chunker-agnostic. At scoring time, retrieved chunks match a labeled footprint if they share the same `(repo, source_file_path)` AND their `line_range` overlaps the labeled `line_range` by ≥50%.

## Session list

- `s01_code.jsonl` — q-c01, q-c02, q-c03 (263 labels)
- `s02_code.jsonl` — q-c04, q-c06, q-c07 (228 labels)
- `s03_code.jsonl` — q-c09, q-c10, q-c12 (291 labels)
- `s04_code.jsonl` — q-c14, q-c17, q-c18 (240 labels)
- `s05_code.jsonl` — q-c19, q-c20, q-c23 (233 labels)
- `s06_code.jsonl` — q-c25, q-c26, q-c30 (220 labels)
- `s07_code.jsonl` — q-c32, q-c40 (225 labels)
- `s08_docs.jsonl` — q-d01, q-d02, q-d03, q-d04 (294 labels)
- `s09_docs.jsonl` — q-d06, q-d07, q-d10 (251 labels)
- `s10_docs.jsonl` — q-d12, q-d14, q-d15 (232 labels)
- `s11_docs.jsonl` — q-d17, q-d18, q-d20 (288 labels)
- `s12_docs.jsonl` — q-d24, q-d25, q-d28 (187 labels)
- `s13_docs.jsonl` — q-d29, q-d30, q-d33 (297 labels)
- `s14_docs.jsonl` — q-d34 (75 labels)

**Total: 14 sessions, 3324 labels.**

After all sessions complete, merge into `qrels.jsonl` and lock with `QRELS.locked.sha256`.
