"""spancheck — score a grounded-answer system on citation accuracy, abstention correctness,
hallucination rate, cost and latency, and emit an audit log a compliance reviewer can read.

Scaffold stage: the package is installable and the CLI entry point resolves, but the public
API (`Case`, `evaluate`, `adapter`, `Run`, …) is not implemented yet. It lands in Phase 1
(see TODO.md), ported and generalised from `eval-lab/evallab` per DECISIONS.md AB-DEC 002.

The intended public surface, once shipped:

    from spancheck import Case, evaluate, adapter

Design pins live in CLAUDE.md; nothing here hard-codes a model provider or depends on any
other project's internals.
"""
from __future__ import annotations

__version__ = "0.0.1"

# The public API is declared here so the target is unambiguous; imports are added as each
# name is implemented (Phase 1+). Referencing one before then raises a clear NotImplementedError
# rather than a bare ImportError.
__all__ = ["Case", "evaluate", "adapter", "Run", "Scorecard", "gate", "diff"]


def __getattr__(name: str):  # PEP 562 — informative error while the API is still scaffolding
    if name in __all__:
        raise NotImplementedError(
            f"spancheck.{name} is not implemented yet — this is the scaffold stage. "
            f"See TODO.md (Phase 1 ports the core from evallab)."
        )
    raise AttributeError(f"module 'spancheck' has no attribute {name!r}")
