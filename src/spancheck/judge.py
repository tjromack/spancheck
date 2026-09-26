"""The LLM-judge — the entailment upgrade for what the deterministic checks can't reach (Phase 4, AB-DEC 009).

Prompts live in version-controlled files (`prompts/*.txt`, design pin #5) and every verdict records its `prompt_version`
and `model`. The judge reaches a model only through a caller-supplied `provider(prompt) -> str`; with `provider=None` it
takes a deterministic offline **stub** path, so tests and CI never need a key. One entailment prompt serves both citation
support (span → claim) and answer-level groundedness (contexts → answer).

Determinism carries the load elsewhere; the judge is opt-in and calibrated before it is trusted (`spancheck.calibrate`).
"""
from __future__ import annotations

import json
import re
from importlib import resources

from ._text import content_words, words
from .adapter import Output, normalize
from .core import GradeResult

_NEG = {"not", "no", "never", "cannot", "cant", "without", "none", "nor",
        "n't", "isn't", "aren't", "doesn't", "don't", "didn't", "won't", "wasn't", "weren't"}


def load_prompt(version: str = "entailment_v1") -> str:
    """Load a versioned judge prompt from the package's prompts/ directory."""
    return resources.files("spancheck.prompts").joinpath(f"{version}.txt").read_text(encoding="utf-8")


def render_prompt(version: str, **fields) -> str:
    """Fill the named placeholders ({claim}, {span}, …) in a prompt template. Only the given keys are substituted, so
    literal braces in the template (e.g. the JSON example) are left untouched."""
    tpl = load_prompt(version)
    for k, v in fields.items():
        tpl = tpl.replace("{" + k + "}", str(v))
    return tpl


def _has_negation(s: str) -> bool:
    return bool(set(re.findall(r"[a-z']+", (s or "").lower())) & _NEG)


def _stub_verdict(hypothesis: str, premise: str) -> dict:
    """A deterministic offline stand-in for a real judge. It is NOT a real entailment model: it uses lexical coverage
    plus a negation-polarity check (so it catches the contradiction the Phase-2 lexical proxy misses), and it will miss
    paraphrase/morphology that a real model would catch — which is exactly what calibration surfaces."""
    cw = content_words(hypothesis)
    pw = words(premise)
    cov = (sum(1 for w in cw if w in pw) / len(cw)) if cw else 1.0
    if _has_negation(premise) != _has_negation(hypothesis) and cov >= 0.5:
        return {"score": round(min(cov, 0.2), 3),
                "reason": "polarity mismatch (negation) — likely contradiction [stub]"}
    return {"score": round(cov, 3), "reason": f"lexical entailment {round(cov, 3)} [stub]"}


def _parse_verdict(raw: str) -> dict:
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        d = json.loads(m.group(0) if m else raw)
        return {"score": max(0.0, min(1.0, float(d.get("score", 0.0)))), "reason": str(d.get("reason", ""))[:300]}
    except Exception:
        return {"score": 0.0, "reason": f"unparseable judge response: {raw[:120]!r}"}


def judge_entailment(claim, span, provider=None, prompt_version="entailment_v1", model=None) -> dict:
    """Does `span` (SOURCE) support `claim` (STATEMENT)? Returns {score, reason, prompt_version, model}.

    `provider=None` → deterministic stub. A provider callable → the model's parsed verdict.
    """
    prompt = render_prompt(prompt_version, claim=claim, span=span)  # always rendered (exercises the versioned file)
    if provider is None:
        v = _stub_verdict(str(claim), str(span))
        model = model or "stub"
    else:
        v = _parse_verdict(provider(prompt))
        model = model or getattr(provider, "model", "unknown")
    return {"score": v["score"], "reason": v["reason"], "prompt_version": prompt_version, "model": model}


def judge_support(provider=None, prompt_version="entailment_v1", threshold=0.5, model=None):
    """Return a `support_fn(claim, span) -> (supported, score)` that `citation_accuracy` can use in place of its lexical
    support proxy — upgrading citation support to model-judged entailment while provenance stays deterministic."""
    def support_fn(claim, span):
        v = judge_entailment(claim, span, provider=provider, prompt_version=prompt_version, model=model)
        return (v["score"] >= threshold, v["score"])
    return support_fn


def llm_judge(provider=None, prompt_version="entailment_v1", threshold=0.5, model=None, name="llm_judge"):
    """Answer-level groundedness grader: does the retrieved context (SOURCE) support the answer (STATEMENT)?

    The qualitative counterpart to the deterministic `groundedness` proxy. Abstentions pass trivially. Opt-in: not in
    the default grader set (which stays offline)."""
    def g(case, output):
        out = output if isinstance(output, Output) else normalize(output)
        from .graders import abstained_flag
        if abstained_flag(out):
            return GradeResult(name, 1.0, True, "abstained (nothing to judge)")
        premise = " \n ".join(out.contexts)
        v = judge_entailment(out.answer, premise, provider=provider, prompt_version=prompt_version, model=model)
        return GradeResult(name, round(v["score"], 3), v["score"] >= threshold,
                           f"{v['reason']} [prompt {v['prompt_version']}, model {v['model']}]")
    return g
