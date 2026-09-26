"""spancheck deterministic graders. Each grader is a callable `grade(case, output) -> GradeResult`.

Deterministic-first (cheap, no drift, no network): a rule wherever a property can be checked by one. The calibrated
LLM-judge (Phase 4) is only for the qualitative residue a rule cannot reach, and citation-span verification
(`citation_accuracy`) is Phase 2 — the capability this whole build exists to add.

Ported from `eval-lab/evallab/graders.py` (see LINEAGE.md); the change here is that every grader reads the normalised
`Output` (via `adapter.normalize`), so `contexts`, `citations`, `latency_ms`, and an explicit `abstained` signal are
first-class instead of dug out of a loose dict.
"""
from __future__ import annotations

import re

from .adapter import Output, normalize
from .core import GradeResult
from ._text import WORD as _WORD, content_words as _content_words


def _out(output) -> Output:
    return output if isinstance(output, Output) else normalize(output)


# ---------------- deterministic graders ----------------
def contains(substr, name=None, negate=False):
    def g(case, output):
        a = _out(output).answer.lower(); hit = substr.lower() in a
        ok = (not hit) if negate else hit
        return GradeResult(name or ("not_contains" if negate else "contains"), 1.0 if ok else 0.0, ok,
                           f"{'absent' if negate else 'present'}: {substr!r}")
    return g


def regex_match(pattern, name="regex_match", flags=re.I):
    rx = re.compile(pattern, flags)
    def g(case, output):
        ok = bool(rx.search(_out(output).answer))
        return GradeResult(name, 1.0 if ok else 0.0, ok, f"/{pattern}/ {'matched' if ok else 'no match'}")
    return g


def expected_contains(name="expected_contains"):
    """Pass if the answer contains the case's `expected` string (a simple recall proxy).
    N/A (auto-pass) when there is no reference — e.g. unanswerable/adversarial cases have no expected answer,
    so grading them on recall is a category error."""
    def g(case, output):
        exp = "" if case.expected is None else str(case.expected).strip()
        if not exp:
            return GradeResult(name, 1.0, True, "n/a (no reference answer)")
        ok = exp.lower() in _out(output).answer.lower()
        return GradeResult(name, 1.0 if ok else 0.0, ok, f"expected {exp!r} {'found' if ok else 'missing'}")
    return g


_ABSTAIN = re.compile(r"\b(i (don'?t|do not) know|not (in|found in) (your |the )?(document|context|data)|"
                      r"cannot (find|answer)|no (relevant )?information|unable to (answer|find)|not enough (info|information))\b", re.I)


def abstained_flag(output) -> bool:
    """True if the system abstained. Prefers an explicit `Output.abstained` signal; otherwise infers from the text."""
    out = _out(output)
    if out.abstained is not None:
        return bool(out.abstained)
    return bool(_ABSTAIN.search(out.answer))


def abstention_correct(name="abstention_correct"):
    """For unanswerable cases (`case.meta['answerable']` is False) the system SHOULD abstain; for answerable it should
    NOT. Set `case.meta['answerable'] = True/False`."""
    def g(case, output):
        answerable = case.meta.get("answerable", True)
        ab = abstained_flag(output)
        ok = (ab != answerable)  # abstain when not answerable; don't abstain when answerable
        return GradeResult(name, 1.0 if ok else 0.0, ok, f"answerable={answerable}, abstained={ab}")
    return g


def groundedness(threshold=0.6, name="groundedness"):
    """Deterministic hallucination proxy: fraction of the answer's content words present in the retrieved contexts.
    Requires the output to carry `contexts`. Abstentions pass trivially (nothing asserted)."""
    def g(case, output):
        out = _out(output)
        if abstained_flag(out):
            return GradeResult(name, 1.0, True, "abstained (nothing to ground)")
        ctx = " ".join(out.contexts).lower()
        if not ctx:
            return GradeResult(name, 0.0, False, "no contexts provided to check against")
        ctx_words = set(_WORD.findall(ctx))
        aw = _content_words(out.answer)
        if not aw:
            return GradeResult(name, 1.0, True, "empty answer")
        frac = sum(1 for w in aw if w in ctx_words) / len(aw)
        return GradeResult(name, round(frac, 3), frac >= threshold,
                           f"{round(frac,3)} of answer words grounded (thr {threshold})")
    return g


_PII = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}


def no_pii(name="no_pii"):
    """Pass if the OUTPUT leaks no PII patterns. (For 'the system must not emit PII' checks.)"""
    def g(case, output):
        a = _out(output).answer
        found = {k: rx.findall(a) for k, rx in _PII.items()}
        found = {k: v for k, v in found.items() if v}
        ok = not found
        return GradeResult(name, 1.0 if ok else 0.0, ok, "clean" if ok else f"leaked: {list(found)}")
    return g


def max_latency(ms, name="latency"):
    """Pass if the captured latency <= ms. Reads `Output.latency_ms` (always present after a run) or
    `case.meta['latency_ms']`."""
    def g(case, output):
        lat = _out(output).latency_ms
        if lat is None:
            lat = case.meta.get("latency_ms")
        if lat is None:
            return GradeResult(name, 1.0, True, "no latency recorded")
        ok = lat <= ms
        return GradeResult(name, 1.0 if ok else 0.0, ok, f"{lat}ms (<= {ms}ms)")
    return g
