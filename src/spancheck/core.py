"""spancheck core — the reusable measurement instrument.

Point it at ANY grounded-answer system via a `input -> output` callable, give it Cases and graders, and get a
Run -> Scorecard (per-grader, per-category) plus a baseline diff and a CI gate for regressions.

Dependency-free (stdlib only). Ported from `eval-lab/evallab/core.py` (see LINEAGE.md); the substantive change here
is that every system call is **timed and normalised into an `Output`** (adapter.py), so latency is always captured and
scoring is uniform whether or not the caller pre-wrapped their system with `adapter()`.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from statistics import mean

from .adapter import Output, normalize


@dataclass
class Case:
    """One test case. `input` is whatever the system takes; `expected` is an optional reference/label.

    Put `meta["answerable"] = True/False` for abstention scoring (True = the answer is in the corpus and the
    system should answer; False = it is not and the system should abstain).
    """
    id: str
    input: object
    category: str = "default"
    expected: object = None
    meta: dict = field(default_factory=dict)


@dataclass
class GradeResult:
    grader: str
    score: float            # 0.0 .. 1.0
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    case_id: str
    category: str
    output: object          # an Output (or None on error)
    grades: list            # list[GradeResult]
    error: str = None

    def output_dict(self):
        return self.output.to_dict() if isinstance(self.output, Output) else self.output


def default_graders():
    """The deterministic grader set applied when `evaluate` is called without explicit graders.

    Includes **citation accuracy** (Phase 2): on the tool's own thesis, an answer that cites nothing verifiable scores
    zero there by default (`require_citation=True`). A caller who doesn't want that supplies their own grader list.
    Cost/latency reporting is Phase 3; the calibrated LLM-judge is Phase 4.
    """
    from . import graders as g
    from .span import citation_accuracy
    return [g.abstention_correct(), g.groundedness(), g.no_pii(), citation_accuracy()]


def evaluate(cases, system, graders=None, on_case=None, retries=0, backoff=3.0, delay=0.0):
    """Run each case through `system` (callable input->output), normalise + time the output, apply `graders`.

    `system` may be a raw callable or one already wrapped with `adapter()`; either way its result is normalised to an
    `Output` and, if it carries no latency, this call is timed and the latency injected — so a captured run always has
    what the offline metrics need (design pin #3).

    Resilient to a flaky system (LLM rate-limits/overloads): `retries` re-attempts a case with exponential `backoff`
    seconds; a case that still fails is RECORDED (err) and the run continues — one bad case never crashes the run.
    `delay` seconds between cases eases rate limits. (Ctrl+C still stops it.)
    """
    graders = default_graders() if graders is None else graders
    results = []
    for c in cases:
        out, grades, err = None, [], None
        for attempt in range(retries + 1):
            try:
                start = time.perf_counter()
                raw = system(c.input)
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                out = normalize(raw)
                if out.latency_ms is None:
                    out.latency_ms = round(elapsed_ms, 3)
                grades = [g(c, out) for g in graders]
                err = None
                break
            except Exception as e:  # a system/grader error is a data point, not a crash
                out, grades, err = None, [], repr(e)
                if attempt < retries:
                    time.sleep(backoff * (attempt + 1))
        cr = CaseResult(c.id, c.category, out, grades, err)
        results.append(cr)
        if on_case:
            on_case(cr)
        if delay:
            time.sleep(delay)
    return Run(results)


# `run_eval` kept as an alias for readers coming from evallab.
run_eval = evaluate


class Run:
    def __init__(self, results):
        self.results = results

    def scorecard(self):
        return Scorecard(self.results)

    # ---- persistence (for baselines / regression gating). The versioned, compliance-readable
    #      audit log is a superset of this and lands in Phase 3 (`audit_log()`). ----
    def to_dict(self):
        return {"results": [
            {"case_id": r.case_id, "category": r.category, "error": r.error,
             "output": r.output_dict(),
             "grades": [asdict(g) for g in r.grades]} for r in self.results]}

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load(path):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        results = [CaseResult(r["case_id"], r.get("category", "default"), r.get("output"),
                              [GradeResult(**g) for g in r["grades"]], r.get("error"))
                   for r in d["results"]]
        return Run(results)


class Scorecard:
    def __init__(self, results):
        self.results = results

    def by_grader(self):
        agg = {}
        for cr in self.results:
            for g in cr.grades:
                a = agg.setdefault(g.grader, {"s": [], "p": []})
                a["s"].append(g.score); a["p"].append(1 if g.passed else 0)
        return {k: {"score": round(mean(v["s"]), 3), "pass_rate": round(mean(v["p"]), 3), "n": len(v["s"])}
                for k, v in agg.items()}

    def by_category(self):
        cats = {}
        for cr in self.results:
            c = cats.setdefault(cr.category, {})
            for g in cr.grades:
                a = c.setdefault(g.grader, {"p": []})
                a["p"].append(1 if g.passed else 0)
        return {cat: {k: round(mean(v["p"]), 3) for k, v in gr.items()} for cat, gr in cats.items()}

    def overall_pass_rate(self):
        passes = [1 if g.passed else 0 for cr in self.results for g in cr.grades]
        return round(mean(passes), 3) if passes else 0.0

    def failures(self, grader=None):
        """CaseResults with at least one failed grade (optionally for a specific grader)."""
        out = []
        for cr in self.results:
            fails = [g for g in cr.grades if not g.passed and (grader is None or g.grader == grader)]
            if fails or cr.error:
                out.append((cr, fails))
        return out


def diff(baseline: Run, current: Run):
    """Per-grader delta of pass_rate (current - baseline). Negative = a regression."""
    b = baseline.scorecard().by_grader()
    c = current.scorecard().by_grader()
    out = {}
    for k in sorted(set(b) | set(c)):
        bp = b.get(k, {}).get("pass_rate")
        cp = c.get(k, {}).get("pass_rate")
        out[k] = {"baseline": bp, "current": cp,
                  "delta": None if bp is None or cp is None else round(cp - bp, 3)}
    return out


def gate(current: Run, thresholds: dict, baseline: Run = None, max_regression: float = 0.0):
    """CI regression gate. Returns (ok: bool, reasons: list[str]).
    thresholds: {grader: min_pass_rate}. If baseline given, also fail on a pass_rate drop > max_regression.
    """
    reasons = []
    sc = current.scorecard().by_grader()
    for g, minv in (thresholds or {}).items():
        got = sc.get(g, {}).get("pass_rate", 0.0)
        if got < minv:
            reasons.append(f"{g} pass_rate {got} < threshold {minv}")
    if baseline is not None:
        for g, d in diff(baseline, current).items():
            if d["delta"] is not None and d["delta"] < -abs(max_regression):
                reasons.append(f"{g} regressed by {d['delta']} (> {max_regression})")
    return (len(reasons) == 0, reasons)
