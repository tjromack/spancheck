"""Phase 5: the CLI (run / score / gate) — thin wrappers over the library, driven against the shipped demo target.

Uses `spancheck.demo:system` so the CLI is exercised end-to-end with no user code and no key — the same command a
reader runs from a clean clone.
"""
from __future__ import annotations

import json

import pytest

from spancheck.cli import main
from spancheck.core import Run

CASES = "examples/cases.jsonl"
TARGET = "spancheck.demo:system"


def test_run_writes_a_valid_audit_log(tmp_path):
    out = tmp_path / "audit.json"
    rc = main(["run", CASES, "--target", TARGET, "--out", str(out)])
    assert rc == 0 and out.exists()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "1.0"
    assert doc["summary"]["n_cases"] == 3
    # the demo answers two and abstains on one, all with valid/absent citations
    assert doc["summary"]["by_grader"]["citation_accuracy"]["pass_rate"] == 1.0


def test_run_with_pricing_computes_cost(tmp_path):
    out = tmp_path / "audit.json"
    main(["run", CASES, "--target", TARGET, "--out", str(out), "--price-in", "3.0", "--price-out", "15.0"])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["cost"]["cost_usd"] is not None and doc["summary"]["cost"]["pricing_applied"] is True


def test_score_reads_a_cached_log_offline(tmp_path, capsys):
    out = tmp_path / "audit.json"
    main(["run", CASES, "--target", TARGET, "--out", str(out)])
    rc = main(["score", str(out)])
    assert rc == 0
    printed = capsys.readouterr().out
    assert "overall pass rate" in printed and "citation_accuracy" in printed


def test_gate_passes_and_fails_with_exit_codes(tmp_path):
    out = tmp_path / "audit.json"
    main(["run", CASES, "--target", TARGET, "--out", str(out)])
    assert main(["gate", str(out), "citation_accuracy=1.0", "abstention_correct=1.0"]) == 0
    assert main(["gate", str(out), "groundedness=1.01"]) == 1  # impossible threshold -> fail -> exit 1


def test_gate_baseline_regression(tmp_path):
    # baseline is the clean demo run; a doctored "current" with a failing grade must trip the regression gate
    base = tmp_path / "base.json"
    main(["run", CASES, "--target", TARGET, "--out", str(base)])
    cur = json.loads(base.read_text(encoding="utf-8"))
    cur["cases"][0]["grades"] = [{"grader": "citation_accuracy", "score": 0.0, "passed": False, "detail": "regressed"}]
    curp = tmp_path / "cur.json"
    curp.write_text(json.dumps(cur), encoding="utf-8")
    rc = main(["gate", str(curp), "--baseline", str(base)])
    assert rc == 1


def test_bad_target_spec_errors():
    with pytest.raises(SystemExit):
        main(["run", CASES, "--target", "not_a_valid_spec", "--out", "x.json"])


def test_from_audit_log_round_trips(tmp_path):
    out = tmp_path / "audit.json"
    main(["run", CASES, "--target", TARGET, "--out", str(out)])
    run = Run.from_audit_log(str(out))
    assert len(run.results) == 3
    assert run.scorecard().by_grader()["citation_accuracy"]["pass_rate"] == 1.0
