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

### Open / next
- **Phase 1 complete; stopped for approval per the contract.** Next is Phase 2 — citation-span verification, decided
  in AB-DEC 007 (span-check design) *before* coding, built first and tested deepest. Awaiting Trevor's go.
