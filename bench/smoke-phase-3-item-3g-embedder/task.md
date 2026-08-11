# Phase 3 · Item 3.g (embedder half) — Embedding round-trip smoke against llama.cpp :8090

## Goal

Prove that the production **embedder endpoint** (`http://127.0.0.1:8090/v1`,
`qwen3-embedding-4b-q8-gguf` on llama.cpp with `--embedding --pooling last`)
returns valid embedding vectors via the OpenAI-compatible `/v1/embeddings`
route.

Rationale: item 3.g asks that "tool-calling is functional against every
configured `base_url`". The **embedder** endpoint is not a chat/tool-calling
endpoint — llama.cpp with `--embedding` disables the chat completion route.
The correct capability check for the embedder is the **embeddings round-trip**
itself: does the endpoint return well-formed embedding vectors?

## Method (verified honesty)

- Direct HTTP `POST http://127.0.0.1:8090/v1/embeddings` — no SDK, no litellm.
  Matches the Row-2 pattern of isolating the endpoint capability from the SDK
  serialization / provider-routing layers.
- Two distinct inputs plus a repeat of one to exercise both determinism and
  discrimination.

## Pass criteria

- HTTP 200.
- Response JSON has `data: [ ... ]` with one item per input.
- Each item's `embedding` is a list of `float` of nonzero length, identical
  length across inputs.
- The vector's L2 norm is > 0 (nonzero embedding).
- Different inputs produce **different** vectors (cosine similarity < 0.999).
- Identical inputs produce **identical** vectors (cosine similarity == 1.0 to
  within float32 epsilon).
- Wall time under 30 s for the whole batch.

## Fail criteria

- HTTP non-200, or response missing `data`.
- Any zero-norm vector.
- Two different inputs produce identical vectors (endpoint returning a
  constant / stub).
- Two identical inputs produce visibly different vectors (nondeterministic
  embedder, would break RAG).

## Prereqs

- Embedder up on :8090 (`scripts/serve-embedder.sh`, per ADR-0017 Option 2
  co-resident with planner).

## Non-goals

- Not verifying embedding quality vs. any gold standard.
- Not verifying MTEB scores or downstream RAG behavior.
- Not touching the SDK — no `LLM(...)` object involved.
