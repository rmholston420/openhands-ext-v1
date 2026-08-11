# bench/tasks — Task-set JSON contract

Each file in this directory defines the set of inputs the Phase 0 tier
runner sends to one role at one tier. The runner (`bench/runner/probes.py`)
loads a JSON file, validates its shape, drives the model against it, and
maps the results to the `BenchRun` categories in `bench/schema/`.

Task-set files are **timestamped and immutable** once the first scored
elimination has been performed against them (see spec §0.0a). Amendments
require an ADR that supersedes ADR-0007 or a follow-on file with a bumped
`schema_version`.

## Common top-level keys (all roles)

- `schema_version` — semver of the task-set format.
- `tier` — `"fast" | "medium" | "full"`.
- `role` — `"coder" | "planner" | "embedder"`.
- `authored_utc` — ISO-8601 timestamp when this file was authored/locked.
- `budget_tokens` — max_tokens the runner will pass on each chat completion.
- `$comment` — free-text description; ignored by the runner.

## Role-specific fields

### coder (`bench/tasks/coder-fast.json`)

Each item in `tasks[]`:

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable id used in result filenames + logs |
| `prompt` | string | User-message content sent to the coder |
| `fixtures` | object | `{ path: content }` to pre-populate in the workspace |
| `expected_tool_sequence` | list[string] | Tool names, in order, the coder should call |
| `expected_tool_sequence_tolerance` | string (optional) | e.g. `"order_preserved_extra_reads_allowed"` |
| `forbidden_tools` | list[string] | Any of these called ⇒ malformed |
| `expected_output_contains` | list[string] (optional) | Substrings the assistant reply must contain |
| `expected_file_state` | object (optional) | Post-run file contents; `{ path: exact_bytes }` |
| `notes` | string | Free-text description |

Pass condition (Fast tier fallback probe): the model's first `tool_calls`
entry matches `expected_tool_sequence[0]`, no forbidden tool appears, and
tool arguments parse as an object. The full-SDK path additionally verifies
`expected_file_state` and `expected_output_contains` after execution
(§0.0c category 1).

### planner (`bench/tasks/planner-fast.json`)

Top-level `output_schema` is a JSON Schema (draft 2020-12) that every task's
completion must validate against. Each item in `tasks[]`:

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable id |
| `prompt` | string | User-message content; must instruct exact JSON shape |
| `min_steps` | int | Minimum steps for the plan to be considered non-trivial |
| `notes` | string | Free-text description |

Pass condition: the completion contains a balanced `{...}` object, that
object validates against `output_schema`, the dependency graph is a DAG
(every dep references a previously-declared id, no duplicates), and the
step count meets `min_steps`.

### embedder (`bench/tasks/embedder-fast.json`)

Top-level `queries[]` is a flat list of texts; the runner sends all of them
in a single `/v1/embeddings` call. Each query:

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable id |
| `text` | string | Input text |
| `role_in_probe` | string | `"identical_pair_member" | "orthogonal_pair_member" | "realistic_snippet"` |
| `pair_id` | string (optional) | Pair identifier for identical/orthogonal probes |

`probes` (top-level) fields:

| Field | Type | Description |
|---|---|---|
| `identical_pair_min_cosine` | float | Cosine between two identical inputs must ≥ this |
| `orthogonal_pair_max_cosine` | float | Cosine between two unrelated inputs must ≤ this |
| `vector_min_norm` | float | Any vector below this L2 norm ⇒ malformed |

Pass condition: `/v1/embeddings` returns non-null vectors for every input,
all norms exceed `vector_min_norm`, the identical pair cosine ≥
`identical_pair_min_cosine`, and the orthogonal pair cosine ≤
`orthogonal_pair_max_cosine`.

## Adding a new task set

1. Draft the file under `bench/tasks/<role>-<tier>.json`.
2. Fill in `schema_version` (start at `1.0.0`) and set `authored_utc` to
   `date -u +%Y-%m-%dT%H:%M:%SZ`.
3. Dry-run the runner against it to confirm the shape passes:
    ```
    python scripts/benchmark-tier-runner.py \
      --tier <tier> --role <role> \
      --task-set bench/tasks/<role>-<tier>.json \
      --rubric bench/rubrics/<tier>-elimination.json \
      --dry-run
    ```
4. Add a BUILD_LOG entry per `kosmos-log-maintenance`.
5. Do NOT edit an already-run task set. Bump `schema_version` in a new
   file if the semantics change.

## Medium-tier embedder task shape (ADR-0016)

Medium-tier embedder task files use a retrieval-scoring shape instead of the
Fast-tier `probes` (identical/orthogonal cosine) shape. Two arms per ADR-0016
hybrid design:

- **Portability arm** (`embedder-medium-beir-scidocs.json`, config only) —
  points to BEIR SciDocs; materialize once via
  `scripts/materialize-beir-scidocs-subset.py` into
  `embedder-medium-beir-scidocs-materialized.json` (inline corpus + queries +
  qrels; deterministic SHA-256 hash-rank subset).
- **Domain arm** (`embedder-medium-domain-openhands-ext.json`) — inline
  corpus + queries + qrels for OpenHands-Ext repo self-retrieval; ~42 chunks
  + 10 queries + hand-labeled 3-level qrels (0/1/2).

Common top-level keys for a materialized/domain Medium-tier embedder task:

| Field | Type | Description |
|---|---|---|
| `arm` | `"portability" \| "domain"` | Which arm this file represents |
| `task_id` | string | Stable ID used in result summaries |
| `corpus` | list[{doc_id, text}] | Documents to embed and search over |
| `queries` | list[{query_id, text}] | Queries to score |
| `qrels` | list[{query_id, doc_id, relevance}] | Ground-truth relevance judgments |
| `metrics.primary` | list[str] | e.g. `["recall@10", "mrr", "ndcg@10"]` |
| `metrics.secondary` | list[str] | e.g. `["recall@1", "recall@5"]` |

Pass condition per query: retrieval was scored without a transport or
malformed-vector error. Numeric metrics are recorded in `ProbeResult.notes`
as a JSON summary object and written to the probe sidecar. Tier-verdict
aggregation is macro-average across queries per arm, then macro-average
across arms per `bench/rubrics/medium-scored.json`.

Dispatch: the runner in `bench/runner/main.py` routes embedder cells to
`probe_embedder_retrieval` (in `bench/runner/probes_retrieval.py`) whenever
the task file has both `corpus` and `qrels` top-level keys; otherwise it
falls back to the Fast-tier `probe_embedder`. The Fast-tier probe file is
untouched — post-hoc-edit-locked per §0.0a bullet 3.
