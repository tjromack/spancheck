# TODO — the build spine

Phased plan with approval gates. Each phase ends at a commit and a stop. The order is deliberate: the one genuinely-new
capability (citation-span verification) is built **first and tested deepest**, so it is proven before anything is built
on top of it. The dogfood target throughout is **Suver's published case study**, evaluated as a black box through the
adapter — never by coupling to Suver's code (design pin #6).

Decisions already settled (do not re-open): `DECISIONS.md` AB-DEC 001–004.

---

## Phase 0 — scaffold ✅ (this session)
- [x] PyPI name check (`abstain` available; `groundcheck` taken) → AB-DEC 001
- [x] `DECISIONS.md` (source = evallab; lineage not replacement) — AB-DEC 001–004
- [x] `CLAUDE.md` — contract + the six design pins + "citation-span built first, tested deepest"
- [x] `README.md` — the promise + intended API shape + lineage
- [x] `TODO.md` — this spine
- [x] `LINEAGE.md` — the carried-over / rewritten / fixed ledger (started; filled as we go)
- [ ] package skeleton — `pyproject.toml` (PEP 621, `src/` layout), `src/abstain/__init__.py`, `LICENSE`, `.gitignore`
- [ ] register the repo in the workspace: `../.gitignore` child-repo list + `../bootstrap.ps1` `$repos` map
- [ ] `git init` + first commit
- [ ] **[Trevor]** create the GitHub remote (outward-facing) — command supplied below; push the scaffold

## Phase 1 — the core, ported from evallab (dependency-free)
- [ ] `Case`, `run_eval`/`evaluate`, `Run`, `Scorecard`, `diff`, `gate` — ported from `evallab/core.py`, generalised
- [ ] the thin **adapter** interface: `adapter(callable)` normalising a system's output to
      `{answer, contexts, citations, usage, latency_ms}`
- [ ] deterministic graders ported from `evallab/graders.py`: `abstention_correct`, `groundedness`, `no_pii`,
      `max_latency`, `contains`/`regex_match`
- [ ] LINEAGE entries for each ported piece (unchanged vs rewritten + why)
- [ ] tests for the ported core; **stop for approval**

## Phase 2 — citation-span verification (the new capability — deepest tests)
- [ ] AB-DEC 005: the span-check design (offset-based? substring? semantic? — decided and written before coding)
- [ ] `citation_accuracy` grader: for each claim + its cited span, does the span support the claim?
- [ ] adversarial fixtures: cited-but-unsupported, right-answer-wrong-span, fabricated span, no-citation — each must
      fail the way it should (a test that would catch a silent pass)
- [ ] LINEAGE: this is the piece the harness did **not** have — record it as the net-new capability
- [ ] **stop for approval**

## Phase 3 — cost & latency + the versioned audit log
- [ ] cost/latency computed from a cached run, no network (design pin #3)
- [ ] the versioned audit-log schema (`schema_version`) + `run.audit_log(path)` — the compliance-readable record
- [ ] `abstain score <audit.json>` recomputes every metric offline from the cache
- [ ] **stop for approval**

## Phase 4 — the LLM-judge (optional, calibrated, file-based prompts)
- [ ] judge prompts as version-controlled files (design pin #5); score records prompt version + model
- [ ] calibration harness: judge vs a human gold set, agreement reported (no number invented — measured)
- [ ] **stop for approval**

## Phase 5 — CLI + GitHub Action (thin wrappers)
- [ ] `abstain run` / `abstain score` / `abstain gate` (argparse; three-lines-of-Python parity)
- [ ] `action.yml` shelling to the CLI; a workflow that fails a PR on a regression (uses `gate`)
- [ ] **stop for approval**

## Phase 6 — dogfood + case study + the harness copy pass
- [ ] run `abstain` end-to-end against Suver's published case study as a black box → real scorecard + audit log
- [ ] `docs/CASE-STUDY.md` — framed as the evolution of the harness (AB-DEC 003), with the measured numbers
- [ ] the harness copy pass — **only now** that the API is stable: move "points at any LLM via a thin adapter" +
      "capstone" claims here; re-describe the harness as "the version that proved the method against one real target"
- [ ] README `Status` updated with real numbers; **stop for approval**

## Later / maybe
- [ ] publish to PyPI (`abstain`) — a release gate, after the audit-log schema is stable (v1.0.0)
- [ ] more adapters (a second real target beyond Suver)

---

### [Trevor] manual: create the GitHub remote (Phase 0)
Outward-facing, so tagged for you. Source-available public, matching the siblings:
```bash
gh auth switch --user tjromack
cd C:/ai/abstain
gh repo create abstain --public \
  --description "Score a grounded-answer system on citation accuracy, abstention correctness, hallucination rate, cost and latency — with an audit log a compliance reviewer can read. Source-available." \
  --source . --remote origin
git push -u origin main
```
(Or say the word and I'll run it.)
