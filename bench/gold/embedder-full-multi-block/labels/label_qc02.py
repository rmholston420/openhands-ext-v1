#!/usr/bin/env python3
"""q-c02 calibration: "where is the llama-swap adapter for LLMPort defined"

Grade-3 primaries (canonical location of the adapter definition):
- Kosmos/adapters/llm/llama_swap/adapter.py entire file (module + class def)
- Kosmos/adapters/llm/llama_swap/__init__.py entire file (module docstring
  identifies this as THE llama-swap adapter + re-exports LlamaSwapAdapter)

Grade 2 (relevant, not the definition):
- Kosmos/adapters/llm/llama_swap/test_contract.py (proves the adapter
  implements LLMPort; adjacent to definition but is the test not the def)
- Kosmos/ports/llm.py (the Protocol being implemented; adjacent context)

Grade 1 (marginal):
- Sibling llm adapters: Kosmos/adapters/llm/ollama/* (same architecture,
  demonstrates the pattern)
- Kosmos/plugins/zetesis/adapters/real/factory.py (consumes llama_swap
  via factory but doesn't define it)
- Kosmos/kernel/app.py (kernel wiring reference)

Grade 0: all remaining chunks (unrelated tests, __init__.py stubs, other
plugin internals, Rigpa-LMS, openhands-ext-v1 chunks).
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from _calibration_driver import emit_qrels

PRIMARIES_G3 = [
    ("Kosmos", "adapters/llm/llama_swap/adapter.py", (1, 276),
     "LlamaSwapAdapter class definition — the canonical location; "
     "implements LLMPort via httpx.AsyncClient against llama-swap's "
     "OpenAI-compat HTTP API (per ADR-009, Stage 1.3)"),
    ("Kosmos", "adapters/llm/llama_swap/__init__.py", (1, 25),
     "Module docstring explicitly identifies this package as THE Kosmos "
     "LLMPort adapter for llama-swap sidecar; re-exports LlamaSwapAdapter"),
]

GRADE_2 = [
    ("Kosmos", "adapters/llm/llama_swap/test_contract.py", (1, 149),
     "Contract test — asserts LlamaSwapAdapter satisfies LLMPort Protocol; "
     "adjacent to definition but is the test, not the def"),
    ("Kosmos", "ports/llm.py", (1, 126),
     "LLMPort Protocol definition — the abstract contract the adapter "
     "implements; needed context but not the adapter itself"),
]

GRADE_1 = [
    ("Kosmos", "adapters/llm/ollama/adapter.py", (1, 999),
     "Sibling LLMPort adapter (Ollama backend) — demonstrates the same "
     "architecture but is a different adapter"),
    ("Kosmos", "adapters/llm/ollama/__init__.py", (1, 999),
     "Sibling adapter package"),
    ("Kosmos", "adapters/llm/ollama/test_contract.py", (1, 999),
     "Sibling adapter contract test"),
    ("Kosmos", "plugins/zetesis/adapters/real/factory.py", (1, 999),
     "Factory that consumes llama_swap adapter — references it but does "
     "not define it"),
    ("Kosmos", "kernel/app.py", (1, 9999),
     "Kernel wiring — likely references the adapter but is boot/composition"),
    ("Kosmos", "adapters/__init__.py", (1, 999),
     "Top-level adapters package __init__ — mentions llama_swap"),
]


if __name__ == "__main__":
    path, counts, unans = emit_qrels(
        qid="q-c02",
        primaries_g3=PRIMARIES_G3,
        secondaries_g2=GRADE_2,
        marginals_g1=GRADE_1,
        notes=(
            "Calibration mode. Read llama_swap/__init__.py (25L, docstring "
            "explicitly names this the LLMPort llama-swap adapter), "
            "adapter.py 1-276 (LlamaSwapAdapter class), ports/llm.py 1-60 "
            "(LLMPort Protocol). Definition is unambiguous: single file "
            "adapters/llm/llama_swap/adapter.py."
        ),
    )
    print(f"wrote {path}")
    print(f"grades: {counts}")
    print(f"unanswerable: {unans}")
