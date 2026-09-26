"""Phase-1 behavioural tests: the adapter contract, the ported core, the deterministic graders,
and regression detection (diff/gate).

These assert the instrument does the right thing on hand-built systems whose behaviour we control:
a grounded answer passes, an ungrounded one fails groundedness, a correct abstention passes, a wrong
one fails, a PII leak is caught, latency is always captured, a crashing system is recorded not fatal,
and a regression is flagged by the gate.
"""
from __future__ import annotations

import spancheck
from spancheck import Case, evaluate, adapter, gate, diff
from spancheck.adapter import Output, normalize
from spancheck import graders as g


# ---------------- adapter / normalize ----------------
def test_normalize_str():
    o = normalize("hello")
    assert isinstance(o, Output) and o.answer == "hello" and o.contexts == []


def test_normalize_dict_aliases_and_types():
    o = normalize({"text": "hi", "context": "a passage", "citations": {"span": "x"},
                   "usage": {"input_tokens": 5}, "latency_ms": 12.0})
    assert o.answer == "hi"
    assert o.contexts == ["a passage"]           # single value coerced to list
    assert o.citations == [{"span": "x"}]         # single citation coerced to list
    assert o.usage == {"input_tokens": 5} and o.latency_ms == 12.0


def test_normalize_output_is_idempotent():
    src = Output(answer="x")
    assert normalize(src) is src


def test_adapter_times_the_call():
    run = adapter(lambda q: "an answer")
    out = run("q")
    assert isinstance(out, Output) and out.latency_ms is not None and out.latency_ms >= 0


def test_adapter_preserves_explicit_latency():
    run = adapter(lambda q: {"answer": "x", "latency_ms": 999.0})
    assert run("q").latency_ms == 999.0


# ---------------- fake systems under test ----------------
_CTX = "Either party may terminate the agreement with 30 days written notice."


def grounded_system(q):
    # answers, grounded in a retrieved context passage
    return {"answer": "Termination requires 30 days written notice.", "contexts": [_CTX]}


def abstaining_system(q):
    return {"answer": "I don't know — that isn't in the document.", "contexts": [_CTX]}


def hallucinating_system(q):
    return {"answer": "The company earned five billion dollars operating in Antarctica.", "contexts": [_CTX]}


def pii_leaking_system(q):
    return {"answer": "Contact the adjuster at john@example.com or 555-123-4567.", "contexts": [_CTX]}


def crashing_system(q):
    raise RuntimeError("provider exploded")


# ---------------- graders, exercised through evaluate ----------------
def test_grounded_answerable_case_passes_all_defaults():
    cases = [Case("c1", "notice period?", "answerable", expected="30 days", meta={"answerable": True})]
    sc = evaluate(cases, grounded_system).scorecard().by_grader()
    assert sc["groundedness"]["pass_rate"] == 1.0
    assert sc["abstention_correct"]["pass_rate"] == 1.0
    assert sc["no_pii"]["pass_rate"] == 1.0


def test_correct_abstention_on_unanswerable_passes():
    cases = [Case("c2", "revenue?", "unanswerable", meta={"answerable": False})]
    sc = evaluate(cases, abstaining_system).scorecard().by_grader()
    assert sc["abstention_correct"]["pass_rate"] == 1.0
    assert sc["groundedness"]["pass_rate"] == 1.0  # abstention grounds trivially


def test_failure_to_abstain_on_unanswerable_fails():
    # answerable=False but the system answers instead of abstaining -> abstention_correct must fail
    cases = [Case("c3", "revenue?", "unanswerable", meta={"answerable": False})]
    sc = evaluate(cases, grounded_system).scorecard().by_grader()
    assert sc["abstention_correct"]["pass_rate"] == 0.0


def test_hallucination_fails_groundedness():
    cases = [Case("c4", "revenue?", "answerable", meta={"answerable": True})]
    sc = evaluate(cases, hallucinating_system).scorecard().by_grader()
    assert sc["groundedness"]["pass_rate"] == 0.0


def test_pii_leak_is_caught():
    cases = [Case("c5", "who handles this?", "sensitive", meta={"answerable": True})]
    sc = evaluate(cases, pii_leaking_system).scorecard().by_grader()
    assert sc["no_pii"]["pass_rate"] == 0.0


def test_explicit_abstained_flag_beats_text_inference():
    # the text looks like a normal answer, but the system flags it as an abstention explicitly
    out = Output(answer="The notice period is 30 days.", abstained=True)
    assert g.abstained_flag(out) is True


def test_expected_contains_is_na_without_reference():
    grade = g.expected_contains()(Case("x", "q", meta={}), normalize("anything"))
    assert grade.passed and "n/a" in grade.detail


def test_latency_always_captured_even_for_bare_string():
    cases = [Case("c6", "q", meta={"answerable": True})]
    run = evaluate(cases, lambda q: "a plain string answer with no metadata")
    assert run.results[0].output.latency_ms is not None


# ---------------- resilience ----------------
def test_crashing_system_is_recorded_not_fatal():
    cases = [Case("c7", "q", meta={"answerable": True})]
    run = evaluate(cases, crashing_system)
    assert run.results[0].error is not None and "provider exploded" in run.results[0].error
    # the run object still exists and scores (the failed case simply has no grades)
    assert run.scorecard().overall_pass_rate() == 0.0


# ---------------- scorecard shapes ----------------
def test_scorecard_by_category_and_failures():
    cases = [
        Case("ok", "q", "answerable", meta={"answerable": True}),
        Case("leak", "q", "sensitive", meta={"answerable": True}),
    ]
    def system(q):
        return pii_leaking_system(q) if q == "q" else grounded_system(q)
    # route by case id via a closure isn't possible here; use two runs merged conceptually — instead
    # build one run with two systems by category:
    results = evaluate([cases[0]], grounded_system).results + evaluate([cases[1]], pii_leaking_system).results
    sc = spancheck.Scorecard(results)
    by_cat = sc.by_category()
    assert "answerable" in by_cat and "sensitive" in by_cat
    assert by_cat["sensitive"]["no_pii"] == 0.0
    assert len(sc.failures(grader="no_pii")) == 1


# ---------------- diff / gate (regression detection) ----------------
def test_gate_passes_when_thresholds_met():
    cases = [Case("c", "q", "answerable", meta={"answerable": True})]
    run = evaluate(cases, grounded_system)
    ok, reasons = gate(run, {"groundedness": 1.0, "no_pii": 1.0})
    assert ok and reasons == []


def test_gate_fails_on_threshold_and_reports_reason():
    cases = [Case("c", "q", "answerable", meta={"answerable": True})]
    run = evaluate(cases, hallucinating_system)
    ok, reasons = gate(run, {"groundedness": 0.9})
    assert not ok and any("groundedness" in r for r in reasons)


def test_diff_and_baseline_regression_gate():
    cases = [Case("c", "q", "answerable", meta={"answerable": True})]
    baseline = evaluate(cases, grounded_system)       # groundedness 1.0
    current = evaluate(cases, hallucinating_system)   # groundedness 0.0 -> a regression
    d = diff(baseline, current)
    assert d["groundedness"]["delta"] == -1.0
    ok, reasons = gate(current, {}, baseline=baseline, max_regression=0.0)
    assert not ok and any("regressed" in r for r in reasons)
