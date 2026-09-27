"""Citation-span verification — the capability spancheck is named for.

For each span an answer cites, two deterministic checks, both of which must hold (DECISIONS AB-DEC 007):

  (a) provenance — is the cited span actually present in the retrieved contexts? (catches a *fabricated* span)
  (b) support   — does the span cover the claim it's attached to? (catches a *cited-but-unsupported* / wrong span,
                  including the "right answer, wrong citation" case)

Both are deterministic. Provenance is a strict normalised-substring match — a system should cite verbatim, and any
fuzzy acceptance would be a door for fabrication. Support is a lexical-overlap **proxy** for entailment: it cannot see
that a span *contradicts* a claim it shares words with — that is what the calibrated LLM-judge (Phase 4) is for. The
boundary is deliberate and tested (see tests/test_span.py::test_lexical_support_is_a_proxy_not_entailment).

Stdlib only. No model call, no network.
"""
from __future__ import annotations

from dataclasses import dataclass

from ._text import norm, words, content_words
from .adapter import Output, normalize
from .core import GradeResult


@dataclass
class CitationVerdict:
    span: str
    span_found: bool        # (a) provenance: the span is present, verbatim (normalised), in the source/contexts
    claim_supported: bool   # (b) support: the span covers the claim's content (lexical proxy)
    ok: bool                # span_found AND claim_supported
    support: float          # the coverage fraction behind claim_supported (0..1), for transparency
    reason: str
    source_id: str = None   # the source this citation names, if any
    scoped: bool = False    # True when provenance was checked against the NAMED source only


def _coerce_citation(c) -> dict:
    """A citation is a bare span string, or a dict with span (or quote/text), and optional claim/source_id."""
    if isinstance(c, str):
        return {"span": c, "claim": None, "source_id": None}
    if isinstance(c, dict):
        span = c.get("span") or c.get("quote") or c.get("text") or ""
        return {"span": str(span), "claim": c.get("claim"), "source_id": c.get("source_id")}
    return {"span": str(c), "claim": None, "source_id": None}


def _covers(claim: str, span: str, threshold: float):
    """Support proxy: fraction of the claim's content words present in the span. Returns (supported, fraction)."""
    cw = content_words(claim)
    if not cw:
        return True, 1.0  # a claim with no assertable content is vacuously supported
    sw = words(span)
    frac = sum(1 for w in cw if w in sw) / len(cw)
    return frac >= threshold, round(frac, 3)


def verify_citation(citation, contexts, answer: str = "", support_threshold: float = 0.6,
                    support_fn=None, sources: dict = None) -> CitationVerdict:
    """Verify one citation against the retrieved contexts. `answer` is the default claim when the citation names none.

    `support_fn`, if given, is a `(claim, span) -> (supported: bool, score: float)` callable used for the support check
    instead of the built-in lexical proxy — e.g. `spancheck.judge_support(provider=...)` for model-judged entailment.
    Provenance is always deterministic and is never delegated to a judge.

    `sources` (a `{source_id: text}` map), if given and the citation names a `source_id` present in it, scopes
    provenance to that **named source only** — so a span attributed to the wrong document fails even when it exists
    elsewhere in the corpus.
    """
    cit = _coerce_citation(citation)
    span = cit["span"]
    src_id = cit.get("source_id")
    if not span or not span.strip():
        return CitationVerdict("", False, False, False, 0.0, "empty citation span", source_id=src_id)

    # (a) provenance — strict normalised substring match. Scoped to the named source when we can; else all contexts.
    scoped = bool(sources and src_id and src_id in sources)
    if scoped:
        haystack = norm(str(sources[src_id]))
    else:
        haystack = norm(" \n ".join(str(c) for c in (contexts or [])))
    span_found = norm(span) in haystack

    # (b) support — does the span cover the claim (the cited sentence, else the whole answer)?
    claim = cit["claim"] if cit["claim"] else answer
    if support_fn is not None:
        supported, frac = support_fn(claim, span)
        frac = round(float(frac), 3)
        how = "judge"
    else:
        supported, frac = _covers(claim, span, support_threshold)
        how = "lexical"

    ok = span_found and supported
    if not span_found:
        reason = (f"misattributed span: not found in its cited source {src_id!r}" if scoped
                  else "fabricated span: not found verbatim in the contexts")
    elif not supported:
        reason = f"unsupported ({how}): span covers {frac} of the claim (< {support_threshold if how == 'lexical' else 'judge threshold'})"
    else:
        reason = f"verified ({how}{', source-scoped' if scoped else ''}): span present, support {frac}"
    return CitationVerdict(span, span_found, supported, ok, frac, reason, source_id=src_id, scoped=scoped)


def citation_accuracy(name: str = "citation_accuracy", support_threshold: float = 0.6,
                      pass_threshold: float = 1.0, require_citation: bool = True, support_fn=None):
    """Grader: the fraction of an answer's citations that are verified (present AND supporting).

    - Abstentions pass trivially (nothing cited).
    - An answer that asserts a claim with **no** citations fails when `require_citation` (the default) — an uncited
      claim is unverifiable.
    - `score` is the fraction of citations that are OK; the case **passes** only when that fraction >= `pass_threshold`
      (default 1.0 — one broken citation breaks the audit trail).
    - `support_fn` (e.g. `spancheck.judge_support(provider=...)`) upgrades the support check from the lexical proxy to
      model-judged entailment; provenance stays deterministic.
    """
    def g(case, output):
        out = output if isinstance(output, Output) else normalize(output)
        from .graders import abstained_flag  # local import: graders imports nothing from span, no cycle
        if abstained_flag(out):
            return GradeResult(name, 1.0, True, "abstained (nothing to cite)")

        cits = out.citations or []
        if not cits:
            if require_citation:
                return GradeResult(name, 0.0, False, "answer makes a claim but cites no span (unverifiable)")
            return GradeResult(name, 1.0, True, "no citations present; citation not required")

        verdicts = [verify_citation(c, out.contexts, out.answer, support_threshold, support_fn=support_fn,
                                    sources=out.sources)
                    for c in cits]
        n_ok = sum(1 for v in verdicts if v.ok)
        frac = n_ok / len(verdicts)
        passed = frac >= pass_threshold
        bad = [v.reason for v in verdicts if not v.ok]
        detail = f"{n_ok}/{len(verdicts)} citations verified"
        if bad:
            detail += "; failing: " + "; ".join(bad[:3])
        return GradeResult(name, round(frac, 3), passed, detail)
    return g
