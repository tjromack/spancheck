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

Measured, not asserted. `spancheck` was run end-to-end against the real product pipeline as a black box (a grounded
answer tool on `claude-sonnet-5`), and the judge was calibrated against a human-labelled gold set. Two dogfood runs: a
single tidy contract, and a messy four-document corpus (a Master Services Agreement, a superseding Amendment, a
Statement of Work, and a Data Processing Addendum) with deliberate cross-document conflicts.

| What | Result |
|---|---|
| Single-doc dogfood: overall pass-rate (12 cases) | **0.967** — spancheck **caught one false-abstention** (the system declined an answerable, paraphrased question) |
| Multi-doc dogfood: overall pass-rate (21 cases, 4 conflicting documents) | **1.00** |
| Multi-doc: source-scoped citation accuracy | **47/47** citations verified against the specific document they named — both sides of each conflict (base agreement *and* amendment) cited correctly |
| Hallucination (groundedness), both runs | **0 hallucinations** |
| Judge calibration vs human gold set — stub / claude-sonnet-5 | 0.75 (a zero-cost floor, no false positives) / **1.00** (12/12) — closing exactly the paraphrase cases the stub missed |
| Test suite | **71 tests**, green on a clean `pip install` and in CI (Python 3.11 & 3.12) |

The single-doc miss is the headline value of an eval: it found a real recall gap in a shipping system — not a spancheck
bug, a measured behaviour. The multi-doc run is the harder test — messy, conflicting, cross-referenced input, scored
with **source-scoped provenance** (a span attributed to the wrong document fails even if it exists elsewhere) — and it
confirms the system attributes every claim to the right source.

### Beyond the dogfood: a real third-party system

Dogfooding proves the method; the claim that spancheck is *system-agnostic* only holds if it works on something it
didn't design for. So it was pointed at [Kotaemon](https://github.com/Cinnamon/kotaemon) — a real, published,
Apache-2.0 citation-RAG application — as a black box: Kotaemon's own citation pipeline and QA prompt, on
`claude-sonnet-5`, over a public healthcare corpus (21 cases). Three things came out of it, all honest:

- **Provenance and attribution ported with zero tuning.** Of Kotaemon's verbatim citations, **18/18 were source-scoped
  to the exact document they named** — spancheck verified a system it had never seen and got attribution 100% right.
- **It caught a real defect.** On an adversarial false-premise question, Kotaemon answered instead of abstaining and
  produced a **fabricated (non-verbatim) citation**; spancheck's provenance check flagged it.
- **It surfaced an assumption in its own metric — and a fix followed.** The support score under-scored (0.29 lexical,
  0.43 judged) because Kotaemon emits a *detailed answer with short, answer-level* evidence quotes, while spancheck's
  support check judged each quote against the *whole* answer — it was calibrated for *claim-scoped* citations. Adding an
  opt-in `claim_split` (score support against the answer sentence a span is most relevant to) moved the same run
  **0.286 → 0.762**, with the remaining failures being the genuinely fabricated citations. Using the tool on a system it
  didn't design for improved the tool.

Full write-up: [`showcase/kotaemon/FINDINGS.md`](../showcase/kotaemon/FINDINGS.md).

## What I'd do differently

- **A second real target beyond one product.** Both dogfoods score the same pipeline; a second, differently-built target
  would show the adapter generalising in public rather than in principle.
- **Push the judge past a 12-item gold set.** The real judge scored 12/12; a larger held-out slice where it is
  *sometimes* wrong would make the "reports its own judge's error rate" story sharper — though that edges into
  benchmark territory, which is deliberately out of scope here.

## Limits

- **Deterministic support is a lexical proxy.** It cannot see a span that shares a claim's words but contradicts it; the
  opt-in, calibrated judge is the upgrade for true entailment.
- **Provenance requires a verbatim quote.** A paraphrased citation fails by design — a deliberate incentive to quote
  sources exactly.
- **Source-scoping needs per-source text.** Attribution is checked against the named document only when the caller
  supplies a `{source_id: text}` map; otherwise provenance falls back to all retrieved contexts.
- **The metrics are only as good as the test set you bring.** spancheck scores a system against cases you author; it
  does not generate them. It is not a general-purpose eval platform, and not a benchmark.

## Closing

`spancheck` turns "our answers are grounded" from a claim into a number, with the eval itself held to the same standard
it applies: deterministic where it can be, calibrated where it can't, and honest about the seam between them. It reads
as the second chapter of a single story — a method proven against one system, then extracted into a tool anyone can run
against their own.

*MIT-licensed. `pip install spancheck` · Repository: https://github.com/tjromack/spancheck*
