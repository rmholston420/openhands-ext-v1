"""Phase 0 tier-runner internals.

Modules:
  progress   — line-buffered timestamped progress printer (ADR-0007 §7)
  server     — VLLMServer / LlamaCppServer process supervisors
  nvml       — background GPU-envelope sampler
  probes     — coder / planner / embedder probe implementations
  candidates — registry loader + candidate expansion
  main       — end-to-end tier orchestration (imported by scripts/benchmark-tier-runner.py)
"""
