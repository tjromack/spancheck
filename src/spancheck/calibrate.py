"""Calibrate the LLM-judge against a human-labelled gold set — a MEASURED agreement number, not an asserted one.

The judge is only trusted after this reports how often it agrees with human labels (AB-DEC 009). With no provider the
stub is measured (a deterministic baseline that catches negation but misses paraphrase — visible in the confusion
counts). The real number comes from a keyed run:

    python -m spancheck.calibrate --real --model claude-sonnet-5    # needs ANTHROPIC_API_KEY

Stdlib only. The gold set (calibration/entailment_gold.jsonl) is synthetic and public.
"""
from __future__ import annotations

import json

from .judge import judge_entailment


def calibrate_judge(gold, provider=None, prompt_version="entailment_v1", threshold=0.5, model=None):
    """Run the judge over labelled (claim, span, label) examples; return agreement + confusion + per-row detail."""
    tp = fp = tn = fn = correct = 0
    rows = []
    for ex in gold:
        v = judge_entailment(ex["claim"], ex["span"], provider=provider, prompt_version=prompt_version, model=model)
        pred = v["score"] >= threshold
        label = bool(ex["label"])
        ok = pred == label
        correct += int(ok)
        if pred and label:
            tp += 1
        elif pred and not label:
            fp += 1
        elif not pred and not label:
            tn += 1
        else:
            fn += 1
        rows.append({"claim": ex["claim"], "span": ex["span"], "label": label,
                     "score": v["score"], "pred": pred, "correct": ok, "reason": v["reason"]})
    n = len(gold)
    return {
        "n": n,
        "agreement": round(correct / n, 3) if n else 0.0,
        "threshold": threshold,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "model": model or ("stub" if provider is None else getattr(provider, "model", "unknown")),
        "prompt_version": prompt_version,
        "rows": rows,
    }


def load_gold(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv=None) -> int:
    import argparse
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    p = argparse.ArgumentParser(prog="spancheck.calibrate",
                                description="Measure judge-vs-human agreement on a gold set.")
    p.add_argument("--gold", default="calibration/entailment_gold.jsonl")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--real", action="store_true", help="use the Anthropic provider (needs ANTHROPIC_API_KEY)")
    p.add_argument("--model", default="claude-sonnet-5")
    a = p.parse_args(argv)

    from ._env import load_dotenv
    load_dotenv()  # pick up ANTHROPIC_API_KEY from a local .env if present (never overwrites a real env var)

    gold = load_gold(a.gold)
    provider = None
    model = None
    if a.real:
        from .provider import anthropic_provider
        provider = anthropic_provider(model=a.model)
        model = a.model

    r = calibrate_judge(gold, provider=provider, threshold=a.threshold, model=model)
    print(f"judge calibration — {r['model']} vs {r['n']} human-labelled cases (prompt {r['prompt_version']})")
    print(f"  agreement: {r['agreement']}   (threshold {r['threshold']})")
    c = r["confusion"]
    print(f"  confusion: tp={c['tp']}  fp={c['fp']}  tn={c['tn']}  fn={c['fn']}")
    for row in r["rows"]:
        mark = "ok" if row["correct"] else "XX"
        print(f"  [{mark}] label={str(row['label']):5} pred={str(row['pred']):5} score={row['score']:<5} "
              f"{row['claim'][:44]!r} ⟵ {row['span'][:44]!r}")
    if not a.real:
        print("\n(stub judge — a deterministic offline baseline. For the real agreement number: "
              "python -m spancheck.calibrate --real)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
