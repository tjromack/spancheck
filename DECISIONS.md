# spancheck — decisions log

> Append-only. Point-in-time record of the calls made, so they are not re-litigated. This file is written **before any
> code** (the build packet's Step 0). Author: Trevor J. Romack.

## AB-DEC 001 — Name: `abstain` (2026-09-26)
**Status:** **Superseded by AB-DEC 005** — renamed to `spancheck` (2026-09-26). The original record is kept verbatim
below; the reasoning for the switch is in AB-DEC 005.

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
single real target (a regulatory RAG copilot), with judge agreement 1.00 on a human gold set. **`spancheck` is the
spinoff it evolved into:** the same method, extracted, generalised to any corpus, and packaged. Neither supersedes the
other in the portfolio; they read as a **sequence**, and `spancheck` gets its own case study framed as that evolution.

Two consequences, executed as part of this build:

- **The harness gets a small copy pass** — but only *once `spancheck`'s public API is stable enough that the claim is
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
door of published reports). `spancheck` is the **installable, corpus-agnostic library** that extracts and generalises
evallab's graders + core and adds citation-span verification, with its own repo root (required for PyPI, for a
distributable Action, and for the "clone it clean and point it at your own corpus" claim to be demonstrable). The lab
keeps producing reports; `spancheck` is the thing a stranger installs.

## AB-DEC 005 — Renamed `abstain` → `spancheck` (2026-09-26)
**Status:** Decided. Supersedes AB-DEC 001. Done while the project is still a fresh scaffold — the cheapest moment to
rename, before a release fixes the name in an install base.

- `spancheck` is available on PyPI (`https://pypi.org/pypi/spancheck/json` → 404), verified again at rename time.
- **Why the switch:**
  1. **It foregrounds the one genuinely-new capability.** `abstain` named *abstention correctness*, which is one of
     four metrics and — per AB-DEC 002 — the *least* novel (it already exists in `evallab`). `spancheck` names
     **citation-span verification**, the single capability new to the whole workspace and the reason this build is more
     than repackaging (the piece built first and tested deepest).
  2. **Unique and searchable.** `abstain` is a common English word — poor to search for, easy to confuse. `spancheck`
     reads like a tool name (cf. "spellcheck"), is distinctive, and collides with nothing.
- **Scope of the rename:** package + import name (`spancheck`), the repo (`tjromack/spancheck`), the CLI/Action slug,
  every doc, and the workspace registration (`.gitignore` + `bootstrap.ps1`). AB-DEC 001 is preserved above as the
  original record; the incidental project-name references in AB-DEC 003–004 were updated to `spancheck` for
  consistency (their *decisions* are unchanged).

## AB-DEC 006 — The normalised adapter `Output` contract (2026-09-26, Phase 1)
**Status:** Decided.

`evallab` let a system return either a bare string or a loose dict, and each grader dug out what it needed
(`output.get("answer")`, `output.get("contexts")`, …). That was fine for one in-repo lab but is too loose for a
library other people point at their own systems: cost/latency and citations were second-class, and nothing guaranteed
a captured run held what offline scoring needs.

**Decision:** normalise every system return **once** into a typed `Output` dataclass —
`{answer, contexts, citations, usage, latency_ms, abstained, raw}` (`adapter.py`). `normalize()` coerces str / dict /
`Output` into it (idempotent on `Output`); `adapter()` wraps a caller's `input->answer` callable and times it; and
`evaluate()` times every call and injects `latency_ms` when the system doesn't supply one. Graders read the `Output`,
never a raw dict.

- **Why:** it makes design pin #3 (every metric computable offline from a captured run) true by construction — a run
  always carries answer + contexts + citations + usage + latency — and gives Phase 2's citation-span verifier a fixed
  place (`Output.citations`) to read from. `raw` preserves the untouched original for the Phase-3 audit log.
- **Rejected:** keeping evallab's loose dict (too fragile a public contract); requiring callers to build the dataclass
  themselves (worse ergonomics than "hand us a function"). The adapter stays *thin* — it normalises and times, nothing
  more, so there is still no provider lock-in (design pin #2).

## AB-DEC 007 — Citation-span verification: design (2026-09-26, Phase 2)
**Status:** Decided (before code). This is the capability the whole build exists to add (`spancheck` is named for it),
so it is built first among the metrics and tested deepest.

**The question it answers:** for each claim an answer makes and each span it cites, *does the cited span actually
support the claim?* A grounded-answer system fails this in three distinct ways, and the design must catch all three:

1. **Fabricated span** — the system quotes source text that isn't in the retrieved context at all.
2. **Cited-but-unsupported / wrong-span** — the span is real (present in context) but doesn't support the claim
   attached to it. *Includes the "right answer, wrong citation" case: a correct answer with a citation that doesn't
   back it is still a citation failure, because the trust artefact — the audit trail — is broken.*
3. **Uncited claim** — the answer asserts something and cites nothing verifiable.

**The design — two deterministic checks per citation, both must hold:**

- **(a) Provenance** — is the cited span present in the retrieved contexts? Deterministic: normalise whitespace and
  case, then require the span to be a **substring** of the joined contexts. Catches (1). Strict on purpose: a system
  should cite **verbatim**; near-match/fuzzy acceptance would be a door for fabrication.
- **(b) Support (proxy)** — does the span cover the claim? Deterministic proxy: the fraction of the claim's content
  words present in the span must clear a threshold (default 0.6, the same spirit as `groundedness`). Catches (2). The
  claim defaults to the whole answer, or is the specific sentence a citation names.

A citation is **OK** iff provenance ∧ support. The `citation_accuracy` grader scores the **fraction** of citations
that are OK (so partial quality is visible) and, by default, **passes only when the fraction is 1.0** (`pass_threshold`,
because one broken citation breaks the audit trail). An **abstention** cites nothing and passes trivially; an answer
that asserts a claim with **no citations** fails (`require_citation=True` default) — catches (3).

**Citation shape (fixes `Output.citations`, previously carried through untyped):** each citation is either a bare
`str` (the span) or a dict `{span|quote|text, claim?, source_id?}`. `claim` scopes support to one sentence;
`source_id` is carried but not yet used to *scope* provenance (see limits).

**Stated limits (honest, and where Phase 4 comes in):**
- The support check is **lexical overlap, not entailment.** It cannot catch a span that contains the claim's words but
  **contradicts** it ("the notice period is **not** 30 days"). True entailment is exactly what the calibrated
  LLM-judge (Phase 4) is for; Phase 2 gives the deterministic backbone and flags this boundary. A test documents the
  false-positive so the boundary is explicit, not hidden.
- **Paraphrased citations are not matched by design** — provenance requires a verbatim (normalised) quote. A system
  that cites by paraphrase will score 0 on provenance; that is a deliberate incentive to quote sources exactly.
- **`source_id` doesn't yet scope provenance** — a span found in *any* context passes. Scoping a citation to its named
  source is a refinement, not shipped in Phase 2.

**Rejected alternatives:**
- **Semantic similarity / embeddings for support.** More robust than lexical overlap, but it needs a heavy dependency
  (a local model) or a new vendor (a new key, egress, cost) — a dependency-free library can't take that on by default,
  and it's the same trust/cost call parked elsewhere in the portfolio. The lexical proxy now, the LLM-judge as the
  opt-in upgrade (Phase 4), keeps the core dependency-free and deterministic.
- **An LLM-judge for provenance.** Provenance is a factual, checkable property; making it non-deterministic would
  invite drift on the one check that should never drift. The judge is reserved for the qualitative residue (support /
  entailment), never for "is this quote real."

---
*Next entry = AB-DEC 008.*
