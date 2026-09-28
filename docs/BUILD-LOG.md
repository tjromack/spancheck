# spancheck — build log

A running, dated record of noteworthy process, decisions, learnings, and acknowledgements as `spancheck` is built.
Raw material for the case study and any later writing — kept honest and specific, numbers only when measured.

---

## 2026-09-26

### What happened
- **Kicked off BUILD 1** from a reviewer packet that corrected the original premise: the eval layer is *not* extracted
  from Suver's `eval/` (which is coupled to Suver's pipeline via `from app.pipeline import …` and does substring/flag
  assertions only) but from **`eval-lab/evallab`**, the dependency-free measurement core that already has most graders.
  Recorded as `DECISIONS.md` AB-DEC 002.
- **Step 0 before any code.** Wrote `DECISIONS.md` (AB-DEC 001–004), `CLAUDE.md` (six design pins), `README.md` (the
  promise), `TODO.md` (7-phase spine), `LINEAGE.md`, then the package skeleton — in that order, per the packet's rule
  "do not scaffold until the decision is written."
- **PyPI name check before writing docs** (the packet flagged that a name lands in the README promise, the import path,
  and the Action slug): `groundcheck` **taken**, `abstain` **available**, `spancheck` **available**.
- Shipped Phase 0 scaffold, created the public source-available repo, pushed.
- **Renamed `abstain` → `spancheck`** (AB-DEC 005) at Trevor's prompt. Reasoning: `abstain` named *abstention
  correctness* — one of four metrics and, per AB-DEC 002, the *least* novel; `spancheck` names **citation-span
  verification**, the one capability genuinely new to the workspace, and is unique/searchable where "abstain" is a
  common word. Renamed the package, repo, all docs, local folder, and workspace registration; kept AB-DEC 001 verbatim
  as the historical record.
- **Started Phase 1** — porting and generalising the measurement core from `evallab`.

### Decisions
- **AB-DEC 001–004** (source = evallab; lineage not replacement; what evallab becomes).
- **AB-DEC 005** — rename to `spancheck`.
- **AB-DEC 006** — the normalised adapter `Output` contract (this session; see below).

### Learnings / process notes
- **The honest reframing is the strength, not a liability.** The packet was explicit that this build closes "the
  packaging gap — none technically." Leaning into that (lineage from the harness, one genuinely-new capability) makes a
  more credible portfolio story than pretending it's all-new. `LINEAGE.md` exists to carry that.
- **Rename cost is real but front-loaded.** Renaming touched package/import/CLI/Action-slug/repo/docs/folder/workspace
  registration + a Windows directory-handle lock (`mv` failed "Device or resource busy"; PowerShell `Rename-Item`
  succeeded after the shell cwd moved out). Doing it at scaffold stage was the cheap moment — the lesson banked is
  *decide the name against the differentiator, not the catchiest metric, and do it before a release.*
- **No-substring-collision check paid off:** confirmed "abstain" is not a substring of "abstention"/"abstained" before
  a blanket rename, so the metric word survived untouched.

### Acknowledgements
- The name switch and the "extract from evallab, not Suver" correction both came from Trevor / the reviewer packet, not
  from me — worth crediting in any write-up as the calls that kept the build honest.

### Phase 1 — shipped this session
- Ported `Case`/`evaluate`/`Run`/`Scorecard`/`diff`/`gate` (`core.py`) + the deterministic graders (`graders.py`) from
  `evallab`, and added the thin **adapter** contract (`adapter.py`): a typed `Output`
  `{answer, contexts, citations, usage, latency_ms, abstained, raw}` that every grader reads. `evaluate()` times each
  system call and injects latency, so a captured run always has what the offline metrics need. Recorded as AB-DEC 006.
- **22 tests**, and — the gate that matters — verified from a **clean `pip install -e .` venv** (no PYTHONPATH), so
  the "clone it and run" claim is real, and the `spancheck` console script resolves.
- Tests assert behaviour, not just shape: a grounded answer passes, a hallucination fails groundedness, a correct
  abstention passes / a failure-to-abstain fails, a PII leak is caught, latency is always captured, a crashing system
  is recorded (not fatal), and a baseline regression is flagged by the gate.

### Learnings (Phase 1)
- **The blanket rename left one landmine.** `sed 's/abstain/spancheck/g'` correctly skipped "abstention/abstained"
  (no substring overlap) but *did* rewrite a README code comment `# should abstain` (the verb) into `# should
  spancheck`. Caught and fixed, then swept the repo for any other verb-collateral (none). Lesson banked: a
  find-replace on a project name will also hit the same letters used as an ordinary word — grep the prose afterwards,
  not just the code.
- **Pinning the output shape early is what makes the offline-scoring pin true.** By normalising once into `Output`,
  design pin #3 ("every metric computable without network from a cached run") stops being an aspiration and becomes a
  property of the type — and Phase 2's span verifier already has its slot (`Output.citations`).

### Phase 2 — shipped this session (citation-span verification, the differentiator)
- Wrote **AB-DEC 007** (the span-check design) *before* code, per the contract: two deterministic checks per citation,
  both required — **provenance** (strict normalised-substring match against the contexts → catches a fabricated quote)
  and **support** (lexical-overlap proxy: does the span cover the claim → catches cited-but-unsupported / wrong-span).
- Built `span.py`: `verify_citation()` (library-first, callable on one citation) + the `citation_accuracy` grader;
  fixed the citation shape (`str | {span, claim?, source_id?}`); joined it to the default grader set so an **uncited
  answer scores 0** on the tool's own thesis.
- **37 tests** (20+ new), the deepest coverage in the repo — every adversarial mode has a test that fails if the
  verifier stops catching it: fabricated span, wrong-span, **right-answer-wrong-citation**, uncited claim, empty span,
  paraphrase-not-matched, partial. Plus a test that pins the **documented proxy boundary** (negation is invisible to
  lexical overlap — Phase-4 judge territory), so the limit is explicit, not hidden.

### Learnings (Phase 2)
- **The tool caught my own bad citation.** A test fixture labelled a bare-string citation "valid," but a bare string
  defaults its claim to the *whole* (multi-topic) answer, which one span can't cover — so `citation_accuracy` scored it
  0.0, not the 0.5 I asserted. The code was right; my fixture was wrong. Two things banked: (1) **claim scoping
  matters** — cite a span *for a specific sentence*, not the whole answer; (2) it's a small live demonstration that the
  verifier does what it says, which is a good case-study beat.
- **Deterministic-first pays off in testability.** Because provenance and support are pure functions, every failure
  mode is a fast, exact unit test with no model in the loop — the reason this is the deepest-tested part of the repo.
- **Naming the limit is part of the trust story.** Writing the negation false-positive into a test and the README
  (rather than quietly hoping nobody hits it) is the same discipline as the eval that "flagged a fabrication that was
  actually correct" elsewhere in the portfolio: measure the boundary, state it, and point at the upgrade (Phase 4).

### Decisions (added)
- **AB-DEC 007** — citation-span verification design (two checks, deterministic, both required; lexical support proxy
  with the judge as the entailment upgrade; strict verbatim provenance; rejected embeddings/semantic-similarity on the
  dependency/vendor cost, same call parked elsewhere in the portfolio).

### Phase 3 — shipped this session (cost/latency + the versioned audit log)
- Wrote **AB-DEC 008** first: cost/latency aggregated offline from the captured `Output`; a versioned
  (`schema_version` "1.0") audit log aimed at a *reviewer*, with per-citation verdicts; and offline re-scoring — the
  concrete pay-off of pinning the output shape in Phase 1.
- Built `audit.py` (`cost_latency`, `build_audit_log`) + `Run.rescore()` / `Run.audit_log()` / `Run.cost_latency()`.
  Made `CaseResult` self-describing (input/expected/meta) and `Run.load()` reconstruct the `Output`, so a saved run
  round-trips into a fully re-gradable object. Documented the schema in `docs/AUDIT-LOG.md` (the "compliance reviewer
  can read it" claim, made legible).
- **49 tests** (12 new): latency percentiles, tokens summed, `cost_usd` null-without-pricing / computed-with-pricing /
  summed-from-explicit; audit-log shape + version + per-citation verdicts + valid-JSON write; and — the headline —
  **re-scoring the same run at a stricter threshold flips a result with no system call.**

### Learnings (Phase 3)
- **"No invented numbers" became a code rule, not a slogan.** `cost_usd` is `null` unless the caller supplies a price
  table or the run carried an explicit cost — spancheck refuses to bake in a price constant that would drift. A test
  pins the null-without-pricing behaviour, so the discipline is enforced, not just documented.
- **The Phase-1 output contract paid its rent this phase.** Because answer+contexts+citations+usage+latency were
  captured once as a typed `Output`, cost/latency, the audit log, *and* offline re-scoring all fell out without a
  second system call. The "capture once, re-score offline" pin went from aspiration to a demonstrated `rescore()`.
- **A versioned schema + a schema doc is the difference between "we log stuff" and "a reviewer can read it."** Writing
  `docs/AUDIT-LOG.md` with the `schema_version` bump rule is a small artefact that makes the compliance claim concrete.

### Decisions (added)
- **AB-DEC 008** — cost/latency + the versioned audit log (offline; `schema_version` "1.0", major-bump-on-break;
  per-citation verdicts; `Run.rescore` for offline re-grading; rejected a built-in price table and a save()-identical
  log).

### Phase 4 — shipped this session (the calibrated LLM-judge)
- Wrote **AB-DEC 009** first: the judge upgrades **support only** (provenance stays deterministic, never judged); a
  provider seam (`provider(prompt)->str`, stub default, lazy optional `anthropic_provider`, no hard vendor dep);
  prompts in version-controlled files with every verdict stamped `prompt_version` + `model`; one entailment prompt
  serving both citation support and answer-level groundedness; calibration measured, never asserted; judge opt-in.
- Built `provider.py`, `judge.py` (`judge_entailment` / `judge_support` / `llm_judge` / `load_prompt`),
  `prompts/entailment_v1.txt` (shipped as package-data), and `calibrate.py` (`calibrate_judge` +
  `python -m spancheck.calibrate`) with a synthetic public gold set (`calibration/entailment_gold.jsonl`). Extended
  `citation_accuracy` / `verify_citation` with an optional `support_fn` so the judge slots in without touching
  provenance.
- **59 tests** (10 new). The headline: `citation_accuracy(support_fn=judge_support())` **fails the negation
  contradiction that the Phase-2 lexical proxy passed** — the blind spot named in Phase 2 is now closed by the opt-in
  judge, and both behaviours are pinned by tests.
- **Stub calibration measured: agreement 0.75 (9/12)** on the gold set — and the only three misses are the
  paraphrase/morphology cases (twenty≈20, renew≈renews, governed≈governing law). A clean, honest picture: the
  deterministic stub nails negation + lexical/reordered support and misses meaning-level paraphrase, which is exactly
  the gap a real model closes.

### Learnings (Phase 4)
- **"Calibrated before trusted" is now a runnable command, not a value statement.** `python -m spancheck.calibrate`
  prints agreement + a confusion matrix + per-row hits/misses. The stub's 0.75 with legible misses is more convincing
  than a bare "we calibrate the judge" — you can see *what* it gets wrong and why.
- **The provider seam kept the dependency-free promise intact even while adding a model.** `anthropic` is imported
  lazily inside `anthropic_provider()`; the package still has zero hard dependencies, and the whole test suite runs on
  the stub with no key. Design pin #2 held under the phase most likely to break it.
- **One prompt, two graders.** Entailment ("does SOURCE support STATEMENT?") generalises to both citation support
  (span→claim) and answer groundedness (contexts→answer), so pin #5 (prompts in files) cost exactly one file.

### Decisions (added)
- **AB-DEC 009** — the calibrated LLM-judge (support-only upgrade; provider seam, stub default, lazy optional vendor
  helper; versioned file prompts; measured calibration; judge opt-in; rejected inline rubrics, a hard Anthropic dep,
  and judging provenance).

### Manual / [Trevor]
- **Optional keyed calibration run** for the *real* agreement number (the credibility figure to quote, mirroring the
  harness's 1.00): `python -m spancheck.calibrate --real --model claude-sonnet-5` with `ANTHROPIC_API_KEY` set. The
  build does not require it; the stub baseline (0.75) is what's committed until a real run is recorded.

### Phase 5 — shipped this session (CLI + GitHub Action)
- `cli.py`: `spancheck run` (load JSONL cases + a `module:callable` target → evaluate → write audit log), `score`
  (recompute metrics from a cached audit log, offline; `--regrade` re-runs graders on cached outputs), `gate`
  (thresholds as `grader=rate`, optional `--baseline` regression gate, **exit 1 on failure** for CI). Each is a few
  lines over the library (pin #1). Added `Run.from_audit_log` so score/gate reconstruct a run from the versioned log.
- A shipped demo target (`spancheck.demo:system`, a fake keyword-retrieval RAG over a 3-clause corpus) +
  `examples/cases.jsonl`, so `spancheck run …` works from a clean clone with **no user code and no key** — the exact
  command in the README.
- `action.yml` (composite: install → run → gate) that fails a PR on a regression; `.github/workflows/ci.yml`
  (pytest on 3.11/3.12 from a clean clone) and `spancheck-demo.yml` (the repo **dogfoods its own Action** against the
  demo on every push).
- **66 tests** (7 new): run writes a valid schema-1.0 log; pricing computes cost; score reads offline; gate
  pass/fail exit codes; a baseline regression trips the gate; a bad target spec errors. Console script verified in a
  clean **non-editable** install (`spancheck run … && spancheck gate …`).

### Learnings (Phase 5)
- **A shipped demo target is what makes "path to try it" real.** Rather than a README snippet a reader has to adapt,
  `spancheck run examples/cases.jsonl --target spancheck.demo:system` runs on a clean clone and scores 3/3 — and the CI
  workflow runs that same command through the Action, so the "try it" path is continuously proven, not just claimed.
- **Library-first kept the CLI honest.** Because every command is a thin wrapper, the CLI has almost no logic of its
  own to test — the behaviour was already covered in the library tests, and `test_cli.py` only checks the wiring
  (parsing, file IO, exit codes). That's the pin #1 dividend.
- **The Action is the honest replacement for the harness's web app** — a reusable tool's surface is CI + a CLI, not a
  running dashboard bound to one deployment. Recorded in LINEAGE as part of "what the harness got wrong that this
  fixes."

### Open / next
- **Phase 5 complete.** Next is Phase 6 — the end-to-end **dogfood against a real target** (Suver's published case
  study, as a black box) producing a real scorecard + audit log, the **case study** framed as the harness's evolution,
  and the **harness copy pass** (now that the API is stable). This is the phase that most benefits from a review — and
  from the optional keyed calibration number — so a natural point to sync with Trevor.

---

## 2026-09-27

### What happened
- New session (paused before Phase 6 last time). Trevor answered the three pre-Phase-6 questions and I did the enabling
  setup so his manual steps are minimal.

### Decisions (Trevor, 2026-09-27)
- **Dogfood target = option A** — score a real grounded system over real material, low/no cost (no big keyed run).
  Exact source doc(s) + capture method to be confirmed before Phase 6 executes.
- **API key created for spancheck.** Placement solved: added a **dependency-free `.env` loader** (`_env.py`) wired into
  `spancheck.calibrate` and the CLI, so a key in `c:/ai/spancheck/.env` is picked up automatically (never overwrites a
  real env var; `.env` is gitignored). No new dependency.
- **Harness copy pass — refined:** move "points at any LLM via a thin adapter" to spancheck (already there) and
  re-describe the harness as "the version that proved the method against one real target"; **drop the "capstone" claim
  ENTIRELY from both repos.** Trevor's rationale, banked: *naming any one project the portfolio's capstone caps the
  ceiling of the whole portfolio.* Recorded in AB-DEC 003 + TODO Phase 6; execution is in Phase 6 (9 harness files).

### Work done today
- `_env.py` (+ `test_env.py`): the .env loader; wired into `calibrate.main` and `cli.main`.
- Recorded the copy-pass refinement in `DECISIONS.md` (AB-DEC 003) and `TODO.md` (Phase 6).
- Outlined the remaining manual steps for Trevor (key placement + dogfood-source confirmation + spend authorisation).

### Phase 6 — ran this session (dogfood + case study + real judge number)
- Trevor confirmed: dogfood **option A** (Suver's own sample corpus) + **B1** (run Suver's real pipeline), key in `.env`,
  small spend authorised.
- Mapped Suver's `AnswerResult` → spancheck `Output` (`Claim.span_text` → citation span, `Claim.text` → claim, the MSA →
  the single context). Built `dogfood/{suver_cases.jsonl, run_dogfood.py}` and ran Suver's real `answer_question` on
  **claude-sonnet-5** over its sample MSA, as a black box (spancheck never imports Suver internals for grading).
- **Result: overall 0.967; citation accuracy 1.00; groundedness 1.00 (0 hallucinations); no_pii 1.00; abstention 11/12;
  recall 11/12.** The single miss is real and valuable: Suver **false-abstained** on a paraphrased answerable question
  (`renewal-notice`) — a genuine recall gap in a shipping system, surfaced by the eval. Audit log committed at
  `dogfood/suver_audit.json`.
- **Judge calibration (keyed): stub 0.75 → claude-sonnet-5 1.00 (12/12)** — the real model closed exactly the three
  paraphrase/morphology cases the stub missed. Recorded in `calibration/RESULTS.md`.
- Wrote `docs/CASE-STUDY.md` (framed as the harness's evolution) and updated README `Status` + a `Results` table.

### Learnings (Phase 6)
- **Two bugs the run caught, both instructive.** (1) My capture script built a grader list but forgot to pass it to
  `evaluate`, so recall wasn't measured — fixed, and I added the recall grader by **re-scoring the captured run
  offline** (`Run.rescore`), no extra model spend: the Phase-3 "capture once, re-score offline" pin paying off in
  practice. (2) The direct judge call failed with a TLS `APIConnectionError` behind a TLS-inspecting proxy while the
  Suver path succeeded — because Suver injects `truststore`. Added an optional `truststore.inject_into_ssl()` to
  `anthropic_provider` (guarded, like the anthropic import), and calibration then ran clean.
- **The dogfood earned its keep by finding a real miss.** A green 12/12 would have been less useful than 0.967 with one
  concrete, reproducible false-abstention — that is the difference between a demo and an evaluation.
- **Verify the provider, don't assume it.** Suver silently degrades to a stub on any model error; I confirmed
  `provider=anthropic` and model-written answers in the audit log before trusting the numbers.

### Manual / [Trevor]
- **Harness copy pass — staged, awaiting your ok before I push the second public repo** (as promised): remove "capstone"
  entirely, move the "any LLM / thin adapter" claim to spancheck, reframe the harness as "the version that proved the
  method against one real target." Wording shown in the session for approval.

### Harness copy pass — pushed (harness 14981b2)
- Removed "capstone" entirely from the harness (8 files: README, CLAUDE, DECISIONS, DEMO, MASTERY, TALKING_TRACK,
  PORTFOLIO_README, docs/CASE-STUDY), reframed it as "the version that proved the method against one real target," and
  linked spancheck as the generalised version. Trevor approved the wording first. The harness's own numbers untouched.

### Phase 6 complete — build is done
- All six phases shipped; spancheck is a complete, dogfooded, CI-green, **MIT-licensed** library with real measured
  numbers (dogfood overall 0.967, citation accuracy 1.00, 0 hallucinations, 1 real finding; judge calibration 1.00).

### Relicensed MIT + PUBLISHED to PyPI (2026-09-27)
- **Decision (Trevor):** spancheck is MIT-licensed and published to PyPI. Rationale: it's a reusable *tool meant to be
  run*, so a source-available "no-use" licence contradicted `pip install`. The product (Suver) and the applied-AI
  engines stay source-available; spancheck is deliberately open as a library — a clean product/tooling split (AB-DEC 010).
- Swapped `LICENSE` to MIT; `pyproject` → `license = "MIT"` (SPDX + license-files, setuptools>=77); updated every
  "source-available" reference (README banner + licence section, CLAUDE, case study) to MIT and the install line to
  `pip install spancheck`. Added `RELEASING.md`.
- **PUBLISHED: `pip install spancheck` → https://pypi.org/project/spancheck/ (v0.1.1, tag v0.1.1).** Verified on a clean
  `--no-cache-dir` install: `spancheck --version` → 0.1.1 and a full `run`/`gate` cycle passes from the PyPI wheel.

### Learnings (publish)
- **The TLS-inspecting proxy bit twice more.** `twine` (via `requests`) failed cert verification exactly like the
  earlier model call; ran the upload through a `truststore.inject_into_ssl()` launcher and it went through. Same root
  cause as the provider fix — worth remembering this network needs the OS trust store for *any* outbound TLS.
- **Ship the version from metadata, not a string.** 0.1.0 published with a stale hardcoded `__version__` ("0.0.1")
  because the code string wasn't synced with `pyproject`. Fixed by reading `__version__` from `importlib.metadata`
  (single source of truth) and re-releasing as 0.1.1. A version is publish-once, so the lesson is cheap here but would
  be expensive later: never hardcode a version in two places.
- **Windows saved `.pypirc` as `.pypirc.txt`.** Notepad appends `.txt`; twine looks for the exact name. Renamed it
  (contents never read/printed) and the token stayed out of the transcript.
- Optional hygiene left to Trevor: yank 0.1.0 on the PyPI web UI (0.1.1 is latest, so `pip install spancheck` already
  gets the good one).

### Rubric self-grade vs the Build Playbook §01 (2026-09-27)
- Scored against the 8-gate rubric: **14/16 → Featured** (no zero anywhere; full marks on the two gates the playbook
  says matter most — Gate 6 try-it via `pip install` + demo target, and Gate 4 verification evidence via the dogfood +
  error analysis + judge calibration).
- Two soft spots at 1: **Gate 2** (README lacked a visual, an explicit audience, and the packet's competitor-landscape
  paragraph) and **Gate 7** (input real but a single tidy 12-case contract, not messy enough that handling it is the work).
- **Gate 2 fixed → 15/16:** added `docs/cli-demo.svg` (a real run + gate render), a "Who it's for" line, a
  "How it compares" paragraph (Ragas/DeepEval/TruLens/promptfoo/Braintrust + the narrow differentiator), and a
  "not a general-purpose eval platform / not a benchmark" limit.
- **Gate 7 fixed → 16/16:** the messy multi-document dogfood (below) + source-scoped provenance.

### Gate 7 → 2: multi-document dogfood + source-scoped provenance (2026-09-27)
- **Source-scoped provenance (AB-DEC 011):** `Output` gained an optional `sources` map (`{source_id: text}`); when a
  citation names a source present in the map, `verify_citation` scopes provenance to *that document only* — a span
  attributed to the wrong document fails as **misattributed**, distinct from *fabricated*. Backward-compatible (no map →
  match all contexts). +3 tests, incl. "a real span attributed to the wrong doc fails."
- **Messy 4-document corpus** (`dogfood/corpus/`): a Master Services Agreement, a **superseding Amendment** (changes
  notice 60→90 days, governing law NY→Delaware, adds a 1.5% late fee), a cross-referencing SOW, and a DPA — deliberate
  cross-document conflicts. 21 cases across answerable / answerable-conflict / unanswerable / adversarial.
- **Dogfooded Suver's real `ask_across`** (its N-document tool) on claude-sonnet-5, black box
  (`dogfood/run_dogfood_multidoc.py`). **Result: overall 1.00; 47/47 citations source-scoped and correct**, both sides
  of each conflict cited to the right document (MSA *and* Amendment for governing law / notice). Provider confirmed
  `anthropic` (via the nested raw + paraphrased answers), not a stub fallback.

### Learnings (Gate 7)
- **Relabelled two adversarial cases before spending.** My first-draft `adv-sixmonth` / `adv-24hr` asserted a false
  number about a topic that *is* in the corpus — a system that *corrects* the premise would then fail a "must-abstain"
  label, the exact "eval flagged correct behaviour" trap from the single-doc run. Swapped them for clean false-premise
  cases where abstention is unambiguously right (arbitration venue in the amendment, an SOW termination penalty — both
  genuinely absent). Caught it in the offline stub smoke test, before the keyed run.
- **A perfect score is only evidence once the provider is confirmed.** The stub is extractive (verbatim doc sentences),
  so it would *also* pass provenance and source-scoping trivially — a clean 21/21 is meaningless until you prove the
  real model ran. Verified via the nested `raw.provider` **and** the answers being paraphrased, not extracted.
- **Two dogfoods tell a better story than one.** Single-doc found a real defect (a false-abstention); the harder
  multi-doc came back clean with 47/47 source-scoped attributions. Together: the eval catches real misses *and*
  validates correct behaviour on the hard case.

### Next (open, all additive / Trevor)
- (a) Site repo — add the spancheck card + case study (body ready at `docs/CASE-STUDY.md`); the card CTA is now a real
  `pip install spancheck`. Copy/paste brief handed over in-session. (b) A RESUME-UPDATES line now that real numbers +
  a live package exist ([[keep-resume-updates-current]]). (c) **Gate 7 → 2:** a messier multi-document dogfood corpus
  (decisions scoped in-session). (d) Optional: a second real adapter, source-scoped citations.

---

## 2026-09-28

### What happened
- Opened the **external showcase** — pointing spancheck at *other people's real, published projects* (not framework
  examples) to prove empirically that it's system/corpus-agnostic, and to generate case-study findings. Trevor picked
  the **healthcare** domain and targets **Kotaemon + AnythingLLM**, design **(a)** (Kotaemon's real citation pipeline
  fed by a BM25-retrieved context).
- Wrote the runbook (`docs/EXTERNAL-SHOWCASE.md`) — per-target protocol, framing rules (neutral, reproducible,
  field-report-not-benchmark), and a Step-0.5 feasibility pre-flight with a timebox.
- Pulled a **public healthcare corpus** myself via `curl` (works through the TLS proxy; the Python HTTP clients don't):
  5 Wikipedia articles (CC BY-SA, attributed) → `showcase/corpus/`.
- **Kotaemon pre-flight — a saga, then success.** Confirmed its `CiteEvidence` model (verbatim source substrings) is a
  perfect match for spancheck's citation-span verification, and got its **real** `CitationPipeline` running on
  claude-sonnet-5 over our corpus. Six real environment hurdles, all solved and recorded in the runbook: Python 3.13→
  3.11 (via `uv`), the TLS proxy on `uv` (`--native-tls`) and on `tiktoken`/`anthropic` (`truststore`), `theflow`'s
  settings loader (`THEFLOW_SETTINGS_MODULE=theflow.settings.default`), the langchain 0.1.x pin (`uv sync` from the
  lockfile), the `model_name` kwarg, and `temperature` being deprecated on the 5-family (`temperature=None`).
- **Ran the scored showcase.** Built `showcase/kotaemon/{cases.jsonl, capture_kotaemon.py, score.py, score_judged.py}`;
  captured 21 cases in Kotaemon's venv, scored offline in spancheck's env.

### Results (Kotaemon × spancheck, 21 healthcare cases, claude-sonnet-5)
- Overall **0.829**. Abstention: off-corpus **5/5**, adversarial 2/3. Groundedness 0.952. No-PII 1.00.
- **Provenance + attribution: 18/23 citations verbatim; 18/18 of those source-scoped to the exact named document
  (100%).** The headline — spancheck's core check ported to an unseen third-party system with zero tuning.
- **Caught a real defect:** on an adversarial false premise, Kotaemon answered instead of abstaining *and* produced a
  fabricated (non-verbatim) citation — provenance flagged it.
- **An honest finding about spancheck's own metric:** citation *support* under-scored (lexical 0.29, judge 0.43)
  because Kotaemon emits a detailed answer + short answer-level quotes, while the support check judges each quote
  against the whole answer — it's calibrated for *claim-scoped* citations (as the dogfood used). Fair metric for such
  systems = provenance + attribution; claim-splitting is the enhancement this surfaced. `showcase/kotaemon/FINDINGS.md`.

### Learnings (2026-09-28)
- **The pre-flight/timebox discipline earned its keep — twice.** It stopped me sinking an afternoon into a Windows
  vector-DB install, and the offline stub smoke test (and the corpus-content read) caught bugs before the keyed run.
- **A perfect score is only evidence once the provider is confirmed** (again): I verified `provider=anthropic` and
  model-written answers before trusting anything.
- **Read the low number correctly.** A 0.29 citation-support score looked alarming but was the *documented* proxy
  boundary meeting a detailed-answer system — not a Kotaemon defect and not a spancheck bug, but a real insight into
  the metric's assumption. The most valuable showcase output is a nuanced true finding, not a green bar.
- **`curl` (OS trust store) reaches the internet here; Python `requests`/`httpx`/`uv` (their own TLS) need
  `truststore`/`--native-tls`.** Banked for any future outbound work on this machine.

### Next (open)
- AnythingLLM (target #2) — pre-flight on the same protocol (its Docker+REST isolation should sidestep the Python-env
  friction Kotaemon had). Then fold both into a "real-world use" case-study section (Kotaemon part already added).
- Optional spancheck enhancement named by this run: a `provenance-only` / claim-splitting mode for answer-level-citation
  systems. Third-party project clones + venvs live outside the repo (`~/showcase-targets/`); only our artifacts commit.

### Enhancement (2026-09-28): `claim_split` — the Kotaemon finding, fixed (v0.3.0)
- Turned the metric-design finding into a shipped option (AB-DEC 012): `citation_accuracy(claim_split=True)` scores an
  unscoped citation's support against the answer **sentence it's most relevant to**, not the whole answer — the fair
  question for systems that emit a detailed answer + short answer-level quotes. A truly irrelevant quote still fails,
  so it's strictly fairer, not laxer. Opt-in (keeps every existing committed number intact). +1 test (72 total).
- **Re-scored the same captured Kotaemon run: citation accuracy 0.286 → 0.762** — the remaining failures are the
  genuinely fabricated citations (the real catches). Folded into `FINDINGS.md` and the case study.
- ⭐ **Case-study framing (Trevor, 2026-09-28): the *practice* of pointing spancheck at other people's real systems is
  its own case study ("Evaluating in the wild") — distinct from spancheck's own case study.** Kotaemon = chapter 1
  (env saga + honest findings + a fix the run produced); AnythingLLM = chapter 2 (next). Documenting the *process and
  lessons*, not just numbers, from here — that narrative is the substance of that second case study.
