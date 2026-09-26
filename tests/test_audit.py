"""Phase 3: cost/latency aggregation, the versioned audit log, and offline re-scoring.

The theme is design pin #3: a captured run holds everything, so metrics and the compliance record are produced with
no system call. These tests build a run, then compute cost/latency, build the audit log, re-score at a new threshold,
and round-trip through save/load — all offline.
"""
from __future__ import annotations

import json

import spancheck
from spancheck import Case, evaluate, Run, build_audit_log, cost_latency, SCHEMA_VERSION, citation_accuracy
from spancheck.adapter import Output

CTX = [
    "Either party may terminate the agreement with 30 days written notice.",
    "Invoices are payable within 45 days of receipt.",
]


def valid_system(q):
    return {"answer": "Either party may terminate with 30 days written notice.",
            "contexts": CTX,
            "citations": [{"span": "Either party may terminate the agreement with 30 days written notice",
                           "claim": "Either party may terminate with 30 days written notice"}],
            "usage": {"input_tokens": 400, "output_tokens": 100},
            "latency_ms": 300.0}


def _run():
    cases = [Case("q1", "notice period?", "answerable", expected="30 days", meta={"answerable": True})]
    return evaluate(cases, valid_system)


# ---------------- cost / latency ----------------
def test_latency_aggregates():
    def sys_lat(q):
        return {"answer": "x", "contexts": CTX, "latency_ms": {"a": 100.0, "b": 200.0, "c": 300.0}[q]}
    run = evaluate([Case(c, c, meta={"answerable": True}) for c in "abc"], sys_lat)
    lat = run.cost_latency()["latency"]
    assert lat["n"] == 3 and lat["total_ms"] == 600.0 and lat["mean_ms"] == 200.0
    assert lat["max_ms"] == 300.0 and lat["p50_ms"] in (200.0,) and lat["p95_ms"] == 300.0


def test_cost_tokens_summed_and_cost_null_without_pricing():
    cost = _run().cost_latency()["cost"]
    assert cost["input_tokens"] == 400 and cost["output_tokens"] == 100 and cost["total_tokens"] == 500
    assert cost["cost_usd"] is None and cost["pricing_applied"] is False  # not invented


def test_cost_computed_when_pricing_supplied():
    cost = _run().cost_latency(pricing={"input_per_1k": 3.0, "output_per_1k": 15.0})["cost"]
    # 400/1000*3 + 100/1000*15 = 1.2 + 1.5 = 2.7
    assert cost["cost_usd"] == 2.7 and cost["pricing_applied"] is True


def test_explicit_cost_usd_is_summed():
    def sys_cost(q):
        return {"answer": "x", "contexts": CTX, "usage": {"cost_usd": 0.01}}
    run = evaluate([Case("a", "a", meta={"answerable": True}), Case("b", "b", meta={"answerable": True})], sys_cost)
    assert run.cost_latency()["cost"]["cost_usd"] == 0.02


# ---------------- the versioned audit log ----------------
def test_audit_log_shape_and_version():
    doc = _run().audit_log()
    assert doc["schema_version"] == SCHEMA_VERSION == "1.0"
    assert doc["spancheck_version"] == spancheck.__version__
    assert "created_at" in doc
    s = doc["summary"]
    assert set(["n_cases", "overall_pass_rate", "by_grader", "by_category", "latency", "cost"]).issubset(s)
    assert s["n_cases"] == 1


def test_audit_log_is_self_describing_per_case():
    case = doc = _run().audit_log()["cases"][0]
    assert case["input"] == "notice period?" and case["expected"] == "30 days"
    assert case["meta"] == {"answerable": True}
    assert "output" in case and "grades" in case


def test_audit_log_carries_per_citation_verdicts():
    case = _run().audit_log()["cases"][0]
    cits = case["citations"]
    assert len(cits) == 1
    v = cits[0]
    assert v["span_found"] is True and v["claim_supported"] is True and v["ok"] is True
    assert "reason" in v and isinstance(v["support"], float)


def test_audit_log_writes_valid_json(tmp_path):
    p = tmp_path / "audit.json"
    _run().audit_log(str(p))
    loaded = json.loads(p.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "1.0" and loaded["cases"][0]["case_id"] == "q1"


# ---------------- offline re-scoring (design pin #3) ----------------
def test_rescore_changes_nothing_when_graders_identical():
    run = _run()
    before = run.scorecard().by_grader()["citation_accuracy"]["pass_rate"]
    after = run.rescore([citation_accuracy()]).scorecard().by_grader()["citation_accuracy"]["pass_rate"]
    assert before == after == 1.0


def test_rescore_at_stricter_threshold_flips_a_result_offline():
    # The cached span covers ~part of a broad claim; a higher support threshold should fail it — with NO system call.
    out = Output(answer="a", contexts=CTX,
                 citations=[{"span": "Invoices are payable within 45 days of receipt",
                             "claim": "Invoices are payable within 45 days of receipt every quarter without exception"}])
    run = Run([spancheck.CaseResult("c", "answerable", out, [], None, input="q", meta={"answerable": True})])
    lenient = run.rescore([citation_accuracy(support_threshold=0.4)]).scorecard().by_grader()["citation_accuracy"]
    strict = run.rescore([citation_accuracy(support_threshold=0.95)]).scorecard().by_grader()["citation_accuracy"]
    assert lenient["pass_rate"] == 1.0 and strict["pass_rate"] == 0.0


def test_rescore_carries_errored_cases_through():
    def boom(q):
        raise RuntimeError("nope")
    run = evaluate([Case("c", "q", meta={"answerable": True})], boom)
    rescored = run.rescore([citation_accuracy()])
    assert rescored.results[0].error is not None and rescored.results[0].grades == []


# ---------------- round-trip ----------------
def test_save_load_round_trip_restores_output_and_regrades(tmp_path):
    p = tmp_path / "run.json"
    _run().save(str(p))
    loaded = Run.load(str(p))
    # the Output came back as an Output, and abstention/meta survived so a re-grade works offline
    assert isinstance(loaded.results[0].output, Output)
    assert loaded.results[0].meta == {"answerable": True}
    sc = loaded.rescore(spancheck.default_graders()).scorecard().by_grader()
    assert sc["citation_accuracy"]["pass_rate"] == 1.0
