"""Score the captured Kotaemon outputs with spancheck (offline, no network). Run from the spancheck repo root:

    PYTHONPATH=src python showcase/kotaemon/score.py
"""
from __future__ import annotations

import json
from pathlib import Path

from spancheck import Case, evaluate, default_graders, graders as G

ROOT = Path(__file__).resolve().parents[2]
cap = json.loads((ROOT / "showcase" / "kotaemon" / "capture.json").read_text(encoding="utf-8"))

by_input = {c["input"]: c["output"] for c in cap}
cases = [Case(c["id"], c["input"], c.get("category", "default"), c.get("expected"), c.get("meta") or {}) for c in cap]


def system(q):
    return by_input[q]  # replay the captured Kotaemon output; spancheck scores it offline


run = evaluate(cases, system, graders=default_graders() + [G.expected_contains()])
sc = run.scorecard()

audit = ROOT / "showcase" / "kotaemon" / "audit.json"
run.audit_log(str(audit))

print("Kotaemon × spancheck — healthcare corpus (21 cases, claude-sonnet-5, BM25 retrieval)\n")
print("Scorecard (by grader):")
for g, v in sc.by_grader().items():
    print(f"  {g:<20} pass_rate={v['pass_rate']:<6} score={v['score']:<6} n={v['n']}")
print("\nBy category (pass_rate):")
for cat, gr in sc.by_category().items():
    print(f"  {cat:<20} " + "  ".join(f"{k}={v}" for k, v in gr.items()))
print(f"\noverall pass rate: {sc.overall_pass_rate()}")
print(f"wrote {audit}")

print("\nFailures / notes:")
for cr, fs in sc.failures():
    for f in fs:
        print(f"  [{cr.case_id}] {f.grader}: {f.detail}")
