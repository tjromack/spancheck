"""Phase 4: the calibrated LLM-judge (stub path — deterministic, no key needed).

Covers: the versioned prompt loads and carries a version; a verdict records prompt_version + model; the judge upgrades
citation support to entailment and — the headline — catches the negation contradiction the Phase-2 lexical proxy missed;
a caller-supplied provider is used and parsed; and calibration produces a measured agreement number against the gold set.
"""
from __future__ import annotations

import json
from pathlib import Path

import spancheck
from spancheck import (Case, evaluate, citation_accuracy, judge_entailment, judge_support, llm_judge,
                       load_prompt, calibrate_judge)
from spancheck.adapter import Output


# ---------------- prompt (design pin #5: versioned, in a file) ----------------
def test_prompt_loads_from_versioned_file():
    p = load_prompt("entailment_v1")
    assert "{claim}" in p and "{span}" in p and "JSON" in p


# ---------------- verdict shape + attribution ----------------
def test_verdict_records_prompt_version_and_model():
    v = judge_entailment("the fee is monthly", "a fee is charged monthly", provider=None)
    assert set(v) == {"score", "reason", "prompt_version", "model"}
    assert v["prompt_version"] == "entailment_v1" and v["model"] == "stub"
    assert 0.0 <= v["score"] <= 1.0


# ---------------- the headline: the judge catches what lexical support missed ----------------
def test_stub_judge_catches_negation_contradiction():
    # Phase 2 (test_span) documented that lexical support scores this as SUPPORTED (its blind spot).
    # The judge (even the stub, via a polarity check) must NOT.
    v = judge_entailment("The notice period is 30 days.",
                         "The notice period is not 30 days under the amended terms.", provider=None)
    assert v["score"] < 0.5  # judged as (likely) contradiction, unlike the lexical proxy


def test_citation_accuracy_with_judge_support_fails_the_contradiction():
    ctx = ["The notice period is not 30 days under the amended terms."]
    out = Output(answer="The notice period is 30 days.", contexts=ctx,
                 citations=[{"span": "The notice period is not 30 days under the amended terms",
                             "claim": "The notice period is 30 days"}])
    case = Case("c", "q", meta={"answerable": True})
    # lexical proxy is fooled (span found + words overlap) -> passes
    lexical = citation_accuracy()(case, out)
    assert lexical.passed is True
    # judge-backed support catches the contradiction -> fails
    judged = citation_accuracy(support_fn=judge_support())(case, out)
    assert judged.passed is False


# ---------------- provider seam (no lock-in): a caller-supplied provider is used ----------------
def test_custom_provider_is_called_and_parsed():
    calls = {"n": 0}

    def fake_provider(prompt):
        calls["n"] += 1
        assert "STATEMENT" in prompt or "{claim}" not in prompt  # the template was rendered
        return '{"score": 0.91, "reason": "supported by the source"}'
    fake_provider.model = "fake-model-1"

    v = judge_entailment("x supports y", "y is established by x", provider=fake_provider)
    assert calls["n"] == 1 and v["score"] == 0.91 and v["model"] == "fake-model-1"


def test_unparseable_provider_response_scores_zero():
    v = judge_entailment("a", "b", provider=lambda p: "the model rambled with no json")
    assert v["score"] == 0.0 and "unparseable" in v["reason"]


# ---------------- llm_judge as an answer-level grader ----------------
def test_llm_judge_grader_abstention_passes_and_records_model():
    abst = Output(answer="I don't know — that isn't in the document.", contexts=["something"])
    g = llm_judge()  # stub
    grade = g(Case("c", "q", meta={"answerable": False}), abst)
    assert grade.passed is True and "abstained" in grade.detail


# ---------------- calibration: a MEASURED number ----------------
def _gold_path():
    return str(Path(__file__).resolve().parents[1] / "calibration" / "entailment_gold.jsonl")


def test_calibration_reports_agreement_on_gold_with_stub():
    gold = [json.loads(l) for l in Path(_gold_path()).read_text(encoding="utf-8").splitlines() if l.strip()]
    r = calibrate_judge(gold, provider=None)
    assert r["n"] == len(gold) and 0.0 <= r["agreement"] <= 1.0
    c = r["confusion"]
    assert c["tp"] + c["fp"] + c["tn"] + c["fn"] == r["n"]
    assert r["model"] == "stub" and r["prompt_version"] == "entailment_v1"


def test_calibration_gold_set_catches_the_clear_negation_case():
    # the stub should at least get the explicit negation contradiction right (that's its whole point)
    gold = [json.loads(l) for l in Path(_gold_path()).read_text(encoding="utf-8").splitlines() if l.strip()]
    r = calibrate_judge(gold, provider=None)
    neg = next(row for row in r["rows"] if "not 30 days" in row["span"])
    assert neg["label"] is False and neg["pred"] is False and neg["correct"] is True


def test_default_grader_set_stays_offline_no_judge():
    # the judge is opt-in; default_graders must not include an LLM-judge grader
    names = {g.grader for g in
             [gr(Case("c", "q", meta={"answerable": True}), spancheck.normalize({"answer": "x", "contexts": ["x"]}))
              for gr in spancheck.default_graders()]}
    assert "llm_judge" not in names
