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
from .audit import build_audit_log, cost_latency, SCHEMA_VERSION
from .judge import judge_entailment, judge_support, llm_judge, load_prompt
from .calibrate import calibrate_judge
from . import graders

try:  # single source of truth: the version declared in pyproject, read from installed metadata
    from importlib.metadata import version as _pkg_version, PackageNotFoundError
    __version__ = _pkg_version("spancheck")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0.0.0+dev"

__all__ = [
    # the declared public surface
    "Case", "evaluate", "adapter", "Run", "Scorecard", "gate", "diff",
    # citation-span verification (the capability spancheck is named for)
    "citation_accuracy", "verify_citation", "CitationVerdict",
    # cost/latency + the versioned audit log
    "build_audit_log", "cost_latency", "SCHEMA_VERSION",
    # the calibrated LLM-judge (opt-in; stub by default, no provider lock-in)
    "judge_entailment", "judge_support", "llm_judge", "load_prompt", "calibrate_judge",
    # supporting types + the grader library
    "Output", "normalize", "GradeResult", "CaseResult", "run_eval", "default_graders", "graders",
]
