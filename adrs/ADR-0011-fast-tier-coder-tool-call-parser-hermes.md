# ADR-0011 — Fast-tier coder `--tool-call-parser` = `hermes` (Qwen3-Thinking-2507)

**Status:** Ratified
**Lock-in phase:** Phase 0.1 · Fast tier
**Supersedes:** — (amends ADR-0010's `ROLE_FLAGS["coder"]` value only; the mechanism from ADR-0010 stands)

## Context

ADR-0010 introduced `VLLMServer.ROLE_FLAGS` and, for the `coder` role, prepended
`--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3`.
That fixed the HTTP 400-at-validation failure: after commit `912c964` the coder
smoke re-run reached the model, produced correct tool calls, and returned
`HTTP 200` for all 5 tasks (server log `1786432207.log`, 2026-08-11 03:10 EDT).

However every task still recorded `fail — no tool_calls (finish='stop')`. The
sidecar's `raw_content` dump showed the model emitting well-formed calls as
literal text inside `message.content`, e.g.:

```
<tool_call>
{"name": "read_file", "arguments": {"path": "/workspace/probe/greeting.txt"}}
</tool_call>
```

with `message.tool_calls == []`. vLLM 0.27's `qwen3_coder` tool-call parser
(implemented as the Rust-backed `Qwen3EngineToolParser` wrapping
`Qwen3ParserToolAdapter`) targets the Qwen3-**Coder** XML wire format
(`<function=name><parameter=…>…</parameter></function>`). It does not match
Hermes-style `<tool_call>{json}</tool_call>` blocks and therefore leaves
`tool_calls` empty.

The Qwen3-Thinking-2507 chat template (used by the AWQ build on disk) emits
Hermes-style tool-call blocks. vLLM 0.27 ships a `hermes` parser
(`hermes_tool_parser.Hermes2ProToolParser`) whose regex is exactly
`<tool_call>(.*?)</tool_call>|<tool_call>(.*)` — a direct match for what the
model produces.

Inspection of the installed vLLM 0.27 tool-parser registry
(`vllm.tool_parsers.ToolParserManager.list_registered()`) confirms `hermes`,
`qwen3_coder`, and `qwen3_xml` are all valid `--tool-call-parser` values.

## Decision

`VLLMServer.ROLE_FLAGS["coder"]` uses `--tool-call-parser hermes` (not
`qwen3_coder`). Full coder role flags:

```
--enable-auto-tool-choice
--tool-call-parser  hermes
--reasoning-parser  qwen3
```

`--reasoning-parser qwen3` is retained: it strips `<think>...</think>` blocks
server-side so `content` no longer carries reasoning noise, and it is required
by vLLM 0.27's tool-choice acceptance path for Qwen3 thinking models.

`planner` and `embedder` role flags are unchanged from ADR-0010.

## Rationale

Alternatives considered:

- **`qwen3_coder`** — rejected; targets Qwen3-Coder's XML `<function=…>` format,
  not Hermes blocks. Confirmed empirically: `qwen3_coder` produced `HTTP 200`
  with `tool_calls: []` and the raw call left embedded in `content`.
- **`qwen3_xml`** — rejected; also XML-based (`<function>`/`<parameter>`),
  designed for Qwen3-Coder / Qwen3-Instruct variants. Would produce the same
  empty-`tool_calls` result on Hermes-style output.
- **Post-hoc parse in `probes.py` fallback** — rejected; hides a launcher
  configuration bug in the probe, duplicates a parser vLLM already ships, and
  splits tool-call parsing across two layers.
- **Ollama route for coder cell** — rejected; the runtime-family selection is
  fixed by the candidate file. Fixing the vLLM launch flags is the correct fix.

## Consequences

- `bench/runner/server.py::VLLMServer.ROLE_FLAGS["coder"][2]` changes from
  `qwen3_coder` to `hermes`. Docstring updated to explain the parser choice.
- ADR-0010 status flips to `Amended · see ADR-0011`; its role-flags table row
  for `coder` is amended and cross-links here.
- No change to task-set files, rubric, `probes.py`, or `main.py`.
- `PORTING_LEDGER.md` unchanged (no vendored component involved).
- Future models that emit XML-format calls (Qwen3-Coder or Qwen3-Instruct
  variants) will need a per-model override of `ROLE_FLAGS["coder"]` — deferred
  to when we actually onboard such a model into the coder pool. The current
  design allows `extra_flags` to override, so this can be handled at the
  candidate-file layer without another ADR.

## Lock-in phase

Phase 0.1 · Fast tier. Freezes the coder launch-flag value used by every
fast-tier vLLM smoke that runs against a Hermes-format Qwen3 model.

## References

- ADR-0010 — Fast-tier vLLM per-role launch flags (mechanism)
- vLLM 0.27 tool parsers:
  - `vllm/tool_parsers/hermes_tool_parser.py::Hermes2ProToolParser`
    (regex: `<tool_call>(.*?)</tool_call>|<tool_call>(.*)`)
  - `vllm/tool_parsers/qwen3_engine_tool_parser.py::Qwen3EngineToolParser`
    (Rust-backed XML parser, not Hermes-compatible)
- Sidecar evidence: `bench/results/smoke-fast-coder-qwen3-30b-a3b-thinking-2507-awq-vllm-gpu-20260811T071005Z.probe.json`
  — 5 tasks, `finish='stop'`, `tool_calls=[]`, raw `<tool_call>{json}</tool_call>` in `content`.
- Server log: `bench/results/server-logs/coder_qwen3-30b-a3b-thinking-2507-awq_vllm_gpu-1786432207.log`
