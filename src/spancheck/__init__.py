"""spancheck — score a grounded-answer system on citation accuracy, abstention correctness,
hallucination rate, cost and latency, and emit an audit log a compliance reviewer can read.

Public API (Phase 1 — the ported measurement core + the thin adapter contract):

    from spancheck import Case, evaluate, adapter, Run, Scorecard, gate, diff

Deterministic graders live in `spancheck.graders`. Citation-span verification (the capability this build exists to
add) lands in Phase 2; the versioned audit log in Phase 3; the calibrated LLM-judge in Phase 4. See TODO.md.

Nothing here hard-codes a model provider or depends on any other project's internals (CLAUDE.md design pins).
"""
from __future__ import annotations

from .adapter import Output, adapter, normalize
from .core import (
    Case,
    GradeResult,
    CaseResult,
    Run,
    Scorecard,
    evaluate,
    run_eval,
    diff,
    gate,
    default_graders,
)
from .span import citation_accuracy, verify_citation, CitationVerdict
from . import graders

__version__ = "0.0.1"

__all__ = [
    # the declared public surface
    "Case", "evaluate", "adapter", "Run", "Scorecard", "gate", "diff",
    # citation-span verification (the capability spancheck is named for)
    "citation_accuracy", "verify_citation", "CitationVerdict",
    # supporting types + the grader library
    "Output", "normalize", "GradeResult", "CaseResult", "run_eval", "default_graders", "graders",
]
