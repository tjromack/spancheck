# Evaluating in the wild — pointing a citation-grade eval at systems I didn't build

**Shipped:** 2026-09 · **Demonstrates:** third-party system integration · RAG evaluation on real tools · honest failure analysis · a tool improved by using it
**Lenses:** trustworthy AI · developer tooling · forward-deployed engineering
**Stack:** [spancheck](https://github.com/tjromack/spancheck) (Python), Docker, `uv`, Anthropic `claude-sonnet-5`, public data only

---

## Overview

Building an evaluation library is one thing; the claim that it is *system- and corpus-agnostic* only holds if it works
on something it wasn't designed for. So I pointed [spancheck](https://github.com/tjromack/spancheck) — my citation-grade
RAG eval — at two real, published, third-party RAG applications, as a black box, over a public healthcare corpus. One
cracked into a full scored run and, in the process, improved spancheck itself. The other stood up cleanly and then hit
a wall I chose to document rather than break through. Both chapters are the point: this is what integrating with and
measuring systems you didn't write actually looks like.

## The problem

A grounded-answer system's most important property — do its citations hold, and does it decline when it should — is
also the least portable to measure, because every system represents "sources" differently. A credible eval has to meet
each target where it is, run against real environments (with their proxies, version pins and container quirks), and be
honest when a target won't cooperate. The test of "corpus-agnostic" is not a claim in a README; it is a run against
someone else's code.

## Constraints

- **Public data only, source cited.** A five-document corpus of US healthcare policy from Wikipedia (CC BY-SA):
  Medicare, Medicaid, health insurance, HIPAA, prior authorization — multi-document and overlapping, so a citation has
  to attribute to the *right* article.
- **Neutral, reproducible, small-set.** The hero is spancheck's generality, not either target's quality. Every run is a
  measurement on ~20 authored cases with the audit log attached — a field report, explicitly not a benchmark.
- **A real, hostile environment.** The work machine runs a TLS-inspecting corporate proxy that breaks almost every
  tool's outbound HTTPS (only OS-trust clients like `curl` pass) — a recurring adversary across both chapters.
- **Time-box the unknowns.** Each target gets a feasibility pre-flight; if it isn't answering a question within a couple
  of hours, it is documented and left, not chased.

## Chapter 1 — Kotaemon (a full, scored run)

[Kotaemon](https://github.com/Cinnamon/kotaemon) (Apache-2.0, Cinnamon Labs) is a real citation-RAG application whose
citation model — a "direct quote from the context, as a substring of the original content" — is an exact match for what
spancheck verifies. Standing it up meant clearing six real environment hurdles in order: it needs Python ≤3.11 (the
machine runs 3.13, so a 3.11 interpreter via `uv`); the proxy broke `uv`'s installer (`--native-tls`) and `tiktoken`'s
and Anthropic's TLS (`truststore`); its settings loader wanted the app's UI package (an env override); a loose
`langchain` pin resolved to a version its code doesn't use (install from its lockfile with `uv sync`); and the model
rejected a deprecated parameter. Then it ran — its real citation pipeline, on `claude-sonnet-5`, over the corpus, 21
cases.

The results were rich and honest:

- **Provenance and attribution ported with zero tuning.** Of Kotaemon's verbatim citations, **18/18 were source-scoped
  to the exact document they named** — spancheck verified a system it had never seen and got attribution 100% right.
- **It caught a real defect.** On an adversarial false-premise question, Kotaemon answered instead of abstaining and
  produced a **fabricated (non-verbatim) citation**; spancheck's provenance check flagged it.
- **It exposed an assumption in spancheck's own metric — which I then fixed.** The support score under-scored (0.29
  lexical, 0.43 judged) because Kotaemon answers *in detail* with short, answer-level quotes, while spancheck judged
  each quote against the *whole* answer — it was calibrated for *claim-scoped* citations. I added an opt-in `claim_split`
  (score support against the answer sentence a span is most relevant to); re-scoring the same run moved citation
  accuracy **0.286 → 0.762**, with the remaining failures being the genuinely fabricated citations.

Using the tool on a system it didn't design for made the tool better — the run's most valuable output.

## Chapter 2 — AnythingLLM (an honest blocker)

[AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) (MIT) is a different shape: a Docker container exposing a
REST API. It stood up cleanly, its outbound HTTPS *worked* through the proxy, and its chat API and developer key both
functioned — confirming it as a **PARTIAL** target (it returns retrieved source *chunks*, not span-level citations, so
spancheck would score abstention, groundedness and source attribution — the intended contrast with Kotaemon). But every
document-ingestion call failed with an opaque internal error (`"Failed integrity signature check"` / a `500` the
collector never explains). Setting the backend↔collector signing keys and restarting did not resolve it; the most
likely cause is the same proxy meeting the collector's processing step, but the service does not surface enough to
confirm it. I documented the fix path (mount the proxy CA into the container) and stopped — because knowing when to
stop is part of the discipline the pre-flight exists to enforce.

## How it's verified

| What | Result |
|---|---|
| Kotaemon — citations source-scoped to the correct document | **18/18 (100%)** on a system spancheck had never seen |
| Kotaemon — real defect caught | a fabricated citation + a failed adversarial abstention, provenance-flagged |
| Kotaemon — the metric fix, measured | citation accuracy **0.286 → 0.762** after shipping `claim_split` |
| AnythingLLM — pre-flight | container + API + key + Anthropic all working; ingestion blocked, documented with a fix path |

Full write-ups and audit logs: [`showcase/kotaemon/FINDINGS.md`](../showcase/kotaemon/FINDINGS.md),
[`showcase/anythingllm/FINDINGS.md`](../showcase/anythingllm/FINDINGS.md); the repeatable protocol is
[`docs/EXTERNAL-SHOWCASE.md`](EXTERNAL-SHOWCASE.md).

## What broke

The instructive break was not an environment fight — it was the **assumption in my own metric**. spancheck's citation
support check quietly assumed citations are claim-scoped, which is true of the system I built it against and false of
the first real system I pointed it at. A 0.29 score looked like a Kotaemon defect; it was a mismatch between how
spancheck asked the question and how Kotaemon answers. Naming that honestly — rather than shipping the low number as a
verdict — is what turned it into a fix.

## What this doesn't prove

Not a benchmark, and not a verdict on either project's quality: two systems, ~20 authored cases, one corpus, one
retrieval choice. It shows that spancheck's provenance and attribution checks are portable and catch real issues on an
independent system, and that the eval is honest enough to surface — and fix — an assumption in its own design.

## What I'd do differently

- **Unblock AnythingLLM properly** by mounting the proxy CA into the container, for a second *scored* target and a real
  PARTIAL data point.
- **Add a `provenance-only` mode** for systems that emit chunk-level sources rather than claims, so the metric fits the
  citation style without a workaround.

## Closing

The claim I most wanted to test was "corpus-agnostic," and the honest answer is: it held on the system that let me in,
and I never got to test it on the one that didn't. That is a truer result than two clean successes — and the chapter
where the tool got better by being used on someone else's code is the one I'd lead with.

*spancheck is MIT-licensed: `pip install spancheck` · https://github.com/tjromack/spancheck*
