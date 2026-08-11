# Forge-OH + OH-GUI → Stock OpenHands/Agent Canvas — Execution Plan (v16, Standalone, Perplexity Computer-Ready)

## What Changed and Why (v14 + v15 → v16)

v16 reconciles v14 (the full consolidation of the eight-version model-selection and integration lineage: v5–v13) with v15 (the serving-runtime version-pin extension covering llama.cpp and vLLM). v14's contribution is authoritative on *what* gets integrated and *how* the three-tier benchmark campaign, workspace policy, suite configuration, and nine downstream phases work. v15's contribution is authoritative on *version currency*: neither OpenHands nor its serving runtimes (llama.cpp, vLLM) may be pinned from a cached number in any prior document — every version must be re-verified live at build/install time. v16 merges these without loss: it keeps v14's full phase structure (0 through 11) verbatim where unchanged, inserts v15's Phase -1 version-baseline work as a hard prerequisite gate before Phase 0, and folds v15's runtime-version discipline into every Phase 0 tier and launch command. v16 is written as a standalone document — no prior version needs to be read to execute this plan — and is scoped for direct, autonomous execution by Perplexity Computer, with explicit skills, custom instructions, and copy-paste prompts included at the end.

**Target platform:** single-user local workstation "Colossus" — 128GB RAM, RTX 5090 (32GB VRAM, Blackwell SM_120), no cloud control planes, no multi-user assumptions, no GitHub-native CI beyond what already exists in the source repos.[^1]

**Source repositories audited:** `rmholston420/OH-GUI` and `rmholston420/Forge-OH`. **Integration target:** `OpenHands/agent-canvas` (MIT-licensed, standalone) running against `openhands-agent-server`.[^2][^1]

**Definition of done:** stock, unforked Agent Canvas UI running exclusively on `DockerWorkspace`, tuned for maximum coding/debugging accuracy via an empirically-derived (not assumed) model topology on versions verified current at execution time, configured to use Canvas's built-in security/skills/MCP/delegation/tools systems, with Forge-OH/OH-GUI's genuinely unique backend capabilities (GPU telemetry, episodic memory, model routing, RepoGraph) reachable through Canvas's native extension surfaces. No custom frontend code from either source repo ships in the final system; the one new frontend surface (a RepoGraph panel) is purpose-built against Canvas's plugin API.[^1]

***

## Phase -1 — Version Baseline and Pin (Mandatory Gate, Runs First)

**Purpose:** confirm every component this plan touches — the OpenHands ecosystem *and* the serving runtimes Phase 0 launches — is targeted at its actual current version, re-verified live, not carried forward from any planning document including this one.[^2]

### -1.1 Verified OpenHands-ecosystem versions (as of the most recent audit, August 2026)

| Component | Repository/package | Last-verified version | Notes |
|---|---|---|---|
| OpenHands app/CLI | `OpenHands/OpenHands` | v1.7.0 (stable line); CLI binary tracks v1.16.0 separately | App and CLI/binary version independently[^2] |
| Software Agent SDK monorepo | `OpenHands/software-agent-sdk` | v1.41.0 (~Aug 6, 2026) | Canonical source of truth; PyPI lags this[^2] |
| `openhands-sdk`/`openhands-tools`/`openhands-agent-server` (PyPI) | PyPI | 1.19.1 / 1.11.1–1.12.0 / 1.5.1 | Confirm with `pip show` at install time, not from a listing[^2] |
| Agent-server Docker image | `ghcr.io/openhands/agent-server` | `latest-python` tracks `main`; pinned examples reference `1.26.0-python`/`1.35.0`/`1.36.1` | Prefer `latest-python` or pin to the exact SDK tag in use[^2] |
| Agent Canvas | `OpenHands/agent-canvas` | v1.5.0 (2026-07-17) | Bumps software-agent-sdk to 1.36.1 internally[^2] |

**These numbers are illustrative of the last audit, not authoritative for execution.** Perplexity Computer must re-fetch each of these at execution time before pinning anything (see -1.4).

### -1.2 Verified serving-runtime versions

| Component | Repository | Last-verified version | Notes |
|---|---|---|---|
| llama.cpp | `ggml-org/llama.cpp` | Rolling build-tag stream (`b####`); no semantic versioning, multiple tags per day | There is no "latest stable" — the top-of-releases tag at build time is current; never trust a cached tag[^2] |
| vLLM | `vllm-project/vllm` | Conflicting mirror snapshots observed (v0.15.0 / v0.17.1 / v0.24.0) | vLLM also ships separately-numbered monthly NVIDIA container builds (e.g., "vLLM Release 26.07") — do not conflate the two schemes[^2] |

**Reconciliation rule for vLLM's version discrepancy:** conflicting "latest" tags across sources reflect scrape-time snapshot lag on a fast-moving project, not a data error. Re-fetch `https://github.com/vllm-project/vllm/releases` immediately before pinning, take the top-listed non-prerelease tag, and log the exact tag plus fetch timestamp in Category 7 run metadata (§0.0c). Never carry forward a version number quoted in any planning document, including this one.[^2]

### -1.3 SDK-to-runtime compatibility: confirmed vs. inferred

**Confirmed:**
- The OpenHands SDK's LLM client is a generic OpenAI-compatible HTTP client (`openai/` model prefix routes against an arbitrary `base_url`); it depends only on the OpenAI-compatible REST surface (`/v1/chat/completions`, `/v1/embeddings`), not on any runtime-internal API.[^2]
- vLLM documents Blackwell (SM100-family) as a first-class target, with FlashInfer MLA as the default MLA backend and TRTLLM as default prefill on Blackwell — directly relevant to the RTX 5090 (SM_120).[^2]
- llama.cpp's CUDA build path ships CUDA 12/13 variants, and recent commits address SM_90/SM_120 dispatch correctness, indicating active Blackwell-generation support.[^2]

**Inference, not fact — must be locally verified, not assumed:**
- No source states an explicit min/max llama.cpp or vLLM version required by the current SDK/agent-server. Compatibility risk sits almost entirely on each runtime's own API stability, not an SDK-side version gate.[^2]
- Whether the plan's specific candidate models (Qwen3.6-27B/35B-A3B variants, Qwen3-Embedding models) load correctly under the very latest build/release has not been verified in any research pass — this must be smoke-tested (§-1.5) before Phase 0.1.[^2]

### -1.4 Version pin procedure (execute at run time, not from this table)

```bash
# --- OpenHands ecosystem ---
curl -s https://api.github.com/repos/OpenHands/software-agent-sdk/releases/latest | grep tag_name
pip install "openhands-sdk==<verified-current-tag>" \
            "openhands-tools==<verified-current-tag>" \
            "openhands-workspace==<verified-current-tag>" \
            "openhands-agent-server==<verified-current-tag>"
pip show openhands-sdk openhands-tools openhands-workspace openhands-agent-server
docker pull ghcr.io/openhands/agent-server:latest-python
npm install -g @openhands/agent-canvas@latest
npm ls -g @openhands/agent-canvas

# --- llama.cpp: build from the current top-of-releases tag ---
curl -s https://api.github.com/repos/ggml-org/llama.cpp/releases/latest | grep tag_name
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
git checkout urrent-top-tag-verified-at-build-time>
cmake -B build -DBUILD_SHARED_LIBS=OFF -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=120
cmake --build build --config Release -j --clean-first --target llama-server llama-cli
cp build/bin/llama-* .
cd ..

# --- vLLM: install from the current top-of-releases tag ---
curl -s https://api.github.com/repos/vllm-project/vllm/releases/latest | grep tag_name
pip install "vllm==urrent-top-tag-verified-at-build-time>"
python -c "import vllm; print(vllm.__version__)"
```

Set `-DCMAKE_CUDA_ARCHITECTURES=120` explicitly for the RTX 5090's Blackwell SM_120 target — do not rely on the generic `-DGGML_CUDA=ON` default, since llama.cpp's commit history shows ongoing SM-family dispatch fixes that could silently mis-target an unpinned build.[^2]

### -1.5 SDK-to-runtime smoke test (precedes Phase 0.1)

1. Launch a trivial small model (1–3B GGUF) under the pinned llama.cpp build; confirm `curl http://127.0.0.1:<port>/v1/models` and one `/v1/chat/completions` tool-call round-trip succeed against the pinned `openhands-sdk`.
2. Repeat with an equivalently small model under the pinned vLLM release.
3. If either fails, treat it as a runtime/SDK integration issue independent of model choice — resolve here, before it contaminates Phase 0.1's elimination results with a false "candidate crashed" finding.[^2]

### Phase -1 Verification

| Check | Method | Pass condition |
|---|---|---|
| SDK version pin matches live GitHub release | `pip show openhands-sdk openhands-tools openhands-workspace openhands-agent-server` | Installed versions match tag confirmed live |
| llama.cpp version re-verified at build time | `curl -s .../ggml-org/llama.cpp/releases/latest` immediately before build | Recorded tag matches actual top-of-releases at build time |
| vLLM version re-verified, discrepancy reconciled | `curl -s .../vllm-project/vllm/releases/latest` immediately before install | Installed version matches top-listed non-prerelease tag, fetch timestamp logged |
| Blackwell/SM_120 target set explicitly | Inspect CMake invocation | `-DCMAKE_CUDA_ARCHITECTURES=120` present |
| SDK-to-runtime smoke test passes both runtimes | Run §-1.5 | Tool-call round-trip succeeds with trivial model on both |
| Version-pin metadata logged into Category 7 | Inspect first Phase 0.1 JSON record | llama.cpp build tag and vLLM release tag present, not only in a separate doc |

***

## Phase 0 — Capability Uplift: Three-Tier Benchmark Campaign

### 0.0 Governing discipline

Before any run, for every tier and role, state: (1) the tier's time budget and the minimum detectable effect (MDE) it supports at 80% power given task-set size; (2) that the tier is a screening step — except the Full tier, which alone may declare a production winner; (3) a go/no-go attainability check — if the budget can't separate the candidate pool, narrow it by engineering judgment first, not by spending the time anyway. No tier result may be promoted to a production config value under time pressure. If the Full tier can't complete before a deadline, ship the last-known-good prior configuration as interim and mark the Full tier pending.[^1]

The candidate pool for every role starts **open** at the Fast tier — never pre-narrow using any prior document's conclusions.[^1]

### 0.0a Statistical-power lessons (binding, guard against actively, not just cite)

- **Denominator exclusion bug:** malformed/missing tool-call events must never be dropped from rate-metric denominators — this previously silently inflated one candidate's apparent ranking.[^1]
- **Latency-estimation error:** a prior unmeasured "24.2s/call" guess was later measured at 0.32–1.30s/call — a 40x error. Every latency figure here must trace to a direct per-call measurement.[^1]
- **Post-hoc rubric editing:** rubrics must be timestamped before the first scored output; no edits after scoring begins.[^1]

### 0.0b Candidate pool per role

| Role | Candidates | Known constraints |
|---|---|---|
| Coder | Qwen3.6-27B (dense, llama.cpp Q6_K or vLLM), Qwen3.6-27B INT4 AutoRound (vLLM), Qwen3.6-35B-A3B (MoE, llama.cpp Q4_K_XL or vLLM AWQ) | Only one full-quant GPU-resident reasoning model fits the 32GB VRAM budget at a time[^1][^2] |
| Planner | Qwen3.6-35B-A3B, Qwen3.6-27B, `qwen3-thinking-2507-awq` | `-np > 1` and `--mmproj` are mutually exclusive under llama.cpp MTP mode[^1] |
| Embedder | `qwen3-embedding:0.6b`, `qwen3-embedding:4b`, each × {CPU, GPU} × {llama.cpp, vLLM} | vLLM CPU backend requires AVX-512 for the standard prebuilt image; quantized CPU serving (AWQ/GPTQ/INT8) is x86-only; vLLM requires `--task embed` explicitly or it silently attempts generation instead of failing cleanly[^1][^2] |

**v16 addition:** re-confirm every constraint above holds under the Phase -1-pinned runtime versions specifically — both projects' flag surfaces and requirements change release to release.[^2]

### 0.0c Mandatory uniform instrumentation schema (all tiers, all roles)

Every run emits one structured JSON record covering seven categories:[^1]

1. **Tool-call behavior** (coder/planner): attempt count, success rate, malformed-call rate, missing-tool-call rate, wrong-tool-selected rate, argument-error rate, loop/repetition count, retry count.
2. **Task outcome** (coder/planner): verdict via deterministic ordered reduction (timeout > verify-verdict > trajectory-status > transport-status); context-budget-skip flag; truncation flag; rubric score (planner, fixed pre-scoring).
3. **GPU resource envelope** (all GPU-resident cells): VRAM peak/avg and % of ~32,607 MiB usable; GPU temp peak/avg (re-verify fresh per candidate against an 83°C throttle ceiling); power draw; utilization %; NVML coverage %; throttle events; CUDA OOM events (nonzero disqualifies).
4. **CPU resource envelope** (CPU-resident embedder cells): isolated process CPU %, system RAM peak, one-time AVX-512 confirmation.
5. **Latency** (all roles/tiers): per-call warm latency (measured, never estimated), cold-start latency, per-task wall time, variance across 3+ repeats.
6. **Cross-candidate contention** (Phase 0.3 only): coder/planner latency/error-rate delta with vs. without concurrent GPU-resident embedder load; swap/reload cost.
7. **Run metadata** (every run): tier, candidate identity (model/quant/format/runtime/device), task-set identity/version, timestamp/duration, harness commit SHA, **plus the exact llama.cpp build tag and vLLM release tag used for that run** (v15/v16 addition).[^2]

Reuse the existing NVML sampler for Categories 3–4; capture Category 1 from the SDK's `ActionEvent`/`ObservationEvent` stream, not by re-parsing free text.[^1]

```python
from openhands.sdk.security import LLMSecurityAnalyzer, ConfirmRisky
agent.security_analyzer = LLMSecurityAnalyzer()
agent.confirmation_policy = ConfirmRisky(threshold="HIGH", confirm_unknown=True)
```

### 0.1 FAST tier (~30 minutes): triage and infeasibility elimination

Launch commands reference the Phase -1 pin explicitly:

```bash
# llama.cpp — pinned build, Blackwell target set at compile time
./llama.cpp/llama-server -m models/andidate>/<quant>.gguf \
  --host 127.0.0.1 --port 8082 -ngl 999 -c 32768 -fa on \
  --cache-type-k q8_0 --cache-type-v q8_0 --jinja --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0

# vLLM — pinned release
vllm serve andidate> --port 8501 --max-model-len 32768

# Embedder — CPU, llama.cpp
./llama.cpp/llama-server -m models/<embed-candidate>/embedding-Q8_0.gguf \
  --host 127.0.0.1 --port 8083 --embedding -ngl 0 -c 4096

# Embedder — CPU, vLLM (verify AVX-512 first)
vllm serve <embed-candidate> --task embed --device cpu --host 127.0.0.1 --port 8090 --max-model-len 4096

# Embedder — GPU, llama.cpp
./llama.cpp/llama-server -m models/<embed-candidate>/embedding-Q8_0.gguf \
  --host 127.0.0.1 --port 8085 --embedding -ngl 999 -c 4096

# Embedder — GPU, vLLM
vllm serve <embed-candidate> --task embed --host 127.0.0.1 --port 8092 --max-model-len 4096
```

| Role | Task count | What's tested |
|---|---|---|
| Coder | 3–5 tasks/candidate | Launches on both runtimes; rough tool-call validity; gross latency |
| Planner | 2–3 tasks/candidate | Completes without truncating at conservative token budget (4096); rough plan coherence |
| Embedder | 1 fixed query set (5–10 queries)/matrix cell | Cell launches at all; rough latency; non-degenerate vectors |

**Elimination criteria** (deliberately conservative): crash/fail-to-launch/malformed output on >1 task → eliminated. Embedder cell fails to launch → eliminated for that device/runtime combo only. Latency >~5x fastest with no offsetting quality signal → flagged, confirmed (not dropped) in Medium tier.[^1]

**v16 addition:** if a candidate fails to launch specifically under the newly-pinned runtime version where it previously worked under an older cached version, log this as a **runtime-version regression**, distinct from a genuine model-candidate failure — the former is an infrastructure fix, not evidence against the model.[^2]

#### Phase 0.1 Verification

| Check | Method | Pass condition |
|---|---|---|
| Total wall time | Time the run | ≤30 minutes across all three roles |
| Every elimination documented | Review pruning log | Concrete failure reason per drop |
| No final ranking claimed | Review write-up | States tier only prunes |
| Runtime-version regressions distinguished from model failures | Review elimination log | Launch failures from flag/behavior changes labeled separately |
| Launch syntax verified against pinned versions | Diff commands vs. current `--help` | No deprecated/renamed flags used silently |
| Full schema present at reduced scale | Inspect JSON records | All 7 categories present or marked insufficient |

### 0.2 MEDIUM tier (~60 minutes): comparative screening

| Role | Task count | What's tested |
|---|---|---|
| Coder | 15–20 tasks/candidate × runtime | Pass/fail against fixed rubric; malformed-call rate in denominator |
| Planner | 8–12 tasks/candidate × runtime | Structured-plan completeness; truncation rate at 2–3 token budgets |
| Embedder | Full surviving matrix cells | Retrieval quality against real corpus (Forge-OH's `episodic_memory.py` trajectory records, not generic MTEB alone); latency; single-repeat GPU contention check |

**Attainability gate:** compute whether the task count can reach ~5 discordant pairs between the top-2 candidates per role before running; if unattainable, report "statistically indistinguishable at this sample size" as a valid finding, or trim elsewhere within budget.[^1]

**Cross-runtime output equivalence check (embedder):** confirm llama.cpp and vLLM produce numerically comparable embedding vectors for the same model/input before comparing quality across runtimes — tokenization/normalization/quantization differences must not be mistaken for model-quality differences.[^1]

#### Phase 0.2 Verification

| Check | Method | Pass condition |
|---|---|---|
| Total wall time | Time the run | ≤60 minutes combined |
| Attainability gate computed pre-run | Review design doc | Discordant-pair math documented first |
| Rubrics fixed before scoring | Timestamp check | No post-hoc edits |
| Ranking claims labeled with confidence | Review write-up | "Ranked with signal" vs. "indistinguishable" per pair |
| Cross-runtime equivalence checked | Compare vectors, same model+input | Documented before trusting comparisons |
| Shortlist size | Count survivors/role | 2–3 per role carried to Full tier |

### 0.3 FULL tier (<10 hours): properly-powered final ranking and combination test

| Segment | Budget | Scope |
|---|---|---|
| Coder final ranking | ~3–4 hrs | SWE-bench-Verified subset (or full 500) for 2–3 shortlisted × runtimes |
| Planner final ranking | ~2–3 hrs | Larger task set at Medium tier's minimum-viable token budget, 3+ repeats |
| Embedder final ranking | ~1–2 hrs | Full surviving matrix cells, real corpus, 3+ repeats, full GPU-contention measurement |
| Combination-level test | ~1–2 hrs | Cross-product of the three shortlists × embedder options under a realistic mixed workload (plan → code → recall), not summed isolated scores |

**This tier alone carries authority to declare a final winner.** The combination winner may not be each role's individual top scorer if co-residency behavior favors a different mix — state this reasoning explicitly.[^1]

#### Phase 0.3 Verification

| Check | Method | Pass condition |
|---|---|---|
| Total wall time | Time the run | <10 hours across all segments |
| MDE stated and met per segment | Review design docs | Sample size justified against stated MDE |
| Variance reported | 3+ repeats | Documented, not assumed negligible |
| Combination test uses shortlists | Review design | 2–3 candidates/role in cross-product |
| Final decision justified | Review write-up | States why the combination was picked, including any non-top-scorer choice |
| Resource envelope captured throughout | Continuous NVML sampling | VRAM/temp/power/util logged for the full run |

### 0.4 Tier escalation rule

If the Fast tier produces an unambiguous, large-margin winner for a role (every competitor crashes or is catastrophically slower with no plausible reversal at higher sample size), that role may skip directly to a reduced-scope Full-tier confirmation rather than a Medium-tier slot — document as a deliberate, reasoned skip, never a silent shortcut.[^1]

### 0.5 Post-decision configuration lock

Applied only to whichever model wins each role in the Full tier:

```bash
# If context-cliff symptoms appear past ~30k tokens on the winning coder model,
# keep K-cache at higher precision than V-cache
--cache-type-k f16 --cache-type-v q8_0
```

```toml
[llm.condenser]
model = "openai/der-role-winner>"
base_url = "http://127.0.0.1:der-winner-port>/v1"
api_key = "none"
temperature = 0.1
max_input_tokens = 1024
# max_size = 120, keep_first = 4
```

Multi-attempt rollouts with a critic/reranker produce a log-linear accuracy gain (60.6% → 66.4% on SWE-bench Verified, one to five attempts) — if two candidates score closely, the non-winning model is a natural critic/reranker candidate rather than being dropped.[^1]

### 0.6 Security analyzer and confirmation policy

```python
from openhands.sdk.security import LLMSecurityAnalyzer, ConfirmRisky
agent.security_analyzer = LLMSecurityAnalyzer()
agent.confirmation_policy = ConfirmRisky(threshold="HIGH", confirm_unknown=True)
```

Both must be set together — one alone has no gating effect. Hard-fail on analyzer-attach errors rather than warn-logging.[^1]

***

## Phase 1 — Fixed Workspace Policy: DockerWorkspace Only

```python
from openhands.workspace import DockerWorkspace

with DockerWorkspace(server_image="ghcr.io/openhands/agent-server:latest-python") as workspace:
    conversation = Conversation(agent=agent, workspace=workspace)
```

No `LocalWorkspace` fallback anywhere in configuration, scripts, or documentation — enforced by a grep check in CI or a pre-commit hook, not documentation alone. Mount only the specific repo directory being worked on; read-only wherever the task doesn't require writes.[^1]

If llama.cpp or vLLM run inside the same container boundary as the agent-server sandbox (rather than as host-level services, this plan's default topology), their pinned versions must be baked into the custom base image per OpenHands's `BASE_IMAGE` build-arg pattern — verify this only applies if the topology changes.[^2]

- **1.1** Security analyzer (§0.6) and loop-guard (Phase 9) run as agent-server-side hooks outside the container — not disable-able by anything inside the sandbox they police.[^1]
- **1.2** Register `code-explorer` (built into `openhands-tools`, read-only) for investigation tasks.[^1] **DEFERRED to §2.4 / Phase 3 per ADR-0032** — registration lands with the runtime tool registry alongside the router table, once the runtime config surface is scaffolded.

### Phase 1 Verification

| Check | Method | Pass condition |
|---|---|---|
| No LocalWorkspace path | `grep -rn "LocalWorkspace" ~/dev/agent-canvas-stock ~/Forge-OH` | Zero references outside test/example code |
| Isolation boundary | Attempt to reach a host file outside the mounted directory | Fails |
| code-explorer delegation | Delegate a read-only investigation task | Completes with no write/execute calls |

***

## Phase 2 — Suite-Wide Configuration

### 2.1 Deployment mode selection

| Mode | Command | Constraint |
|---|---|---|
| TUI | `openhands` | Interactive only |
| Headless | `openhands --headless -t "..."` | Always `always-approve`; `--llm-approve` unavailable |
| Serve (Canvas) | `openhands serve --gpu` | Full visual workspace, Docker required |

Reserve headless/CI automation for low-risk, well-scoped tasks only.[^1]

### 2.2 MCP servers via proxy, not direct stdio

```bash
supergateway --stdio "npx @modelcontextprotocol/server-filesystem /" --port 8080
```

This is the install pattern for every Forge-OH MCP server (Phases 5–7).[^1]

### 2.3 Skills captured retroactively

`/skill-creator Create a skill for automating this workflow in the future`, stored in `<repo>/.agents/skills/` or `~/.agents/skills/`.[^1]

### 2.4 Tiered multi-LLM routing (populated only after Phase 0.3 concludes)

```toml
[llm]
model = "openai/der-winner-from-full-tier-combination-test>"
base_url = "http://127.0.0.1:der-winner-port>/v1"
api_key = "none"
num_retries = 3
retry_min_wait = 10
retry_max_wait = 60
max_output_tokens = "<measured-in-full-tier, not assumed>"

[llm.planner]
model = "openai/<planner-winner-from-full-tier-combination-test>"
base_url = "http://127.0.0.1:<planner-winner-port>/v1"
api_key = "none"
max_output_tokens = "<measured-in-full-tier, not assumed>"

[llm.condenser]
model = "openai/der-winner-from-full-tier-combination-test>"
base_url = "http://127.0.0.1:der-winner-port>/v1"
api_key = "none"
temperature = 0.1
max_input_tokens = 1024

[llm.embedding]
model = "<embedder-winner-from-full-tier-combination-test>"
base_url = "http://127.0.0.1:<embedder-winner-port>/v1"
api_key = "none"
```

Do not populate this file from Fast- or Medium-tier results, even provisionally. The `openai/` prefix routes the SDK's OpenAI-compatible client against `base_url`; if llama.cpp wins any role, its `--jinja` flag must be set for correct chat-template/tool-call handling. Verify each `base_url` independently against a trivial OpenHands task before combining into this config.[^2][^1]

### 2.5 Delegation model per task shape

`DelegateTool` for parallel independent subtasks; `TaskToolSet` for sequential dependency-ordered subtasks. If the Full tier selects a GPU-resident embedder cell, the dual/tri-port supervisor's swap logic (designed around exactly two resident roles) needs extension to manage a third concurrent GPU process — flag for design review before implementation. If coder and planner winners differ, confirm actual combined VRAM footprint post-benchmark before relying on concurrent `DelegateTool` routing; if it exceeds budget, reduce quant further or fall back to a sequential swap-script pattern.[^1]

***

## Phase 3 — Baseline Verification (runs only after Phase 0.3 concludes and Phase 2.4 is populated)

```bash
mkdir -p ~/dev/agent-canvas-stock && cd ~/dev/agent-canvas-stock
git clone https://github.com/OpenHands/agent-canvas.git .
npm install && npm run build
npm run start -- --backend-only=false --agent-server-url=http://127.0.0.1:8000
```

Verify against `DockerWorkspace` exclusively, using the Full tier's actual winning endpoints. Confirm tool-calling works correctly against every `base_url` in the final config, the event stream renders, confirmation UI fires, `code-explorer` is reachable, and MCP tools from §2.2 are callable.[^1]

### Phase 3 Verification

| Check | Method | Pass condition |
|---|---|---|
| Trivial task under DockerWorkspace, real winning endpoints | Run a scoped task end-to-end | Event stream, confirmation UI, tool-calling all functional |
| Role-switch test | Trigger coder→planner delegation | Both endpoints respond correctly; supervisor swap completes if applicable |

***

## Phase 4 — Register Forge-OH BFF as a Second Canvas Backend

```bash
cd ~/Forge-OH
cp .env.example .env
docker compose up -d bff
curl -sf http://localhost:8081/health || curl -sf http://localhost:8081/api/repograph/health
```

**Port collision check:** Forge-OH's BFF and any `llama-server`/vLLM instance defaulting to port 8081 (or overlapping with the Full tier's winning ports) must be resolved explicitly — remap one before bringing both up, never let one silently fail to bind:

```bash
grep -n "PORT\|8081" ~/Forge-OH/.env
```

Inspect the BFF's client contract before assuming compatibility:

```bash
grep -n "base_url\|httpx.AsyncClient" ~/Forge-OH/bff/openhands_client.py
```

If the event stream doesn't render correctly after switching the active backend in Canvas, patch `event_normalize.py` to pass through native SDK event shapes unmodified, or scope Forge-OH's registration to MCP-only capabilities (Phases 5–8).[^1]

### Phase 4 Verification

| Check | Method | Pass condition |
|---|---|---|
| Port collision resolved | Grep `.env` and winning-model ports | No conflict |
| Contract inspected | Review `openhands_client.py` | Compatibility confirmed before switching |
| Backend switch test | Switch active backend, repeat trivial task | Event stream renders unmodified |

***

## Phase 5 — GPU Telemetry as an MCP Server

```bash
mkdir -p ~/dev/mcp-servers/gpu-monitor
cp ~/Forge-OH/bff/services/gpu_monitor.py ~/dev/mcp-servers/gpu-monitor/
```

Extend `gpu_status()` to report the process name/role (coder/planner/embedder) bound to the GPU, not just utilization/temperature, reflecting whatever resident-process topology the Full tier's combination test determined.[^1]

### Phase 5 Verification

| Check | Method | Pass condition |
|---|---|---|
| Invoke `gpu_status` | Call during active use | Correctly identifies resident role/model matching actual topology |

***

## Phase 6 — Inference Backend Health + Episodic Memory as MCP Servers

```bash
mkdir -p ~/dev/mcp-servers/inference-backends
cp -r ~/Forge-OH/bff/services/inference_backends ~/dev/mcp-servers/inference-backends/lib

mkdir -p ~/dev/mcp-servers/episodic-memory
cp ~/Forge-OH/bff/services/episodic_memory.py ~/dev/mcp-servers/episodic-memory/
```

Forge-OH's `inference_backends` adapters were written against Ollama/vLLM/SGLang, not raw llama.cpp OpenAI-compatible servers — if llama.cpp wins any role, real adapter code changes are required in `inference_backends/registry.py`, not just registry configuration. The embedding health-check adapter must be generic enough to work against whichever runtime wins, without a second code change. If a CPU-resident embedder is used instead of GPU-resident, register it as its own adapter entry distinct from the GPU-resident endpoints, so a CPU-bound failure is never conflated with a GPU-resident failure.[^1]

### Phase 6 Verification

| Check | Method | Pass condition |
|---|---|---|
| Invoke `list_backends`/`backend_health` | Call against actual winning endpoints | Real health data returned, not stale adapters |
| Embedding adapter genericity | Confirm no further code change needed post-decision | Works against winning runtime out of the box |

***

## Phase 7 — RepoGraph: Neo4j + MCP Server + Canvas Panel

Forge-OH's existing Neo4j-backed code knowledge graph (`openhands_tools_ext/repograph/`) is surfaced as a persistent Canvas plugin panel using neovis.js against a live Neo4j instance, rather than Neo4j Browser alone or ephemeral Mermaid diagrams. Neo4j runs as independent infrastructure; the indexer is wrapped as an MCP server; the panel connects directly via Bolt protocol. **This is the largest net-new engineering effort in the plan** — a real frontend build (JS panel + Bolt client + Cypher query design), not a port. Scope it as its own mini-project and do not let it block Phases 8–11.[^1]

### Phase 7 Verification

| Check | Method | Pass condition |
|---|---|---|
| Neo4j restart persistence | Restart container, re-query | Data persists |
| Malicious-repo index safety | Index a deliberately malformed repo | Indexer fails safely, no crash/corruption |
| Canvas panel render | Load panel in Canvas | Graph renders correctly against live Bolt connection |
| Scale test | Load a 1000+-symbol repo | Panel remains responsive |

***

## Phase 8 — Security Hook: Port Only the Genuinely Novel Piece

A native `SecurityAnalyzerBase` subclass reimplements OH-GUI's blast-radius projection, layered on top of `LLMSecurityAnalyzer` (§0.6) — this supersedes OH-GUI's custom `AuthorizationCard`/blast-radius UI entirely; the only genuinely novel piece worth porting is the blast-radius projection logic. Preserve the four-outcome invariant against the documented mangled-class-name lookup bug.[^1]

### Phase 8 Verification

| Check | Method | Pass condition |
|---|---|---|
| Trigger HIGH-risk action | Perform an action requiring confirmation | Risk badge shown via layered native analyzer; audit record created |

***

## Phase 9 — Loop Guard (Rewrite, Not Port)

Implemented as a native, always-on agent-server-side hook (per §1.1), not a port of any prior frontend logic.[^1]

### Phase 9 Verification

| Check | Method | Pass condition |
|---|---|---|
| Send 3+ identical/near-identical tool calls | Repeated call test | Loop-guard hook flags repetition |

***

## Phase 10 — Dynamic Model Switching (Conditional)

Fully satisfied by Phase 2.4's benchmark-derived config in the common case. Retain only a dynamic-switching MCP tool if mid-conversation role switching beyond static config is required, and only if the Full tier's benchmark produces a genuine multi-model split — if a single model wins every role, this tool is unnecessary:[^1]

```python
@mcp.tool()
async def select_model(role: str, context_length: int) -> dict:
    """Report which base_url/model to use for a given role."""
```

***

## Phase 11 — Decommission

```bash
mkdir -p ~/dev/archived-frontends
mv ~/OH-GUI/apps/gui ~/dev/archived-frontends/oh-gui-apps-gui
mv ~/Forge-OH/src ~/dev/archived-frontends/forge-oh-src
rm -rf ~/OH-GUI/services/middleware
```

Retire Forge-OH's `bff/routers/*.py` and Socket.IO relay once every router's function has a confirmed native-tool, hook, MCP, or panel equivalent. Archive rather than delete for one release cycle.[^1]

### Phase 11 Verification

| Check | Method | Pass condition |
|---|---|---|
| Grep for remaining frontend imports | `grep -rn` across backend code for removed directories | None found |

***

## Full Verification Matrix

| Phase | Verification | Pass condition |
|---|---|---|
| -1 | OpenHands + llama.cpp + vLLM versions re-verified live; Blackwell target set; smoke test passes | Per §-1 table |
| 0.1 (Fast) | ≤30 min; eliminations documented; version regressions distinguished from model failures | Per §0.1 table |
| 0.2 (Medium) | ≤60 min; attainability gate; rubrics fixed pre-run; cross-runtime equivalence checked | Per §0.2 table |
| 0.3 (Full) | <10 hr; MDE stated; variance reported; combination test uses shortlists; decision justified | Per §0.3 table |
| 0.4–0.6 | Tier-skip documented; config lock; security layering | Per §0.4–0.6 |
| 1 | Zero LocalWorkspace; isolation confirmed; code-explorer delegation | Per Phase 1 table |
| 2 | Deployment mode, MCP kill-test, skill capture, tiered routing against real endpoints | No Fast/Medium values leak into production config |
| 3 | Trivial task + role-switch under DockerWorkspace, real endpoints | Fully functional |
| 4 | Port collision resolved; contract inspected; backend switch renders unmodified | Per Phase 4 table |
| 5–6 | GPU telemetry and backend health reflect actual topology | Accurate, non-conflated |
| 7 | Neo4j persistence, indexer safety, panel render, scale test | Per Phase 7 table |
| 8 | Trigger HIGH-risk action | Risk badge shown; audit persisted |
| 9 | Repeated tool calls | Loop-guard flags repetition |
| 11 | Grep for remaining frontend imports | None found |

## Risk Notes

- llama.cpp ships no semantic versions — only a rolling build-tag stream that can advance multiple times per day; any version number in this document is stale the moment it is written.[^2]
- vLLM's version reporting is genuinely inconsistent across mirrors — query the GitHub releases page live at build time, never trust a cached reference.[^2]
- No source establishes an explicit SDK-to-runtime version compatibility matrix; the low-risk inference (OpenAI-compatible HTTP surface only) is unconfirmed for this plan's specific candidate models and must be validated by §-1.5 and §0.1, not assumed.[^2]
- Building llama.cpp for the RTX 5090 without `-DCMAKE_CUDA_ARCHITECTURES=120` risks a silent mis-target given llama.cpp's active SM-family dispatch bugs.[^2]
- The three benchmark tiers are not interchangeable evidence — Fast/Medium results must never be promoted to production config under time pressure.[^1]
- Tier budgets (~30/~60/<600 min) exclude setup time (model pulls, dual GGUF/safetensors preparation, AVX-512 image builds) — budget setup separately.[^1]
- The candidate pool for every role must remain open at the Fast tier — no inheriting prior conclusions.[^1]
- Phase 4's event-shape compatibility remains the highest technical risk in the migration workstream.[^1]
- Phase 7 is the largest net-new engineering effort — scope independently, don't let it block Phases 8–11.[^1]
- Phase 8's action-kind mangling bug is a documented historical failure mode requiring explicit guarding.[^1]
- Phase 1's zero-`LocalWorkspace` policy must be enforced by CI/pre-commit grep, not documentation alone — a single missed fallback path defeats the entire trust model.[^1]
- vLLM's CPU AVX-512 dependency and GGUF/safetensors format incompatibility mean a model may need to be pulled/prepared twice if both runtimes remain in contention.[^1]
- If a vLLM cell wins the embedder role, no llama.cpp process needs to run in production at all for that workload — a meaningful operational simplification worth weighing.[^1]

***

## Perplexity Computer Execution Package

### Recommended Custom Instructions (paste into Perplexity Computer's system/custom-instructions field)

```
You are executing "Forge-OH + OH-GUI → Stock OpenHands/Agent Canvas — Execution Plan v16" on the local
workstation "Colossus" (128GB RAM, RTX 5090 32GB VRAM, Blackwell SM_120, Kubuntu Linux).

Non-negotiable rules:
1. NEVER hardcode a version number for OpenHands, openhands-sdk/tools/workspace/agent-server, agent-canvas,
   llama.cpp, or vLLM from this plan or any cached knowledge. Always re-fetch the live GitHub releases page
   or `pip show`/`npm ls` output immediately before pinning, and log the fetched tag + timestamp.
2. Execute phases strictly in order: Phase -1 before Phase 0; Phase 0 (Fast -> Medium -> Full tiers, in
   that order) before Phase 2.4 is populated; Phase 3 only after Phase 0.3 concludes and Phase 2.4 is
   populated. Do not skip ahead or promote a Fast/Medium-tier result into a production config file.
3. Treat DockerWorkspace as the only allowed workspace backend. Grep for "LocalWorkspace" after every
   phase that touches configuration or code and fail the phase if any reference is found outside
   test/example code.
4. Every benchmark run (Fast, Medium, Full tier; every role) must emit the 7-category JSON schema defined
   in Phase 0.0c, including the exact llama.cpp build tag and vLLM release tag used for that specific run.
5. Never estimate a latency figure — measure it directly, per call, and report variance across 3+ repeats
   where the plan specifies repeats.
6. Timestamp every rubric before the first scored output. Never edit a rubric after scoring begins.
7. After each phase, run that phase's Verification table exactly as specified before proceeding to the
   next phase. If a check fails, stop, report the failure, and do not proceed.
8. Distinguish explicitly between a "runtime-version regression" (a candidate that fails to launch only
   because of a newly-pinned runtime version) and a genuine model-candidate failure. Log them separately.
9. Report progress after each phase with: what was verified, what passed/failed, and the exact commands
   run. Do not claim a phase is complete without showing its verification table results.
10. If any repository, endpoint, or file referenced in this plan (OH-GUI, Forge-OH, agent-canvas,
    openhands-agent-server) is unreachable or missing, stop and report exactly what is missing rather
    than proceeding on assumption.
```

### Five Skills to Configure in Perplexity Computer

**Skill 1 — `version-pin-verifier`**
Purpose: re-fetches and reconciles live version tags for OpenHands SDK/CLI/agent-server/agent-canvas, llama.cpp, and vLLM before any install or benchmark step; refuses to proceed if a version is sourced from a cached document instead of a live fetch.
Trigger: any phase requiring `pip install`, `npm install`, `git checkout`, or `docker pull` of a plan component.

**Skill 2 — `benchmark-tier-runner`**
Purpose: executes the Fast/Medium/Full tier benchmark campaign per Phase 0, enforcing time budgets, the open-candidate-pool rule, MDE/attainability gates, timestamped rubrics, and emission of the 7-category JSON schema (including runtime build/release tags) for every run.
Trigger: Phase 0.1, 0.2, 0.3.

**Skill 3 — `docker-workspace-enforcer`**
Purpose: grep-based CI/pre-commit style check across the codebase for any `LocalWorkspace` reference, container isolation boundary test, and `code-explorer` read-only delegation verification.
Trigger: Phase 1, and re-run at the end of Phases 3, 4, 11 as a regression check.

**Skill 4 — `mcp-adapter-porter`**
Purpose: copies and adapts Forge-OH's GPU telemetry, inference-backend health, and episodic-memory services into standalone MCP servers behind `supergateway`, updating `inference_backends/registry.py` adapter code (not just config) if llama.cpp wins any role.
Trigger: Phase 5, 6.

**Skill 5 — `repograph-panel-builder`**
Purpose: scopes and builds the Neo4j-backed RepoGraph MCP server and Canvas plugin panel (neovis.js + Bolt protocol) as an isolated mini-project with its own persistence, safety, render, and scale tests, without blocking Phases 8–11.
Trigger: Phase 7, run independently/in parallel with Phases 8–11.

### Copy-Paste Prompts for Perplexity Computer (run in sequence)

**Prompt 1 — Phase -1:**
```
Execute Phase -1 of integration-execution-plan-v16.md exactly as written: re-fetch live version tags for
openhands-sdk/tools/workspace/agent-server, agent-canvas, llama.cpp, and vLLM; install/build/pin each to
the live-verified tag; run the -1.5 SDK-to-runtime smoke test against a trivial small model on both
llama.cpp and vLLM; and report the full Phase -1 Verification table with pass/fail for each row.
```

**Prompt 2 — Phase 0.1 (Fast tier):**
```
Execute Phase 0.1 (Fast tier) of integration-execution-plan-v16.md. Use the open candidate pool in 0.0b.
Launch every coder/planner/embedder candidate per the commands in 0.1, using only the Phase -1-pinned
runtime versions. Apply the elimination criteria exactly as written, distinguish runtime-version
regressions from genuine model failures, emit the full 7-category JSON schema per run, and stay within a
30-minute combined wall-clock budget. Report the elimination log and the Phase 0.1 Verification table.
```

**Prompt 3 — Phase 0.2 (Medium tier):**
```
Execute Phase 0.2 (Medium tier) using only the Fast-tier survivors. Compute the attainability gate before
running. Fix rubrics and timestamp them before the first scored output. Run the cross-runtime embedding
equivalence check. Stay within a 60-minute combined wall-clock budget. Produce a 2-3 candidate shortlist
per role with each ranking claim explicitly labeled by confidence, and report the Phase 0.2 Verification
table.
```

**Prompt 4 — Phase 0.3 (Full tier) + config lock:**
```
Execute Phase 0.3 (Full tier) using the Medium-tier shortlists. Run per-role final rankings and the
combination-level test as specified, with 3+ repeats and stated MDE per segment. Declare a final winner
per role and for the combination, explicitly justifying any non-top-scorer selection. Then apply Phase
0.5's post-decision configuration lock and Phase 0.6's security analyzer/confirmation policy. Populate
Phase 2.4's config.toml only from these Full-tier results. Report the Phase 0.3 Verification table.
```

**Prompt 5 — Phases 1-3 (workspace, suite config, baseline verification):**
```
Execute Phase 1 (DockerWorkspace-only policy with grep enforcement and code-explorer delegation test),
Phase 2 (deployment mode selection, MCP proxy setup, skill capture, and the Phase 2.4 config populated
from Phase 0.3's actual winners), and Phase 3 (clone/build/run agent-canvas against DockerWorkspace using
the real winning endpoints, including a role-switch test). Report all three Verification tables.
```

**Prompt 6 — Phases 4-6 (BFF registration, GPU telemetry, backend health/episodic memory):**
```
Execute Phase 4 (register Forge-OH's BFF as a second Canvas backend, resolving any port collision against
the actual winning model ports, inspecting the client contract before switching), Phase 5 (GPU telemetry
MCP server reflecting the actual resident-process topology), and Phase 6 (inference-backend health and
episodic-memory MCP servers, updating adapter code in inference_backends/registry.py if llama.cpp won any
role). Report all three Verification tables.
```

**Prompt 7 — Phase 7 (RepoGraph, scoped independently):**
```
Execute Phase 7 as an isolated mini-project: stand up Neo4j, wrap Forge-OH's RepoGraph indexer as an MCP
server, and build a Canvas plugin panel using neovis.js against a live Bolt connection. Run the
persistence, malicious-repo safety, panel-render, and 1000+-symbol scale tests. Do not block on Phases
8-11. Report the Phase 7 Verification table.
```

**Prompt 8 — Phases 8-11 (security hook, loop guard, dynamic switching, decommission):**
```
Execute Phase 8 (native SecurityAnalyzerBase blast-radius subclass layered on LLMSecurityAnalyzer, guarding
the mangled-class-name bug), Phase 9 (native always-on loop-guard hook), Phase 10 (add the select_model MCP
tool only if the Full tier produced a genuine multi-model split across roles), and Phase 11 (archive
OH-GUI/Forge-OH frontend code and retire Forge-OH's routers/Socket.IO relay once each has a confirmed native
equivalent). Report all four Verification tables and the Full Verification Matrix summary.
```

---

## References

1. [integration-execution-plan-v15.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/57152701/ba880ede-a3b0-40e0-a57e-9fd58cc03fc6/integration-execution-plan-v15.md) - # Forge-OH + OH-GUI → Stock OpenHands/Agent Canvas — Execution Plan (v15)

## What Changed and Why

...

2. [integration-execution-plan-v14.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/57152701/2553647d-0dad-46c4-bb28-31dddf2fcb38/integration-execution-plan-v14.md) - # Forge-OH + OH-GUI → Stock OpenHands/Agent Canvas — Execution Plan (v14)

## Scope and Ground Truth...

