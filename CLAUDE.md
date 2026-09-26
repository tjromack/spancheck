# CLAUDE.md — Operating Contract

Working agreement for building `spancheck` with Claude Code. Read it before each session. The decisions this contract
assumes are already recorded in `DECISIONS.md` (AB-DEC 001–004) — read those first; do not re-open them.

## Purpose

Build **`spancheck`**: an installable, corpus-agnostic Python library (CLI second) that scores a grounded-answer system —
any RAG or retrieval-then-answer pipeline — on the four metrics that decide whether its answers can be trusted, and
emits an audit log a compliance reviewer can read.

The four metrics:

1. **Citation accuracy** — does the cited span actually support the claim? *(The one capability genuinely new to this
   workspace. Built first, tested deepest.)*
2. **Abstention correctness** — does it decline when the answer is not in the corpus, and answer when it is?
3. **Hallucination rate** — the share of answers asserting something the retrieved context does not support.
4. **Cost & latency** — per-run tokens/dollars and wall-clock, computed from a cached run without a network call.

This is a **packaging** build, not a research one: the metrics (bar citation-span) already exist scattered across
`eval-lab/evallab` and `llm-eval-guardrails-harness`. `spancheck` is the version a stranger can `pip install` and point
at their own corpus. See `LINEAGE.md` for what carried over and what was rewritten.

## Design pins (do not violate without a DECISIONS entry)

1. **Library-first, CLI-second.** The Python API is the product; the CLI and the GitHub Action are thin wrappers over
   it. Anything the CLI can do, a caller can do in three lines of Python.
2. **No provider lock-in.** A thin adapter from day one — the library never hard-codes Anthropic (or any vendor). A
   caller supplies a `run(input) -> output` callable and, for the judge, a provider callable. Stub by default.
3. **Every metric computable without network given a cached run.** A run is captured once (outputs + retrieved
   contexts + citations + timings/usage), then all four scores recompute offline. Re-scoring never re-calls a model
   except the LLM-judge, which is itself optional and cacheable.
4. **The audit-log schema is versioned; a breaking change is a major version bump.** The audit log is a contract with
   a compliance reader, not an internal dump.
5. **Judge prompts live in version-controlled files, never inline in code.** A rubric change is a reviewable diff with
   a version stamp; a judge score always records the prompt version + model that produced it.
6. **No dependency on Suver internals** — or on any other portfolio project's code. `spancheck` is standalone. It is
   *dogfooded* against Suver's published case study (as a black-box target through the adapter), never *coupled* to it.

## Operating principles

- **Synthetic / public test data only.** No PHI, no internal systems, no client-identifying detail — including in
  commit messages.
- **Deterministic checks carry the load; the judge is for the qualitative only, and is calibrated, never blindly
  trusted.** Citation accuracy, abstention correctness, PII leak, cost/latency are deterministic. The judge scores only
  what a rule cannot, records its rubric + model version, and is validated against a human gold set before it is
  trusted.
- **No invented facts.** Any number, benchmark, or result not yet measured is `[TKTK]` until it is run for real.
  Illustrative numbers never ship as if measured.
- **Source-available, not open-source** (LICENSE): view-for-evaluation; no reuse/deploy/commercial use.

## Stack

- Python 3.11+, standard library first. A hard dependency is added only with a DECISIONS entry justifying it.
- Packaging: `pyproject.toml` (PEP 621), `src/` layout, package + import name `spancheck`.
- CLI: `argparse` (stdlib) — no framework.
- GitHub Action: a thin `action.yml` shelling to the CLI.
- `pytest` for tests; the citation-span verifier gets the deepest test coverage.

## Conventions

- Small, single-purpose modules. Keep the public API surface small and documented in the README.
- Every run persisted as a versioned audit-log JSON: target + version, per-case output, retrieved contexts, citations,
  each metric's verdict, judge scores + rubric version, timings + usage.
- No secrets in code; read from the environment.
- **Commit at each phase boundary** with a readable message; the git history is an interview artifact.
- Update `DECISIONS.md` on every non-trivial choice (the audit-log schema, the adapter interface, the citation-span
  algorithm, the judge rubric) with the rejected alternative and the why. Update `LINEAGE.md` as things are ported.

## Definition of done (per phase)

- The phase's checklist in `TODO.md` is complete.
- The behaviour is demonstrable from a **clean clone** (`pip install -e .` then a documented command).
- Citation-span verification, once built, has tests that would fail if it silently passed an unsupported claim.
- New decisions recorded; a commit marks the phase boundary.
- **Stop and wait for approval before the next phase.**

## Do not

- Do not couple to Suver or any portfolio project's internals; go through the adapter.
- Do not use the LLM judge where a deterministic check would do; do not trust it without calibration.
- Do not inline a judge prompt; do not break the audit-log schema without a major version bump.
- Do not ship an illustrative number as a measured one; do not use real/PHI data.

## Case study voice

State plainly what the system is, what it does, the decisions made, and what was learned.

- No disclaimers about the author's experience. Limits belong to the system, stated as scope or cost.
- No honesty signalling ("the honest version", "published as a loss"). State the number.
- No apologising for scale. State the numbers and the design target.
- Real limits, costs, and failures stay — as facts about the system, not confessions.
