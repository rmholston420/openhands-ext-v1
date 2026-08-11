# OpenHands-Ext v1 · Session Handoff — 2026-08-11 16:07 EDT

## Current build-sequencing position

- **Phase / gate / step:** Phase 0.4 · gate-4 · step 6c (Perplexity-Max qrels labeling)
- **Sub-step:** q-c01 calibration slice emitted; awaiting user spot-check
- **Ports in progress:** none (labeling task)

## Completed this session

- Rubric G2 pre-labeling amendments (16 cells + line_range_overlap_threshold=0.5)
- Split 3324 pool rows into 14 labeling sessions
- Authored LABELING_PROMPT.md
- Cloned Kosmos @ 1f33519a and Rigpa-LMS @ 55b55539 to /tmp/pool-corpus/
- Read openhands-ext-v1 canonical files: server.py, candidates.py, probes.py, main.py, schema/run.py (identified 4 grade-3 primaries for q-c01)
- Spot-read Kosmos LLM adapters + Rigpa gateway (confirmed no cross-repo primaries)
- Emitted qrels_q-c01.jsonl (103 rows: 15 g3, 3 g2, 4 g1, 81 g0)

## Remaining before current Definition of Done (step 6c)

- User spot-check q-c01 grades → decision on path forward
- Options for remaining 19 queries:
  - (a) Continue calibration-slice mode per query (grade-0-default with primary reads)
  - (b) Full-rigor labeling per session (~45 min/query × 19 = ~14 hr tool time)
  - (c) Hybrid: rigorous for code queries, calibration for docs queries
- Merge all qrels into single qrels.jsonl
- Run session drift-check on any full-rigor session (re-label first 10 rows, verify no changes)
- Lock qrels + append to BUILD_LOG

## Open questions / awaiting user answer

1. Spot-check verdict on q-c01 grades — do the 4 grade-3 primaries look right?
2. Path forward: (a) calibration for all, (b) full-rigor, or (c) hybrid?

## Exact next action

Wait for user spot-check. On approval, either:
- If (a): loop label_qc01.py pattern for q-c02 through q-d10 (adapt PRIMARIES_G3 per query)
- If (b): resume full pool-row-by-row reads for q-c02 (next query in s01_code session)
- If (c): user specifies which queries need full rigor

Commit already pushed to git-agent-proxy.
