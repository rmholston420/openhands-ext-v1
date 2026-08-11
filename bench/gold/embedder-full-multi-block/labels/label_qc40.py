#!/usr/bin/env python3
"""q-c40 calibration: "Graphiti temporal edge insertion for a MemoryPort claim"

Canonical answers at pinned corpus SHA (Kosmos-side).

Interpretation: "temporal edge insertion" for a MemoryPort claim breaks into:
  1. The port protocol method that inserts an edge (link_entities in ports/memory.py)
  2. The adapter implementation of that method (adapter.py write_edge / link_entities)
  3. The Graphiti temporal INDEX registration (record_event) — the Graphiti-specific piece
  4. The TemporalIndex Protocol declaring record_event

NOTE: ADR-075 D1 hard-deleted the concrete GraphitiTemporalIndex class body,
but the Protocol contract, InMemoryTemporalIndex test backend, and adapter
call sites remain. The pool reflects the live code at SHA a9d5bd6.

Grade-3 primaries (each answers a core piece):
  Kosmos/ports/memory.py L230-248: link_entities protocol method — the port
      contract for typed edge insertion between memory nodes (claims)
  Kosmos/adapters/memory/dozerdb/adapter.py L263-283: TemporalIndex Protocol
      including record_event (Graphiti backend's temporal registration)
  Kosmos/adapters/memory/dozerdb/adapter.py L291-330: InMemoryTemporalIndex
      backend implementing record_event (the temporal-edge insertion path)
  Kosmos/adapters/memory/dozerdb/adapter.py L440-465: adapter code that
      constructs subject/object/event nodes + inserts SUBJECT_OF / OBJECT_OF
      edges + calls _temporal.record_event

Grade-2 secondaries:
  Kosmos/adapters/memory/dozerdb/adapter.py L505-515: write_edge implementation
      (calls _graph.add_edge for the typed edge)

Grade-1 marginals:
  Kosmos/adapters/memory/dozerdb/adapter.py L1-60: module docstring naming
      Graphiti, MemoryPort, TemporalIndex components — context only
  Kosmos/adapters/memory/__init__.py: adapter export surface

Pool coverage verified against pool.jsonl:
  L275-349 covers L291-320 InMemoryTemporalIndex — retrieved by e08b only
  L260-284 covers L263-283 TemporalIndex Protocol — retrieved by e08b only
  L344-400 covers L440-460 boundary — all 3 Qwens (near miss on adapter body)
  L389-491 covers L440-465 write path — nomic only
  L434-491 covers L440-465 — nomic only
  L482-536 covers L505-513 write_edge — nomic only

DISCRIMINATIVE SIGNAL: This is the pattern q-c40 was chosen for. Each Qwen
finds different fragments. Grade-3 primaries at L263-283, L291-330, L440-465
each have partial pool coverage — some Qwens will hit them, others won't.
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from _calibration_driver import emit_qrels


PRIMARIES_G3 = [
    ("Kosmos", "ports/memory.py",
     (228, 250), "link_entities: port protocol for directed typed edge between memory nodes (MemoryPort claim edge)"),
    ("Kosmos", "adapters/memory/dozerdb/adapter.py",
     (261, 285), "TemporalIndex Protocol: Graphiti backend's record_event contract"),
    ("Kosmos", "adapters/memory/dozerdb/adapter.py",
     (291, 330), "InMemoryTemporalIndex: record_event implementation (temporal edge insertion path)"),
    ("Kosmos", "adapters/memory/dozerdb/adapter.py",
     (440, 465), "Adapter write path: insert subject/object nodes, SUBJECT_OF/OBJECT_OF edges, record_event"),
]

SECONDARIES_G2 = [
    ("Kosmos", "adapters/memory/dozerdb/adapter.py",
     (505, 520), "write_edge: applies typed edge via _graph.add_edge after AMG verdict"),
    ("Kosmos", "ports/memory.py",
     (180, 230), "MemoryPort docstring + query_temporal (adjacent context: Graphiti-backed temporal graph)"),
    ("Kosmos", "adapters/memory/dozerdb/adapter.py",
     (150, 200), "Add edge on _graph mock/stub interfaces (test-backend edge insertion signature)"),
    ("Kosmos", "adapters/memory/dozerdb/semantic_memory_path.py",
     (1, 5000), "Semantic memory lane: parallel write path that also feeds temporal index"),
]

MARGINALS_G1 = [
    ("Kosmos", "adapters/memory/dozerdb/adapter.py",
     (1, 60), "Module docstring: names Graphiti, MemoryPort, TemporalIndex — orientation only"),
    ("Kosmos", "adapters/memory/dozerdb/adapter.py",
     (343, 405), "DozerDbMemoryAdapter class docstring: mentions GraphitiTemporalIndex — background"),
    ("Kosmos", "adapters/memory/__init__.py",
     (1, 50), "Adapter export surface"),
    ("Kosmos", "adapters/memory/dozerdb/__init__.py",
     (1, 50), "Notes ADR-075 D1 hard-deletion of Graphiti class body — historical context"),
    ("Kosmos", "adapters/memory/dozerdb/test_contract.py",
     (1, 5000), "Adapter contract tests: exercise link_entities + record_event indirectly"),
]


if __name__ == "__main__":
    path, counts, unans = emit_qrels(
        qid="q-c40",
        primaries_g3=PRIMARIES_G3,
        secondaries_g2=SECONDARIES_G2,
        marginals_g1=MARGINALS_G1,
        notes=(
            "Compound query. Primary answer = MemoryPort link_entities protocol "
            "(ports/memory.py L228-250) + adapter write path (adapter.py L440-465) "
            "+ TemporalIndex.record_event (adapter.py L263-283 protocol, L291-330 impl). "
            "Discriminative: different Qwens retrieve different fragments per pool "
            "coverage analysis."
        ),
    )
    print(f"wrote {path}")
    print(f"grades: {counts}")
    print(f"unanswerable: {unans}")
    assert not unans, "expected answerable"
