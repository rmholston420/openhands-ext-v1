# ADR-0011 — Fast-tier coder `--tool-call-parser` = `hermes` (Qwen3-Thinking-2507)

**Status:** Amended (2026-08-11 04:07 EDT, 2026-08-11 04:26 EDT) — hermes is the **default** tool-call parser; per-cell override supported; **reasoning-parser is now per-cell with no role default**.
**Lock-in phase:** Phase 0.1 · Fast tier
**Supersedes:** — (amends ADR-0010's `ROLE_FLAGS["coder"]` value only; the mechanism from ADR-0010 stands)

> **STATUS AMENDMENT 2 (2026-08-11 04:26 EDT):** `--reasoning-parser` is now **per-cell**, not a role default. `VLLMServer.ROLE_FLAGS["coder"]` and `ROLE_FLAGS["planner"]` no longer include `--reasoning-parser qwen3`. Candidates whose model card declares thinking-mode output (Qwen3-Thinking-2507 family) MUST set `reasoning_parser="qwen3"` in their registry / pool row. Non-thinking coders (Qwen3-Coder-Instruct family) MUST leave the field unset.
>
> **Root cause driving the amendment:** the qwen3 reasoning parser captures assistant output into the OpenAI `reasoning` field before the tool-call parser inspects `content`. On thinking models this is desired (strips `<think>` blocks). On non-thinking coders (Qwen3-Coder-Instruct) it captures the model's `<function=name><parameter=arg>value</parameter></function>` XML block into `reasoning`, leaving `content=null` and `tool_calls=[]`. Observed 2026-08-11 04:18 EDT on Cell 2 (qwen3-coder-30b-a3b-instruct-awq-4bit) tasks 01/04 of coder-fast POOL: reasoning field contained a stray `</tool_call>` closer with no matching opener; tasks 03/05 passed only because the model emitted separator prose that consumed the reasoning-parser slot before the XML.
>
> **Ratified additions:**
>
> - `bench/candidates/registry.json` entries and pool rows MAY include `"reasoning_parser"`. When present, it is passed as `--reasoning-parser <value>`. When absent, NO reasoning-parser flag is emitted.
> - `ExpandedCandidate` gained `reasoning_parser: Optional[str] = None`, propagated through `expand_for_role()` (both GPU and CPU-embedder construction sites) and `_from_candidate_dict()`.
> - `_make_server()` for vLLM cells appends `["--reasoning-parser", cand.reasoning_parser]` to `extra_flags` only when set.
> - `VLLMServer.ROLE_FLAGS` (server.py): coder = `[--enable-auto-tool-choice, --tool-call-parser, hermes]`; planner = `[]`; embedder = `[]`. Reasoning parser is no longer a role default.
>
> **Registry-authoring rule (extends the tool-call-parser rule):**
>
> | Model family | Thinking mode | reasoning_parser |
> |---|---|---|
> | Qwen3-Thinking-2507 (`Qwen3-…-Thinking-…`) | Yes (`<think>…</think>` emitted) | `"qwen3"` |
> | Qwen3-Coder-Instruct (`Qwen3-Coder-…-Instruct-…`) | No | UNSET (`None`) |
> | Qwen3 base Instruct (non-coder, non-thinking) | No | UNSET (`None`) |
>
> Wrong setting → tool-call XML routed into `reasoning`, `tool_calls: []`, R2/R3 fail with `no tool_calls (finish='stop')`.
>
> **First locked-in overrides:**
> - `qwen3-30b-a3b-thinking-2507-awq`: `reasoning_parser="qwen3"` (both `roles.coder` and `roles.planner` entries in registry, and coder-fast-pool row).
> - `qwen3-coder-30b-a3b-instruct-awq-4bit`: `reasoning_parser` INTENTIONALLY unset.
>
> **Consequences of amendment 2:**
> - `bench/runner/candidates.py`: `ExpandedCandidate.reasoning_parser` added; both `ExpandedCandidate()` construction sites in `expand_for_role` updated.
> - `bench/runner/main.py::_from_candidate_dict`: reads `row.get("reasoning_parser")`.
> - `bench/runner/main.py::_make_server`: appends `--reasoning-parser` via `extra_flags` when set.
> - `bench/runner/server.py::VLLMServer.ROLE_FLAGS`: `--reasoning-parser qwen3` removed from `coder` and `planner` role defaults.
> - `bench/candidates/registry.json`: `reasoning_parser="qwen3"` added to thinker under both `roles.coder` and `roles.planner`.
> - `bench/candidates/coder-fast-pool.json`: `reasoning_parser="qwen3"` added to thinker row; coder-instruct row unchanged (field absent).
> - `PORTING_LEDGER.md`: no changes (no OSS component added).
> - Amendment references BUILD_LOG entry at 2026-08-11 04:26 EDT.

> **STATUS AMENDMENT (2026-08-11 04:07 EDT):** Parser is now **per-cell**, not global. The class-level default in `VLLMServer.ROLE_FLAGS["coder"]` remains `hermes` (correct for Qwen3-Thinking-2507 and any other model whose chat template emits `<tool_call>{json}</tool_call>` blocks). Candidates whose chat template emits a different wire format MUST declare `tool_call_parser` in their registry entry; the runner appends `--tool-call-parser <value>` after `ROLE_FLAGS` so vLLM argparse honors last-value-wins.
>
> **Ratified additions:**
>
> - `bench/candidates/registry.json` entries MAY include an optional `"tool_call_parser"` field. When present, it overrides the role default for that candidate; when absent, the role default applies.
> - `bench/candidates/*.json` pool files MAY include `"tool_call_parser"` per row with the same semantics.
> - `ExpandedCandidate` gained a `tool_call_parser: Optional[str] = None` field, propagated by `expand_for_role()` (registry path) and `_from_candidate_dict()` (candidate-file path).
> - `_make_server()` builds `extra_flags=["--tool-call-parser", cand.tool_call_parser]` when the field is set for coder cells and passes it to `VLLMServer(extra_flags=...)`. Role flags come first, override comes after — last-value-wins.
>
> **Registry-authoring rule (locks in with ADR-0013's architectures rule):** before adding any vLLM coder candidate to the registry, verify its `chat_template.jinja` (or `tokenizer_config.json.chat_template`) tool-call marker signature:
>
> | Wire format | Marker signature | Required parser |
> |---|---|---|
> | Hermes | `<tool_call>{json}</tool_call>`; no `<function=` | `hermes` |
> | Qwen3-Coder XML | outer `<tool_call>` wrapping inner `<function=name><parameter=arg>value</parameter></function>` | `qwen3_coder` |
> | Qwen3 XML (Instruct family, non-coder) | `<function>...</function>` without `<tool_call>` wrapper | `qwen3_xml` |
> | Qwen3 native | `<|tool_call|>` sentinel token | `qwen3` |
>
> Wrong parser → `tool_calls: []` with the raw call left in `message.content` → R2/R3 fail with `no tool_calls (finish='stop')` even though the model emitted a well-formed call.
>
> **First locked-in override:** `qwen3-coder-30b-a3b-instruct-awq-4bit` uses `tool_call_parser="qwen3_coder"`. Verified 2026-08-11 04:06 EDT via chat template inspection (3× `<tool_call>`, 3× `<function=`, 2× `arguments`, 0× `name=`).
>
> **Consequences of amendment:**
> - `bench/runner/candidates.py`: `ExpandedCandidate` gains optional `tool_call_parser` field.
> - `bench/runner/main.py::_from_candidate_dict`: reads `row.get("tool_call_parser")`.
> - `bench/runner/main.py::_make_server`: passes per-cell `--tool-call-parser` via `extra_flags` for coder role only.
> - `bench/runner/server.py`: **no change**. `VLLMServer` already accepted `extra_flags`; role-default hermes still applies to any candidate that omits the field.
> - `PORTING_LEDGER.md`: no changes (no OSS component added).
> - Amendment references BUILD_LOG entry at 2026-08-11 04:07 EDT for the plumbing patch.

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
