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

### Open / next
- **Phase 3 complete.** Next is Phase 4 — the calibrated LLM-judge for the qualitative residue (true entailment, the
  Phase-2 support-proxy's blind spot), with prompts in **version-controlled files** (design pin #5) and a calibration
  harness reporting judge-vs-human agreement (measured, not invented). This is the first phase that *can* touch a
  provider — but via a caller-supplied callable, stub by default (no lock-in). Proceeding per Trevor's standing note.
