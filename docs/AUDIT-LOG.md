# The spancheck audit log — schema v1.0

The audit log is what a reviewer reads to understand a run without re-running it. It is produced offline from a
captured run (`run.audit_log("audit.json")` or `spancheck.build_audit_log(run)`), so it needs no network and no second
call to the system under test.

**Versioning.** The top-level `schema_version` starts at `"1.0"`. A **breaking** change to this shape (a removed or
renamed field, a changed meaning) is a **major** version bump; additive fields are a minor bump (design pin #4). Read
`schema_version` before parsing.

## Top-level shape

```jsonc
{
  "schema_version": "1.0",
  "spancheck_version": "0.0.1",        // the library version that produced the log
  "created_at": "2026-09-26T00:00:00+00:00",
  "summary": {
    "n_cases": 3,
    "overall_pass_rate": 0.83,          // mean over all grades in the run
    "by_grader":   { "citation_accuracy": {"score": 0.67, "pass_rate": 0.67, "n": 3}, ... },
    "by_category": { "answerable": {"citation_accuracy": 1.0, ...}, "unanswerable": {...} },
    "latency": {
      "n": 3, "total_ms": 900.0, "mean_ms": 300.0,
      "p50_ms": 280.0, "p95_ms": 410.0, "max_ms": 410.0
    },
    "cost": {
      "input_tokens": 1200, "output_tokens": 300, "total_tokens": 1500,
      "cost_usd": null,                 // null unless pricing was supplied or usage carried explicit cost_usd
      "pricing_applied": false          // true only when a {input_per_1k, output_per_1k} table was passed
    }
  },
  "cases": [ /* one entry per case, see below */ ]
}
```

## Per-case entry

```jsonc
{
  "case_id": "q1",
  "category": "answerable",
  "input": "What is the notice period?",
  "expected": "30 days",                // the reference/label, if any
  "meta": { "answerable": true },       // enough to re-grade the case offline
  "error": null,                        // a repr string if the system/grader raised (the case still appears)
  "output": {
    "answer": "...", "contexts": ["..."], "citations": [ ... ],
    "usage": { "input_tokens": 400, "output_tokens": 100 },
    "latency_ms": 300.0, "abstained": null, "raw": ...
  },
  "grades": [
    { "grader": "citation_accuracy", "score": 1.0, "passed": true, "detail": "1/1 citations verified" },
    ...
  ],
  "citations": [                        // per-citation verdicts, recomputed from the cached output
    {
      "span": "Either party may terminate ... 30 days written notice",
      "span_found": true,               // (a) provenance: present verbatim in the contexts
      "claim_supported": true,          // (b) support: the span covers the claim (lexical proxy)
      "ok": true,
      "support": 1.0,                   // the coverage fraction behind claim_supported
      "reason": "verified: span present, covers 1.0 of the claim"
    }
  ]
}
```

## Notes

- **Cost is never invented.** `cost_usd` is `null` unless you passed a `pricing` table (then it is computed from token
  counts) or the system's `usage` already carried an explicit `cost_usd` (then those are summed). Prices drift and vary
  by contract, so spancheck does not ship a price constant.
- **The `citations` block is the compliance payload.** It is the deterministic "why" behind each answer's citation
  score — which spans were real, which supported their claim, and the reason each failed — recomputed from the cached
  output, not re-fetched.
- **A saved run round-trips.** `Run.load()` restores the `Output` and case metadata, so a loaded run can be re-graded
  (`Run.rescore(graders)`) or re-audited offline.
