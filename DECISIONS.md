# abstain — decisions log

> Append-only. Point-in-time record of the calls made, so they are not re-litigated. This file is written **before any
> code** (the build packet's Step 0). Author: Trevor J. Romack.

## AB-DEC 001 — Name: `abstain` (2026-09-26)
**Status:** Decided.

- The build packet's two working names were `abstain` and `groundcheck`. Checked on PyPI before writing any docs
  (the name lands in the README promise, the import path, and the GitHub Action's marketplace slug — renaming later
  touches all three):
  - `groundcheck` — **TAKEN** (`https://pypi.org/pypi/groundcheck/json` → 200).
  - `abstain` — **AVAILABLE** (404). (`spancheck` also available; `citecheck` taken.)
- **Chosen: `abstain`.** It is free, short and installable (`pip install abstain`), and it names the single
  most-cited under-instrumented metric in the packet — *abstention correctness: "does it decline when the answer
  genuinely isn't in the corpus? Nobody instruments this well."* Package name and import name are both `abstain`.
- *If a citation-span-forward name is preferred instead, `spancheck` is available — a fresh-scaffold rename, cheap now,
  expensive after the first release.*

## AB-DEC 002 — Extraction source is `evallab`, not Suver's `eval/` (2026-09-26)
**Status:** Decided. Corrects the packet premise ("pull the evaluation layer out of Suver").

Three eval codebases already exist in this workspace; verified by reading the files:

- **`project-suver/eval/`** opens `run.py` with `from app.pipeline import answer_question, ask_across` and
  `from app.config import settings`, and its own docstring says *"there is no model call in the scoring itself — every
  check is a plain substring/flag assertion over the pipeline's own output."* No judge, no citation-span verification,
  no cost/latency metric, no audit log. It is tightly coupled to Suver's pipeline. Extracting it would mean rewriting
  all four packet metrics from scratch and keeping only the four-category case taxonomy.
- **`eval-lab/evallab/`** already has most of the metrics. `graders.py` defines `abstention_correct`, `groundedness`,
  `llm_judge`, `max_latency`, `no_pii`, `expected_contains`, `regex_match`; `core.py` defines `Case`, `run_eval`,
  `Run`, `Scorecard`, `diff`, `gate`. Dependency-free, runs end to end. Its Case Study #1 is "Evaluating Suver's RAG."
- **`llm-eval-guardrails-harness/`** already describes itself as *"test set → run the target → score with rule checks
  + LLM-as-judge → regression & quality dashboard… points at any LLM system through a thin adapter,"* with judge–human
  agreement 1.00 against a human gold set — which is the packet's stated "credibility move."

**Decision: extract and generalise from `evallab`.** The only capability genuinely *new* to the whole workspace is
**citation-span verification** — does the cited span actually support the claim. Everything else exists here in some
form; this build is the **packaging** of a scattered capability into an installable, corpus-agnostic library + a
GitHub Action, plus the one new metric. The packet is honest about this: *"GAP IT CLOSES: none technically — this is
the packaging gap."*

## AB-DEC 003 — Lineage, not replacement: the harness stays; this is its spinoff (2026-09-26)
**Status:** Decided (given, not open).

`llm-eval-guardrails-harness` **stays published as the first version** — the one that proved the method against a
single real target (a regulatory RAG copilot), with judge agreement 1.00 on a human gold set. **`abstain` is the
spinoff it evolved into:** the same method, extracted, generalised to any corpus, and packaged. Neither supersedes the
other in the portfolio; they read as a **sequence**, and `abstain` gets its own case study framed as that evolution.

Two consequences, executed as part of this build:

- **The harness gets a small copy pass** — but only *once `abstain`'s public API is stable enough that the claim is
  actually true.* The harness README currently claims the ground this package is being built to take ("points at any
  LLM system through a thin adapter," "this is the capstone"); those move here, and the harness is re-described as what
  it was — the version that proved the method against one real target. **Not before** the API is stable.
- **Lineage is written down as it goes** — what carried over from `evallab` unchanged, what was rewritten and why,
  what the harness got wrong that this fixes. That is the substance of the second case study and is near-impossible to
  reconstruct afterwards. Kept in `LINEAGE.md` in this repo; polish is not required.

## AB-DEC 004 — What `evallab` becomes (2026-09-26)
**Status:** Decided.

`evallab` is tracked *inside* the `ai-suite` workspace repo, so it cannot be `pip install`ed independently regardless
of how good it is. It **stays there as the lab** — the in-repo instrument and the case-study practice (the revolving
door of published reports). `abstain` is the **installable, corpus-agnostic library** that extracts and generalises
evallab's graders + core and adds citation-span verification, with its own repo root (required for PyPI, for a
distributable Action, and for the "clone it clean and point it at your own corpus" claim to be demonstrable). The lab
keeps producing reports; `abstain` is the thing a stranger installs.

---
*Next entry = AB-DEC 005 (the citation-span verification design, once the API is sketched).*
