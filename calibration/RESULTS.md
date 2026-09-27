# Judge calibration — results

Measured judge-vs-human agreement on the 12-case gold set (`entailment_gold.jsonl`), prompt `entailment_v1`,
threshold 0.5. Re-runnable: `python -m spancheck.calibrate [--real]`.

| Judge | Agreement | Confusion (tp/fp/tn/fn) | Notes |
|---|---|---|---|
| **stub** (deterministic, offline) | **0.75** (9/12) | 4 / 0 / 5 / 3 | Catches negation + lexical/reordered support; misses the 3 meaning-level paraphrase/morphology cases (twenty≈20, renew≈renews, governed≈governing law). No false positives. |
| **claude-sonnet-5** (real) | **1.00** (12/12) | 7 / 0 / 5 / 0 | Gets every case, including the 3 the stub missed (scored 0.95–0.97). No false positives, no false negatives. — run 2026-09-27 |

**Reading it:** the deterministic stub is a safe, zero-cost floor (it never *wrongly affirms* — 0 false positives — it just can't see paraphrase). The real model closes that gap exactly, which is why the judge is the opt-in *entailment* upgrade over the lexical support proxy. The judge is trusted only because this number is measured, not asserted.
