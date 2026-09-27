"""Dogfood: score Suver's real answer-a-document pipeline with spancheck, as a black box.

This runs Suver's *actual* pipeline (`app.pipeline.answer_question`) on the real Anthropic model over Suver's own
sample contract, mapping each answer into spancheck's Output contract, then scores it. spancheck never imports Suver's
internals for grading — it only calls the pipeline through an adapter and reads {answer, contexts, citations}.

Requires: `project-suver` checked out next to `spancheck` (../project-suver) and an ANTHROPIC_API_KEY in spancheck/.env.
Run from the spancheck repo root:

    python dogfood/run_dogfood.py

Writes dogfood/suver_audit.json and prints the scorecard. This is evidence-generation, not a package feature — it is
the one place spancheck knowingly reaches into a sibling repo (guarded behind this script, never in the library).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SPANCHECK_ROOT = Path(__file__).resolve().parents[1]
SUVER_ROOT = SPANCHECK_ROOT.parent / "project-suver"
sys.path.insert(0, str(SPANCHECK_ROOT / "src"))
sys.path.insert(0, str(SUVER_ROOT))

# Load the key BEFORE importing Suver — its settings pick the real provider only if the key is already in the env.
from spancheck._env import load_dotenv  # noqa: E402
load_dotenv(str(SPANCHECK_ROOT / ".env"))

import os  # noqa: E402
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise SystemExit("No ANTHROPIC_API_KEY found (put it in spancheck/.env). Aborting — the dogfood needs the real model.")

from spancheck import Case, evaluate, default_graders, graders as G  # noqa: E402
from app.pipeline import answer_question  # noqa: E402  (Suver, as a black box)

# Suver's own sample corpus (the Copilot tool's sample_text) — the "real material" for the dogfood.
MSA = ("MASTER SERVICES AGREEMENT. The initial term is two years, beginning January 1, 2026. The "
       "agreement auto-renews for successive one-year terms unless either party gives sixty (60) days "
       "written notice. Fees are $12,000 per month, net thirty days. Governing law is the State of New York.")


def suver_target(query: str) -> dict:
    """Adapter: run Suver's real pipeline on the fixed corpus, map its AnswerResult to spancheck's Output shape."""
    r = answer_question(MSA, query, provider="anthropic")
    if getattr(r, "blocked", False):
        return {"answer": r.block_message or "[blocked]", "contexts": [MSA], "abstained": True,
                "raw": {"provider": r.provider, "blocked": True}}
    if not r.answered:
        return {"answer": r.answer or getattr(r, "abstain_reason", "") or "not in the document",
                "contexts": [MSA], "abstained": True, "raw": {"provider": r.provider, "answered": False}}
    cites = [{"span": c.span_text, "claim": c.text} for c in (r.citations or [])]
    return {"answer": r.answer, "contexts": [MSA], "citations": cites, "abstained": False,
            "raw": {"provider": r.provider, "support": [c.support for c in (r.citations or [])]}}


def load_cases(path):
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        cases.append(Case(d["id"], d["input"], d.get("category", "default"), d.get("expected"), d.get("meta") or {}))
    return cases


def main():
    cases = load_cases(SPANCHECK_ROOT / "dogfood" / "suver_cases.jsonl")
    # Default deterministic graders + recall on the answerable cases (expected_contains auto-passes where no expected).
    grds = default_graders() + [G.expected_contains()]  # +recall on the answerable cases
    print(f"Dogfooding spancheck against Suver's real pipeline — {len(cases)} cases on claude-sonnet-5 ...\n")
    run = evaluate(cases, suver_target, graders=grds)

    # Sanity: confirm we actually hit the real model, not a stub.
    providers = {(cr.output.raw or {}).get("provider") for cr in run.results if cr.output and cr.output.raw}
    print(f"provider(s) used by the target: {providers}")

    out = SPANCHECK_ROOT / "dogfood" / "suver_audit.json"
    doc = run.audit_log(str(out))
    sc = run.scorecard()
    print("\nScorecard (by grader):")
    for g, v in sc.by_grader().items():
        print(f"  {g:<20} pass_rate={v['pass_rate']:<6} score={v['score']:<6} n={v['n']}")
    print("\nBy category (pass_rate):")
    for cat, gr in sc.by_category().items():
        print(f"  {cat:<14} " + "  ".join(f"{k}={v}" for k, v in gr.items()))
    print(f"\noverall pass rate: {sc.overall_pass_rate()}")
    print(f"wrote {out}")

    # Print any failures so a real miss is visible, not hidden.
    fails = sc.failures()
    if fails:
        print("\nFailures / notes:")
        for cr, fs in fails:
            for f in fs:
                print(f"  [{cr.case_id}] {f.grader}: {f.detail}")


if __name__ == "__main__":
    main()
