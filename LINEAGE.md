# LINEAGE.md — what carried over, what was rewritten, what got fixed

`spancheck` is not written from scratch and does not pretend to be. It is the spinoff of `llm-eval-guardrails-harness`,
extracting and generalising the measurement core that has lived inside `eval-lab/evallab`. This file is the ledger of
that inheritance — written *as the port happens*, because it is the substance of the second case study (AB-DEC 003) and
is near-impossible to reconstruct afterwards.

Three columns of the story:
- **Carried over** — code/design taken essentially as-is, because it was already right.
- **Rewritten** — taken but changed, with the reason.
- **New here** — capability that neither the lab nor the harness had.
- **What the harness got wrong that this fixes** — the honest delta that justifies the spinoff existing.

Status: **started at scaffold; filled per phase.** The tables below are the plan; entries move from *planned* to *done*
with the commit that lands them.

---

## The three ancestors (as found, verified by reading the code)

| Ancestor | Where | What it is | Why it isn't already the answer |
|---|---|---|---|
| `evallab` | inside `ai-suite` repo (`eval-lab/evallab/`) | dependency-free measurement core: `Case`, `run_eval`, `Run`, `Scorecard`, `diff`, `gate`; graders `abstention_correct`, `groundedness`, `llm_judge`, `no_pii`, `max_latency`, `contains`, `regex_match` | tracked *inside* the workspace repo → not independently `pip install`-able; no citation-span check; no versioned audit log |
| `llm-eval-guardrails-harness` | own repo | the method proved against one real target (regulatory RAG copilot); judge agreement 1.00 vs human gold set; FastAPI dashboard | a running app wired to one target, not a library a stranger installs and points at their own corpus |
| `project-suver/eval/` | own repo | four-category case taxonomy (answerable / unanswerable / adversarial / sensitive); substring-and-flag assertions over Suver's pipeline | coupled to Suver's pipeline (`from app.pipeline import …`); no judge, no span check, no cost/latency, no audit log — **not** the extraction source (AB-DEC 002) |

---

## Carried over — **landed in Phase 1 (2026-09-26)** unless noted

The `Case`/`Run`/`Scorecard`/`diff`/`gate` core and the deterministic graders below were ported from `evallab`
essentially verbatim (logic and regexes unchanged); the only structural change was the read path (see *Rewritten*).

| Piece | From | Notes |
|---|---|---|
| `Case` dataclass (id/input/category/expected/meta) | `evallab/core.py` | shape is right as-is |
| `run_eval` loop with per-case retry/backoff and error-as-data-point | `evallab/core.py` | the "one bad case never crashes the run" behaviour is worth keeping |
| `Scorecard` (`by_grader`, `by_category`, `overall_pass_rate`, `failures`) | `evallab/core.py` | |
| `diff` + `gate` (regression gate: thresholds + max_regression vs baseline) | `evallab/core.py` | the CI story reuses this directly |
| deterministic graders: `abstention_correct`, `groundedness`, `no_pii`, `max_latency` | `evallab/graders.py` | generalised to read from the normalised adapter output |
| the four-category case taxonomy | `project-suver/eval/` | taxonomy only (answerable/unanswerable/adversarial/sensitive), not the coupled assertions |
| calibrate-don't-trust discipline for the judge; human gold set | `harness` | the credibility move the harness already proved (agreement 1.00) — **realised in Phase 4** as `calibrate_judge` + `python -m spancheck.calibrate` (stub baseline 0.75; real number via a keyed run) |
| the LLM-as-judge concept | `evallab.graders.llm_judge` / `harness` | **carried, then re-homed (Phase 4):** evallab took an *inline* rubric string; `spancheck` moves prompts to version-controlled files (`prompts/entailment_v1.txt`), stamps every verdict with `prompt_version` + `model`, and reaches a model only through a caller-supplied provider (stub default) — no vendor hard-coded (AB-DEC 009, design pins #2/#5). The judge is scoped to **entailment** — the exact blind spot of the Phase-2 lexical proxy — not a general-purpose grader. |

## Rewritten — **output shape + timing landed in Phase 1 (2026-09-26)**

Landed this phase: the normalised **`Output`** dataclass (`adapter.py`) replaces evallab's loose str-or-dict — every
grader now reads `Output.answer/contexts/citations/usage/latency_ms/abstained` via `normalize()`, so cost/latency and
citations are first-class rather than dug out ad hoc (DECISIONS AB-DEC 006). `evaluate()` **times every system call**
and injects `latency_ms` when the system doesn't supply it, so a captured run always has what the offline metrics need
(design pin #3). Provider decoupling holds: the core calls only a caller-supplied `input->output` callable. The
versioned audit-log schema and the file-based judge prompts are still **planned** (Phases 3 and 4).

| Piece | From | Why it changes |
|---|---|---|
| output shape | evallab's loose `str`-or-`dict` | pinned to a normalised adapter contract `{answer, contexts, citations, usage, latency_ms}` so all four metrics have what they need and cost/latency is always present |
| judge prompt location | `evallab` accepts an inline `rubric` string | moved to version-controlled prompt files with a version stamp (design pin #5) — a rubric change becomes a reviewable diff |
| audit output | evallab's `Run.save` (a results dump) | a **versioned** audit-log schema aimed at a compliance reader (design pin #4), not an internal dump |
| provider coupling | evallab's `from . import provider` | a caller-supplied provider callable; stub by default; no vendor hard-coded (design pin #2) |
| packaging | inside the workspace repo | standalone `src/` package, PyPI-installable (AB-DEC 004) |

## New here

| Piece | Status | Why it's net-new |
|---|---|---|
| **citation-span verification** (`span.py`: `verify_citation`, `citation_accuracy`) | **landed Phase 2 (2026-09-26)** | Neither `evallab`, the harness, nor Suver's eval checks whether a *cited span actually supports the claim*. `evallab.groundedness` checks word-overlap against the *whole* context bag — it cannot tell a fabricated quote from a real one, or a right-answer-wrong-citation from a right one. `spancheck` splits this into **provenance** (is the span really in the context?) and **support** (does the span cover the claim?), both deterministic, both required. This is the one capability new to the entire workspace and the reason the build is more than repackaging (AB-DEC 007). Built first, tested deepest — 20+ span tests including every adversarial failure mode and the documented proxy boundary. |
| cost/latency as a first-class metric computed offline from a cached run | **landed Phase 3 (2026-09-26)** | evallab had `max_latency` as a pass/fail grader but no cost accounting and no "capture once, re-score offline" guarantee. `spancheck` aggregates latency (total/mean/p50/p95/max) and tokens/cost from the captured `Output`, and — the real pay-off of the Phase-1 output contract — `Run.rescore()` re-runs graders against a captured run with **no system call**. `cost_usd` is only computed when pricing is supplied, never invented (AB-DEC 008). |
| the versioned, compliance-readable **audit log** (`audit.py`) | **landed Phase 3 (2026-09-26)** | Neither evallab's `Run.save()` (an internal grade dump) nor the harness had a *versioned* record aimed at a reviewer. `spancheck`'s audit log has a `schema_version`, is self-describing per case (input/expected/meta), and carries per-citation verdicts — the deterministic "why" behind each citation score. Documented in `docs/AUDIT-LOG.md`. |

## What the harness got wrong that this fixes (to be filled honestly as discovered)

- **Confirmed in Phase 1:** the harness is a running app bound to a single target, and the reusable core was buried in
  it and in `evallab`, so the "points at any LLM through a thin adapter" claim was more true of the *lab* than of the
  shipped harness. Extracting the core into `spancheck` (a dependency-free package with a pinned adapter contract that
  installs clean and scores a black-box system in three lines) makes the reusable thing the actual deliverable — which
  is precisely the claim the harness README made but its shape didn't quite honour.
- *(TKTK — recorded as the port surfaces real ones. No invented deltas.)*
