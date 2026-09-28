"""Re-score Kotaemon's citations with the opt-in LLM-judge (entailment) — the documented upgrade over the lexical
support proxy — to show the difference on a real third-party system. Keyed run (a judge call per citation).

    PYTHONPATH=src python showcase/kotaemon/score_judged.py
"""
from __future__ import annotations

import json
from pathlib import Path

from spancheck import Run, citation_accuracy, judge_support
from spancheck._env import load_dotenv
from spancheck.provider import anthropic_provider

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(str(ROOT / ".env"))

run = Run.from_audit_log(str(ROOT / "showcase" / "kotaemon" / "audit.json"))

det = run.scorecard().by_grader()["citation_accuracy"]["pass_rate"]

provider = anthropic_provider(model="claude-sonnet-5")
judged = run.rescore([citation_accuracy(support_fn=judge_support(provider=provider))])
jud = judged.scorecard().by_grader()["citation_accuracy"]["pass_rate"]

print(f"citation_accuracy — deterministic lexical proxy: {det}")
print(f"citation_accuracy — opt-in LLM-judge (entailment): {jud}")
print("\nby category (judged):")
for cat, gr in judged.scorecard().by_category().items():
    if "citation_accuracy" in gr:
        print(f"  {cat:<20} citation_accuracy={gr['citation_accuracy']}")

judged.audit_log(str(ROOT / "showcase" / "kotaemon" / "audit_judged.json"))
print("\nwrote showcase/kotaemon/audit_judged.json")
