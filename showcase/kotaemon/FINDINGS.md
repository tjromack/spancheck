# Field report — spancheck × Kotaemon (healthcare corpus)

**What ran.** spancheck scored [Kotaemon](https://github.com/Cinnamon/kotaemon) (Apache-2.0, Cinnamon Labs) — a real,
published citation-RAG application — as a black box. Kotaemon's **own** `CitationPipeline` and QA prompt, on
`claude-sonnet-5`, answered and cited over our 5-document public healthcare corpus (Wikipedia, CC BY-SA), with a small
built-in BM25 supplying the retrieved context (the "(a)" design). 21 cases: answerable · a cross-document conflict ·
unanswerable (off-corpus) · adversarial (false-premise). Reproduce: `capture_kotaemon.py` (in Kotaemon's venv) →
`score.py` / `score_judged.py` (spancheck). Audit logs: `audit.json`, `audit_judged.json`.

The hero here is spancheck's generality, not Kotaemon's quality: this is a neutral, reproducible measurement on a small
authored set. Kotaemon is a strong project; the point is what a corpus-agnostic eval can *measure* on someone else's
real system.

## What spancheck measured

| Metric | Result | Reading |
|---|---|---|
| Overall pass-rate (21 cases) | **0.829** | |
| **Citation provenance + attribution** | **18/23 verbatim; 18/18 of those source-scoped to the exact document named (100%)** | The headline: spancheck verified Kotaemon's quotes against the *specific* source and got attribution 100% right — on a third-party system it had never seen. |
| Abstention — off-corpus | **5/5** | Kotaemon correctly declined every genuinely-off-corpus question. |
| Abstention — adversarial | 2/3 | It was misled by one false premise (below). |
| Hallucination (groundedness) | 0.952 pass | |
| PII leak | 1.00 | |
| Citation *support* — lexical proxy / LLM-judge | 0.286 / 0.429 | Both under-score — see the finding below. This is about spancheck's metric, not Kotaemon's quotes. |

## Findings

**1. Provenance + source-scoping port perfectly to a real third-party system.** Every verbatim quote Kotaemon produced
(18 of 23) was attributed to the correct source document — 18/18 source-scoped. spancheck's core check needed *no*
tuning to work on a system it had never seen. This is the empirical proof that the citation model is system-agnostic.

**2. spancheck caught a real defect the naive view would miss.** On `adv-hipaa-pa-rate` (a false-premise question
conflating HIPAA with prior-authorization rates), Kotaemon **answered instead of abstaining** *and* produced a
**fabricated citation** — an "evidence" quote that is **not verbatim in the retrieved context**. spancheck's provenance
check flagged it. (Separately, on four correctly-*abstained* off-corpus questions, Kotaemon's citation stage still
emitted a non-verbatim evidence string — moot, since the answer abstained, but a notable mismatch between its answer and
citation stages.)

**3. An honest finding about spancheck's *own* metric.** `citation_accuracy`'s support check under-scored (lexical
0.29, judge 0.43) — but the failures are all `unsupported`, not `fabricated`: the quotes are real and on-topic. The
cause is a design assumption: spancheck's support check judges each citation against the citation's *claim*, which
defaults to the **whole answer**. Kotaemon answers *in detail* and attaches a few short, answer-level evidence quotes
(not per-claim citations), so "does this 15-word quote support the entire paragraph?" scores low — even for the LLM
judge. The dogfood scored 1.00 precisely because its citations were **claim-scoped**. The fair metric for
answer-level-citation systems is **provenance + attribution** (finding 1); claim-splitting, or a `provenance-only`
support mode, is the enhancement this run surfaced.

## What it does *not* claim

A verdict on Kotaemon's quality (21 authored cases, one corpus, one retrieval choice), or a benchmark. It is one field
report showing that spancheck's provenance/attribution checks are portable and catch real issues on an independent
real-world system — and honest enough to surface an assumption in its own support metric.
