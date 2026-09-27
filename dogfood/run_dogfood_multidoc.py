"""Multi-document dogfood: score Suver's real `ask_across` (its N-document tool) with spancheck, as a black box.

This is the messier, cross-referenced sibling of run_dogfood.py: a four-document corpus (a Master Services Agreement,
an Amendment that supersedes parts of it, a Statement of Work, and a Data Processing Addendum) with deliberate
conflicts. Each per-document answer becomes a spancheck citation tagged with its source_id, so provenance is scored
**source-scoped** — a span attributed to the wrong document fails even if it exists elsewhere in the corpus.

Requires: `project-suver` next to `spancheck` and an ANTHROPIC_API_KEY in spancheck/.env. Run from the repo root:

    python dogfood/run_dogfood_multidoc.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SPANCHECK_ROOT = Path(__file__).resolve().parents[1]
SUVER_ROOT = SPANCHECK_ROOT.parent / "project-suver"
sys.path.insert(0, str(SPANCHECK_ROOT / "src"))
sys.path.insert(0, str(SUVER_ROOT))

from spancheck._env import load_dotenv  # noqa: E402
load_dotenv(str(SPANCHECK_ROOT / ".env"))

import os  # noqa: E402
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise SystemExit("No ANTHROPIC_API_KEY (put it in spancheck/.env). The dogfood needs the real model.")

from spancheck import Case, evaluate, default_graders, graders as G  # noqa: E402
from app.pipeline import ask_across  # noqa: E402  (Suver's N-document tool, as a black box)

CORPUS_DIR = SPANCHECK_ROOT / "dogfood" / "corpus"
DOC_FILES = ["msa.txt", "amendment.txt", "sow1.txt", "dpa.txt"]
DOC_LABELS = {"msa.txt": "MSA", "amendment.txt": "Amendment No. 1", "sow1.txt": "SOW No. 1",
              "dpa.txt": "Data Processing Addendum"}

SOURCES = {DOC_LABELS[f]: (CORPUS_DIR / f).read_text(encoding="utf-8") for f in DOC_FILES}
DOCS = [(label, text) for label, text in SOURCES.items()]  # (name, text) as ask_across expects


def suver_target(query: str) -> dict:
    """Run Suver's real ask_across over the corpus; map the per-document answers to spancheck's Output shape,
    tagging each citation with the document it came from so provenance is scored source-scoped."""
    outcome = ask_across(DOCS, query, provider="anthropic")
    if getattr(outcome, "blocked", False):
        return {"answer": outcome.block_message or "[blocked]", "contexts": list(SOURCES.values()),
                "sources": SOURCES, "abstained": True, "raw": {"provider": outcome.provider, "blocked": True}}
    if not outcome.answered:
        return {"answer": outcome.summary_line, "contexts": list(SOURCES.values()), "sources": SOURCES,
                "abstained": True, "raw": {"provider": outcome.provider, "n_answered": 0}}
    parts, citations = [], []
    for da in outcome.per_doc:
        if da.answered and da.answer:
            parts.append(f"[{da.doc}] {da.answer}")
            for c in (da.citations or []):
                citations.append({"span": c.span_text, "claim": c.text, "source_id": da.doc})
    return {"answer": "  ".join(parts), "contexts": list(SOURCES.values()), "sources": SOURCES,
            "citations": citations, "abstained": False,
            "raw": {"provider": outcome.provider, "source_docs": list(outcome.source_docs)}}


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
    cases = load_cases(SPANCHECK_ROOT / "dogfood" / "suver_multidoc_cases.jsonl")
    grds = default_graders() + [G.expected_contains()]
    print(f"Multi-doc dogfood — Suver ask_across over {len(SOURCES)} documents, {len(cases)} cases on "
          f"claude-sonnet-5 ...\n")
    run = evaluate(cases, suver_target, graders=grds)

    providers = {((cr.output.raw or {}).get("provider")) for cr in run.results if cr.output and cr.output.raw}
    print(f"provider(s) used by the target: {providers}")

    out = SPANCHECK_ROOT / "dogfood" / "suver_multidoc_audit.json"
    run.audit_log(str(out))
    sc = run.scorecard()
    print("\nScorecard (by grader):")
    for g, v in sc.by_grader().items():
        print(f"  {g:<20} pass_rate={v['pass_rate']:<6} score={v['score']:<6} n={v['n']}")
    print("\nBy category (pass_rate):")
    for cat, gr in sc.by_category().items():
        print(f"  {cat:<20} " + "  ".join(f"{k}={v}" for k, v in gr.items()))
    print(f"\noverall pass rate: {sc.overall_pass_rate()}")
    print(f"wrote {out}")

    fails = sc.failures()
    if fails:
        print("\nFailures / notes:")
        for cr, fs in fails:
            for f in fs:
                print(f"  [{cr.case_id}] {f.grader}: {f.detail}")


if __name__ == "__main__":
    main()
