"""Registry-based candidate expansion for the Phase 0 runner.

Reads `bench/candidates/registry.json` and `models/manifest.json`, then
expands the per-tier candidate list required by the runner. Each expanded
candidate carries the info the server supervisors need:
  slug, format, runtime, hf_repo, hf_files, approx_size_gib,
  local_model_dir, local_gguf_file (relative to models/<slug>/).

Coder pool = registry.roles.coder that fits VRAM; planner pool includes
both planner-only entries and coder entries whose role_pool contains
'planner'. Embedder pool expands each embedder entry across the (CPU, GPU)
axis for its declared runtime (spec §0.1: eight-cell matrix minimum).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# --- On-disk locations ------------------------------------------------------

REGISTRY_PATH = REPO_ROOT / "bench" / "candidates" / "registry.json"
MANIFEST_PATH = REPO_ROOT / "models" / "manifest.json"
MODELS_DIR = REPO_ROOT / "models"


@dataclass
class ExpandedCandidate:
    """A single (model x runtime x device) cell the runner will benchmark."""
    slug: str
    hf_repo: str
    format: str            # "gguf" | "safetensors"
    runtime: str           # "llama.cpp" | "vllm"
    device: str            # "gpu" | "cpu"
    role: str              # "coder" | "planner" | "embedder"
    quant: str
    approx_size_gib: float
    local_model_dir: Path  # models/<slug>/
    local_gguf_file: Optional[str]  # relative filename for GGUF, else None
    notes: str = ""
    # Per-cell vLLM --tool-call-parser override. When None, falls back to
    # VLLMServer.ROLE_FLAGS[role] default ("hermes" for coder per ADR-0011).
    # Amendment 2026-08-11 04:07 EDT: parser is per-cell, driven by the
    # model's chat_template tool-call marker signature. Qwen3-Coder-Instruct
    # family uses "qwen3_coder" (XML <function=name>/<parameter=...>);
    # Qwen3-Thinking family uses "hermes" (<tool_call>{json}</tool_call>).
    tool_call_parser: Optional[str] = None
    # Per-cell vLLM --reasoning-parser. When None, NO reasoning parser flag is
    # emitted (ROLE_FLAGS no longer defaults it). Amendment 2026-08-11 04:26 EDT
    # (ADR-0011 amend 2): reasoning-parser is per-cell, model-card-driven.
    # Thinking models (Qwen3-Thinking-2507) set "qwen3" so vLLM strips
    # <think>...</think> blocks and exposes them via the `reasoning` field.
    # Non-thinking models (Qwen3-Coder-Instruct) MUST leave this None — the
    # qwen3 reasoning parser captures the model's XML function-call block into
    # `reasoning` before the tool_call_parser can extract it, resulting in
    # tool_calls=[] and mangled output on tasks that emit no separator prose.
    reasoning_parser: Optional[str] = None


def _load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _load_manifest() -> Optional[dict]:
    if not MANIFEST_PATH.exists():
        return None
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _infer_quant(entry: dict) -> str:
    slug = entry["slug"]
    if "bf16" in slug: return "bf16"
    if "int4" in slug: return "int4"
    if "awq" in slug: return "awq4"
    if "q6k" in slug or "q6_k" in slug: return "q6_k"
    if "q4kxl" in slug or "q4_k_xl" in slug: return "q4_k_xl"
    if "q8" in slug: return "q8_0"
    return "unknown"


def _resolve_gguf_file(entry: dict, manifest: Optional[dict]) -> Optional[str]:
    """Return the .gguf filename we should feed llama-server."""
    if entry["format"] != "gguf":
        return None
    slug = entry["slug"]
    # 1. Manifest wins if present.
    if manifest and "candidates" in manifest:
        m = manifest["candidates"].get(slug) or {}
        if m.get("gguf_file"):
            return m["gguf_file"]
    # 2. Registry hf_files first entry.
    if entry.get("hf_files"):
        return entry["hf_files"][0]
    # 3. Scan models/<slug>/ for a *.gguf file.
    d = MODELS_DIR / slug
    if d.exists():
        for f in sorted(d.iterdir()):
            if f.suffix == ".gguf":
                return f.name
    return None


def expand_for_role(role: str, *, include_oversized: bool = False,
                    vram_budget_gib: float = 30.0) -> list[ExpandedCandidate]:
    """Return candidates whose role_pool contains `role`.

    Filters out entries whose approx_size_gib exceeds vram_budget_gib unless
    include_oversized=True (used for reference-only cells).
    """
    reg = _load_registry()
    manifest = _load_manifest()
    out: list[ExpandedCandidate] = []

    def _matches(entry: dict, role: str) -> bool:
        return role in entry.get("role_pool", [])

    for source_role in ("coder", "planner", "embedder"):
        for entry in reg["roles"].get(source_role, []):
            if not _matches(entry, role):
                continue
            approx = float(entry.get("approx_size_gib", 0))
            if approx > vram_budget_gib and not include_oversized:
                continue
            gguf_file = _resolve_gguf_file(entry, manifest)
            slug = entry["slug"]
            cand = ExpandedCandidate(
                slug=slug,
                hf_repo=entry["hf_repo"],
                format=entry["format"],
                runtime=entry["runtime"],
                device="gpu",
                role=role,
                quant=_infer_quant(entry),
                approx_size_gib=approx,
                local_model_dir=MODELS_DIR / slug,
                local_gguf_file=gguf_file,
                notes=entry.get("notes", ""),
                tool_call_parser=entry.get("tool_call_parser"),
                reasoning_parser=entry.get("reasoning_parser"),
            )
            out.append(cand)

    # Embedder: add CPU cells for each entry (spec §0.1 matrix).
    if role == "embedder":
        cpu_variants = []
        for c in out:
            cpu = ExpandedCandidate(
                slug=c.slug,
                hf_repo=c.hf_repo,
                format=c.format,
                runtime=c.runtime,
                device="cpu",
                role=c.role,
                quant=c.quant,
                approx_size_gib=c.approx_size_gib,
                local_model_dir=c.local_model_dir,
                local_gguf_file=c.local_gguf_file,
                notes=c.notes + " (CPU cell)",
                tool_call_parser=c.tool_call_parser,
                reasoning_parser=c.reasoning_parser,
            )
            cpu_variants.append(cpu)
        out = out + cpu_variants

    return out
