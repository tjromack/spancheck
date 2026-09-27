"""spancheck CLI — a thin wrapper over the library (design pin #1: library-first, CLI-second).

Three commands, each a few lines over the Python API:

    spancheck run   cases.jsonl --target module:callable --out audit.json   # run a system, write an audit log
    spancheck score audit.json                                             # recompute metrics from a cached run
    spancheck gate  audit.json citation_accuracy=1.0 [--baseline base.json] # pass/fail for CI (exit 1 on fail)

`run` and `score` never touch the network beyond whatever the target itself does; `score` and `gate` are fully offline.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys

from . import __version__
from .core import Case, Run, evaluate, gate, default_graders


def _load_cases(path):
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            cases.append(Case(d.get("id") or d.get("case_id"), d.get("input"),
                              d.get("category", "default"), d.get("expected"), d.get("meta") or {}))
    return cases


def _load_target(spec):
    """Load a system callable from a 'module:attribute' spec (imports arbitrary user code, like a test runner)."""
    if ":" not in spec:
        raise SystemExit(f"--target must be 'module:callable', got {spec!r}")
    mod_name, attr = spec.split(":", 1)
    obj = importlib.import_module(mod_name)
    for part in attr.split("."):
        obj = getattr(obj, part)
    return obj


def _pricing(a):
    if getattr(a, "price_in", None) is None and getattr(a, "price_out", None) is None:
        return None
    return {"input_per_1k": a.price_in or 0.0, "output_per_1k": a.price_out or 0.0}


def _print_summary(doc):
    s = doc["summary"]
    print(f"cases: {s['n_cases']}   overall pass rate: {s['overall_pass_rate']}")
    for g, v in s["by_grader"].items():
        print(f"  {g:<20} pass_rate={v['pass_rate']}  score={v['score']}  n={v['n']}")
    lat, cost = s["latency"], s["cost"]
    print(f"  latency: mean={lat['mean_ms']}ms  p95={lat['p95_ms']}ms   "
          f"tokens={cost['total_tokens']}  cost_usd={cost['cost_usd']}")


def cmd_run(a):
    cases = _load_cases(a.cases)
    system = _load_target(a.target)
    run = evaluate(cases, system)
    doc = run.audit_log(a.out, pricing=_pricing(a))
    print(f"wrote {a.out}")
    _print_summary(doc)
    return 0


def cmd_score(a):
    run = Run.from_audit_log(a.audit)
    if a.regrade:
        run = run.rescore(default_graders())  # re-grade cached outputs offline, no system call
    _print_summary(run.audit_log(pricing=_pricing(a)))
    return 0


def cmd_gate(a):
    run = Run.from_audit_log(a.audit)
    thresholds = {}
    for t in a.thresholds:
        k, _, v = t.partition("=")
        if not _:
            raise SystemExit(f"threshold must be 'grader=min_pass_rate', got {t!r}")
        thresholds[k] = float(v)
    baseline = Run.from_audit_log(a.baseline) if a.baseline else None
    ok, reasons = gate(run, thresholds, baseline=baseline, max_regression=a.max_regression)
    if ok:
        print("gate: PASS")
    else:
        print("gate: FAIL")
        for r in reasons:
            print("  - " + r)
    return 0 if ok else 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spancheck",
        description="Score a grounded-answer system on citation accuracy, abstention correctness, "
                    "hallucination rate, cost and latency — with a compliance-readable audit log.",
    )
    p.add_argument("--version", action="version", version=f"spancheck {__version__}")
    sub = p.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run a test set against a target and write an audit log")
    run.add_argument("cases", help="path to the cases file (JSONL: one {id,input,category?,expected?,meta?} per line)")
    run.add_argument("--target", required=True, help="module:callable adapter for the system under test")
    run.add_argument("--out", default="audit.json", help="where to write the audit log")
    run.add_argument("--price-in", type=float, default=None, help="USD per 1k input tokens (enables cost)")
    run.add_argument("--price-out", type=float, default=None, help="USD per 1k output tokens (enables cost)")
    run.set_defaults(func=cmd_run)

    score = sub.add_parser("score", help="recompute metrics from a cached audit log (no network)")
    score.add_argument("audit", help="path to a captured audit log")
    score.add_argument("--regrade", action="store_true", help="re-run the default graders on the cached outputs")
    score.add_argument("--price-in", type=float, default=None)
    score.add_argument("--price-out", type=float, default=None)
    score.set_defaults(func=cmd_score)

    g = sub.add_parser("gate", help="pass/fail a run against thresholds (exit 1 on fail; for CI)")
    g.add_argument("audit", help="path to a captured audit log")
    g.add_argument("thresholds", nargs="*", help="grader=min_pass_rate (e.g. citation_accuracy=1.0 groundedness=0.9)")
    g.add_argument("--baseline", default="", help="optional baseline audit log for regression gating")
    g.add_argument("--max-regression", type=float, default=0.0, help="max allowed pass_rate drop vs baseline")
    g.set_defaults(func=cmd_gate)
    return p


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    from ._env import load_dotenv
    load_dotenv()  # a target that calls a model can read its key from a local .env (never overwrites a real env var)
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
