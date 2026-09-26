# spancheck

> © 2026 Trevor J. Romack — **source-available for review, not open-source** ([LICENSE](LICENSE)). No reuse or
> commercial use without permission. · tjromack@gmail.com

**Score a grounded-answer system on citation accuracy, abstention correctness, hallucination rate, cost and latency —
and get an audit log a compliance reviewer can read.**

`spancheck` is an installable, corpus-agnostic evaluation library for RAG and retrieval-then-answer pipelines. Point it
at any system through a thin adapter, give it a test set, and it produces a scorecard on the four metrics that decide
whether the system's answers can be trusted — plus a versioned audit log that reconstructs *why* each answer passed or
failed.

Library first, CLI second, GitHub Action third: the Python API is the product; the command line and the Action are thin
wrappers over it.

---

## The four metrics

| Metric | Question it answers | How it's scored |
|---|---|---|
| **Citation accuracy** | Does the cited span actually support the claim? | Deterministic span check *(the capability built first and tested deepest)* |
| **Abstention correctness** | Does it decline when the answer isn't in the corpus, and answer when it is? | Deterministic |
| **Hallucination rate** | What share of answers assert something the retrieved context doesn't support? | Deterministic groundedness + calibrated LLM-judge for the qualitative residue |
| **Cost & latency** | Tokens / dollars / wall-clock per answer, against a budget | Deterministic, from a cached run — no network |

## Status

**Phase 1 shipped — the measurement core runs.** `Case` / `evaluate` / `Run` / `Scorecard` / `diff` / `gate`, the thin
`adapter` contract, and the deterministic graders (abstention correctness, a groundedness/hallucination proxy, PII-leak,
latency) are implemented, dependency-free, and tested (22 tests, verified from a clean `pip install -e .`). Still to
come per `TODO.md`: **citation-span verification** (Phase 2 — the capability this build exists to add), the **versioned
audit log** (Phase 3), and the **calibrated LLM-judge** (Phase 4).

No benchmark numbers appear here yet: they arrive when `spancheck` is run end-to-end against a real target (Phase 6).
Until measured, any figure would be invented, and this project does not ship invented numbers (see `CLAUDE.md`).

## Lineage

`spancheck` is the spinoff of [`llm-eval-guardrails-harness`](https://github.com/tjromack/llm-eval-guardrails-harness) —
the version that proved the method against a single real target (a regulatory RAG copilot), with LLM-judge agreement
1.00 against a human gold set. This package is the same method, extracted from an in-repo lab, generalised to any
corpus, and packaged so a stranger can install it and point it at their own system. What carried over unchanged, what
was rewritten and why, and what the harness got wrong that this fixes are recorded in [`LINEAGE.md`](LINEAGE.md).

## Quickstart

> The Phase-1 core below runs today (`pip install -e .`). Lines marked *(Phase 3)* / *(Phase 2)* are the intended shape
> of what those phases add; see `Status` and `TODO.md`.

```python
from spancheck import Case, evaluate, adapter

# 1. Wrap your system in a thin adapter: input -> {answer, contexts, citations, usage, latency_ms}
#    (optional — evaluate() also accepts a plain input->answer callable and times it for you)
my_system = adapter(lambda q: my_rag_pipeline(q))

# 2. Describe your test set — answerable, unanswerable, and adversarial cases
cases = [
    Case(id="q1", input="What is the notice period?", category="answerable",
         expected="30 days", meta={"answerable": True}),
    Case(id="q2", input="What is the company's revenue?", category="unanswerable",
         meta={"answerable": False}),  # should abstain
]

# 3. Score it — a run is captured once, then the metrics compute offline
run = evaluate(cases, my_system)
print(run.scorecard().by_grader())   # abstention correctness, groundedness, PII-leak (+ citation accuracy in Phase 2)
run.save("run.json")                 # persist a run for baselines / regression gating
# run.audit_log("audit.json")        # the versioned, compliance-readable record — Phase 3
```

```bash
# CLI (thin wrapper over the same API)
spancheck run cases.jsonl --target my_module:my_system --out audit.json
spancheck score audit.json        # recompute metrics from a cached run, no network
```

## Design pins

- **Library-first, CLI-second** — the API is the product.
- **No provider lock-in** — a thin adapter from day one; stub by default, any model behind a callable.
- **Every metric computable without network given a cached run** — capture once, re-score offline.
- **The audit-log schema is versioned** — a breaking change is a major version bump; it's a contract with a reviewer.
- **Judge prompts live in version-controlled files** — a rubric change is a reviewable, version-stamped diff.
- **No dependency on any other project's internals** — standalone; dogfooded as a black box, never coupled.

## License

Source-available for evaluation only. See [LICENSE](LICENSE). Not open-source: no reuse, redistribution, deployment, or
commercial use without written permission.
