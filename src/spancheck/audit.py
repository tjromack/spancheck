"""Cost/latency aggregation and the versioned, compliance-readable audit log (Phase 3).

Everything here is computed **offline** from a captured run — no system call, no network (design pin #3). The audit
log is a contract with a reviewer: its shape is versioned (`schema_version`), and a breaking change to it is a major
version bump (design pin #4). The schema is documented in docs/AUDIT-LOG.md.

Stdlib only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .adapter import Output
from .span import verify_citation

# Bump the MAJOR component only on a breaking change to the audit-log shape (design pin #4).
SCHEMA_VERSION = "1.0"


def _percentile(sorted_vals, pct):
    """Nearest-rank percentile on an already-sorted list. Handles n=1. pct in [0,100]."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = max(0, min(len(sorted_vals) - 1, round((pct / 100.0) * (len(sorted_vals) - 1))))
    return sorted_vals[k]


def cost_latency(run, pricing=None):
    """Aggregate cost and latency from a run's captured outputs.

    latency: total / mean / p50 / p95 / max (ms), over cases that recorded a latency.
    cost: summed input/output/total tokens and any explicit `cost_usd` in usage. If `pricing`
    ({"input_per_1k", "output_per_1k"}) is given, a dollar cost is computed from tokens; otherwise
    `cost_usd` is only the sum of explicit per-call costs (or None if none were provided).
    """
    lats, in_tok, out_tok, tot_tok, explicit_cost = [], 0, 0, 0, []
    for cr in run.results:
        out = cr.output
        if not isinstance(out, Output):
            continue
        if out.latency_ms is not None:
            lats.append(out.latency_ms)
        u = out.usage or {}
        in_tok += int(u.get("input_tokens", 0) or 0)
        out_tok += int(u.get("output_tokens", 0) or 0)
        tot_tok += int(u.get("total_tokens", 0) or (int(u.get("input_tokens", 0) or 0) + int(u.get("output_tokens", 0) or 0)))
        if "cost_usd" in u and u["cost_usd"] is not None:
            explicit_cost.append(float(u["cost_usd"]))

    lats_sorted = sorted(lats)
    latency = {
        "n": len(lats),
        "total_ms": round(sum(lats), 3) if lats else None,
        "mean_ms": round(sum(lats) / len(lats), 3) if lats else None,
        "p50_ms": _percentile(lats_sorted, 50),
        "p95_ms": _percentile(lats_sorted, 95),
        "max_ms": max(lats) if lats else None,
    }

    cost_usd = None
    if pricing:
        cost_usd = round(
            (in_tok / 1000.0) * float(pricing.get("input_per_1k", 0.0))
            + (out_tok / 1000.0) * float(pricing.get("output_per_1k", 0.0)),
            6,
        )
    elif explicit_cost:
        cost_usd = round(sum(explicit_cost), 6)

    cost = {
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": tot_tok,
        "cost_usd": cost_usd,                # None when no pricing and no explicit cost was supplied (not invented)
        "pricing_applied": bool(pricing),
    }
    return {"latency": latency, "cost": cost}


def _citation_verdicts(out: Output):
    """Per-citation verdicts recomputed from the cached output — the 'why' a reviewer needs."""
    verdicts = []
    for c in (out.citations or []):
        v = verify_citation(c, out.contexts, out.answer, sources=out.sources)
        verdicts.append({
            "span": v.span, "source_id": v.source_id, "scoped": v.scoped,
            "span_found": v.span_found, "claim_supported": v.claim_supported,
            "ok": v.ok, "support": v.support, "reason": v.reason,
        })
    return verdicts


def build_audit_log(run, path=None, *, pricing=None, verify_citations=True, spancheck_version=None):
    """Build the versioned audit log (a superset of Run.to_dict). Writes JSON to `path` if given; returns the dict."""
    if spancheck_version is None:
        from . import __version__ as spancheck_version

    sc = run.scorecard()
    cases = []
    for cr in run.results:
        out = cr.output
        entry = {
            "case_id": cr.case_id,
            "category": cr.category,
            "input": cr.input,
            "expected": cr.expected,
            "meta": cr.meta,
            "error": cr.error,
            "output": cr.output_dict(),
            "grades": [{"grader": g.grader, "score": g.score, "passed": g.passed, "detail": g.detail}
                       for g in cr.grades],
            "citations": _citation_verdicts(out) if (verify_citations and isinstance(out, Output)) else [],
        }
        cases.append(entry)

    doc = {
        "schema_version": SCHEMA_VERSION,
        "spancheck_version": spancheck_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "n_cases": len(run.results),
            "overall_pass_rate": sc.overall_pass_rate(),
            "by_grader": sc.by_grader(),
            "by_category": sc.by_category(),
            **cost_latency(run, pricing=pricing),
        },
        "cases": cases,
    }

    if path is not None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
    return doc
