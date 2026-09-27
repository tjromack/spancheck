# spancheck — a citation-grade eval library for grounded-answer systems

**Shipped:** 2026-09 · **Demonstrates:** RAG evaluation · citation-span verification · calibrated LLM-as-judge · CI regression gating · library API design
**Lenses:** trustworthy AI · developer tooling · measure-before-claim
**Stack:** Python 3.11+, standard library only (zero hard dependencies), argparse CLI, a composite GitHub Action, `pytest`

---

## Overview

`spancheck` scores a grounded-answer system — any RAG or retrieval-then-answer pipeline — on the four things that decide
whether its answers can be trusted: **citation accuracy, abstention correctness, hallucination rate, and cost/latency**.
It runs offline, has no vendor lock-in, and emits a versioned audit log a compliance reviewer can read. It installs with
`pip`, runs as a three-command CLI, and drops into CI as a GitHub Action that fails a pull request on a regression.

It is the spinoff of an earlier project, the [LLM Evaluation & Guardrails
Harness](https://github.com/tjromack/llm-eval-guardrails-harness) — the version that proved the method against one real
target (a regulatory RAG copilot), with LLM-judge agreement of 1.00 on a human gold set. `spancheck` is that method
extracted from an in-repo lab, generalised to any corpus, and packaged so a stranger can point it at their own system.
What carried over, what was rewritten, and what changed is recorded in [`LINEAGE.md`](../LINEAGE.md).

## The problem

Teams shipping RAG can tell you their retriever's hit rate, but not whether the answer's *citations actually hold*. Two
failure modes slip through ordinary evals: an answer that cites a passage which does not support it (including the
insidious "right answer, wrong citation"), and an answer that should have said "I don't know" but didn't. Both destroy
the one thing a grounded system is supposed to provide — an auditable trail from claim to source. Measuring them needs
more than string overlap, and doing it credibly needs the eval itself to be trustworthy.

## Constraints

- **Deterministic-first.** Anything checkable by a rule is checked by a rule — no model in the loop, no drift, no cost.
  The LLM-judge is reserved for the one thing rules cannot do (entailment), and it is calibrated before it is trusted.
- **No vendor lock-in.** The library never hard-codes a model provider. A caller supplies a plain `input -> answer`
  callable; the judge reaches a model only through a caller-supplied provider, stubbed by default.
- **Every metric computable offline from a captured run.** Capture a run once — answers, contexts, citations, usage,
  latency — and re-score it any number of times without touching the system again.
- **No invented numbers.** Any figure in the docs is measured; where a number would have to be assumed (a per-token
  dollar cost), the tool reports a blank rather than a guess.

## Architecture

A small, layered, dependency-free package:

```
adapter.py   normalise any system's return into a typed Output {answer, contexts, citations, usage, latency_ms}
core.py      Case / evaluate / Run / Scorecard / diff / gate  (ported and generalised from the eval lab)
graders.py   deterministic graders: abstention, groundedness, PII-leak, latency, contains/regex, recall
span.py      citation-span verification — the capability the tool is named for
judge.py     the calibrated LLM-judge (entailment), prompts loaded from version-controlled files
audit.py     cost/latency aggregation + the versioned, compliance-readable audit log
cli.py       run / score / gate — thin wrappers over the library
```

**Citation verification** splits each citation into two deterministic checks, both of which must hold: **provenance**
(is the cited span present, verbatim, in the retrieved context? — catches a fabricated quote) and **support** (does the
span cover the claim? — catches a real-but-unsupporting citation). The default support check is a lexical proxy; the
opt-in judge upgrades it to true entailment, while provenance is always deterministic and never delegated to a model.

## Key decisions

- **Extract from the lab, not from the product.** Three eval codebases already existed in the portfolio; the most
  reusable was the dependency-free lab core, not the eval coupled to the product's pipeline. spancheck generalises the
  lab and adds the one genuinely new capability, citation-span verification.
- **Pin the output shape early.** Normalising every system return into one typed `Output` is what makes offline
  re-scoring, cost/latency accounting, and the audit log fall out for free instead of being bolted on later.
- **Prompts are version-controlled files, not inline strings.** A rubric change is a reviewable diff, and every judge
  verdict records the prompt version and model that produced it.
- **Name the limits in tests.** The lexical support proxy cannot see a contradiction that shares a claim's words; that
  false positive is pinned by a test and stated in the README, with the judge as the documented upgrade.

## How it's verified

Measured, not asserted. `spancheck` was run end-to-end against the real product pipeline as a black box (Suver's
answer-a-document tool on `claude-sonnet-5`, over its own sample contract), and the judge was calibrated against a
human-labelled gold set.

| What | Result |
|---|---|
| Dogfood: citation accuracy on a real pipeline | **1.00** — every cited span was real and supported its claim |
| Dogfood: hallucination (groundedness) | **0 hallucinations** (groundedness pass-rate 1.00) |
| Dogfood: abstention correctness | 11/12 — spancheck **caught one false-abstention** (the system declined an answerable, paraphrased question) |
| Dogfood: overall pass-rate across 12 cases | **0.967** |
| Judge calibration vs human gold set (stub) | 0.75 — a safe, zero-cost floor; no false positives |
| Judge calibration vs human gold set (claude-sonnet-5) | **1.00** (12/12) — closes exactly the paraphrase cases the stub missed |
| Test suite | **68 tests**, green on a clean `pip install` and in CI (Python 3.11 & 3.12) |

The single dogfood miss is the headline value: the eval found a real recall gap in a shipping system — not a spancheck
bug, a measured behaviour — which is what an eval is for.

## What I'd do differently

- **Scope citations to their named source.** A cited span found in *any* retrieved context currently passes; tying a
  citation to the specific document it names would tighten multi-document provenance.
- **Broaden the dogfood corpus.** One sample contract exercises the four case categories cleanly, but a larger,
  multi-document corpus would stress retrieval harder and surface more of the kind of gap the one miss hints at.

## Limits

- **Deterministic support is a lexical proxy.** It cannot see a span that shares a claim's words but contradicts it; the
  opt-in, calibrated judge is the upgrade for true entailment.
- **Provenance requires a verbatim quote.** A paraphrased citation fails by design — a deliberate incentive to quote
  sources exactly.
- **The metrics are only as good as the test set you bring.** spancheck scores a system against cases you author; it
  does not generate them.

## Closing

`spancheck` turns "our answers are grounded" from a claim into a number, with the eval itself held to the same standard
it applies: deterministic where it can be, calibrated where it can't, and honest about the seam between them. It reads
as the second chapter of a single story — a method proven against one system, then extracted into a tool anyone can run
against their own.

*MIT-licensed. `pip install spancheck` · Repository: https://github.com/tjromack/spancheck*
