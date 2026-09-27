# TODO — the build spine

Phased plan with approval gates. Each phase ends at a commit and a stop. The order is deliberate: the one genuinely-new
capability (citation-span verification) is built **first and tested deepest**, so it is proven before anything is built
on top of it. The dogfood target throughout is **Suver's published case study**, evaluated as a black box through the
adapter — never by coupling to Suver's code (design pin #6).

Decisions already settled (do not re-open): `DECISIONS.md` AB-DEC 001–004.

---

## Phase 0 — scaffold ✅ (this session)
- [x] PyPI name check → AB-DEC 001, then renamed `abstain` → `spancheck` (`spancheck` available; `groundcheck` taken) → AB-DEC 005
- [x] `DECISIONS.md` (source = evallab; lineage not replacement) — AB-DEC 001–004
- [x] `CLAUDE.md` — contract + the six design pins + "citation-span built first, tested deepest"
- [x] `README.md` — the promise + intended API shape + lineage
- [x] `TODO.md` — this spine
- [x] `LINEAGE.md` — the carried-over / rewritten / fixed ledger (started; filled as we go)
- [x] package skeleton — `pyproject.toml` (PEP 621, `src/` layout), `src/spancheck/__init__.py`, `LICENSE`, `.gitignore`
- [x] register the repo in the workspace: `../.gitignore` child-repo list + `../bootstrap.ps1` `$repos` map
- [x] `git init` + first commit
- [x] GitHub remote created + scaffold pushed → https://github.com/tjromack/spancheck

## Phase 1 — the core, ported from evallab (dependency-free) ✅ (2026-09-26)
- [x] `Case`, `run_eval`/`evaluate`, `Run`, `Scorecard`, `diff`, `gate` — ported from `evallab/core.py`, generalised (`core.py`)
- [x] the thin **adapter** interface (`adapter.py`): `adapter(callable)` + `normalize()` → the typed `Output`
      `{answer, contexts, citations, usage, latency_ms, abstained, raw}`; `evaluate()` times every call (AB-DEC 006)
- [x] deterministic graders (`graders.py`): `abstention_correct`, `groundedness`, `no_pii`, `max_latency`,
      `contains`/`regex_match`, `expected_contains` — reading the `Output`
- [x] LINEAGE entries (carried-over vs rewritten + why); AB-DEC 006 for the `Output` contract
- [x] tests: 22 pass; verified from a clean `pip install -e .` venv (no PYTHONPATH). **← stop for approval before Phase 2**

## Phase 2 — citation-span verification (the new capability — deepest tests) ✅ (2026-09-26)
- [x] AB-DEC 007: the span-check design — two deterministic checks (provenance = strict normalised substring;
      support = lexical-overlap proxy), both must hold; written before coding
- [x] `verify_citation()` + `citation_accuracy` grader (`span.py`); citation shape fixed (str | {span, claim?, source_id?});
      joined the default grader set (uncited answer scores 0 by default)
- [x] adversarial fixtures (`tests/test_span.py`): fabricated span, cited-but-unsupported/wrong-span,
      right-answer-wrong-citation, uncited claim, empty span, paraphrase-not-matched, partial — each fails as it should
- [x] the documented proxy boundary: a test pins that lexical support can't see negation (Phase-4 judge territory)
- [x] LINEAGE: recorded as the net-new capability the harness/evallab never had
- [x] 37 tests pass. **← stop for approval before Phase 3**

## Phase 3 — cost & latency + the versioned audit log ✅ (2026-09-26)
- [x] cost/latency computed from a cached run, no network (`audit.cost_latency`): latency total/mean/p50/p95/max;
      tokens summed; `cost_usd` only when pricing supplied or usage carried it (never invented)
- [x] the versioned audit-log schema (`schema_version` "1.0") + `run.audit_log(path)` — self-describing per case +
      per-citation verdicts; documented in `docs/AUDIT-LOG.md` (AB-DEC 008)
- [x] offline re-scoring (`Run.rescore(graders)`) — change a threshold / add a grader with no system call; `Run.load`
      round-trips the `Output` + case meta so a saved run is re-gradable
- [x] `spancheck score <audit.json>` — library recompute done here; CLI wrapper wired in **Phase 5** ✅
- [x] 49 tests pass. **← stop for approval before Phase 4**

## Phase 4 — the LLM-judge (optional, calibrated, file-based prompts) ✅ (2026-09-26)
- [x] provider seam (`provider.py`): `provider(prompt)->str`; stub by default; lazy optional `anthropic_provider()` —
      no hard vendor dependency, no lock-in (design pin #2)
- [x] judge prompts as version-controlled files (`prompts/entailment_v1.txt`, shipped as package-data); every verdict
      records `prompt_version` + `model` (design pin #5)
- [x] `judge_entailment` + `judge_support` (upgrades `citation_accuracy` support to entailment) + `llm_judge`
      (answer-level groundedness); one entailment prompt serves both
- [x] calibration harness (`calibrate.py`, `python -m spancheck.calibrate`): judge vs a human gold set
      (`calibration/entailment_gold.jsonl`), **agreement measured, not invented** — stub baseline **0.75 (9/12)**,
      misses only the paraphrase/morphology cases
- [x] judge stays **opt-in**; `default_graders()` remains fully offline/deterministic
- [x] 59 tests pass. **[Trevor] optional keyed run** for the real agreement number: `python -m spancheck.calibrate --real`
      (needs `ANTHROPIC_API_KEY`). **← stop for approval before Phase 5**

## Phase 5 — CLI + GitHub Action (thin wrappers) ✅ (2026-09-26)
- [x] `spancheck run` / `spancheck score` / `spancheck gate` (`cli.py`, argparse; each a few lines over the API);
      `gate` exits 1 on failure for CI; `Run.from_audit_log` reconstructs a run so score/gate recompute offline
- [x] a shipped demo target (`spancheck.demo:system`) + `examples/cases.jsonl` so `run` works from a clean clone with
      no user code and no key
- [x] `action.yml` (composite: install → run → gate) failing a PR on a regression via `gate`
- [x] `.github/workflows/ci.yml` (pytest on 3.11/3.12 from a clean clone) + `spancheck-demo.yml` (dogfoods the Action
      against the demo on every push)
- [x] 66 tests pass; console script verified in a clean non-editable install. **← stop for approval before Phase 6**

## Phase 6 — dogfood + case study + the harness copy pass
- [ ] **dogfood = option A** (Trevor 2026-09-27): score a real grounded system over real material, low/no cost.
      Source doc(s) + capture method TBC with Trevor; produce a real scorecard + audit log (`spancheck run … --out`)
- [ ] `docs/CASE-STUDY.md` — framed as the evolution of the harness (AB-DEC 003), with the measured numbers
- [ ] optional keyed **judge calibration** for the real agreement number (`python -m spancheck.calibrate --real`)
- [ ] the harness copy pass (API is stable). **Per Trevor 2026-09-27:** move "points at any LLM via a thin adapter" to
      spancheck (done here) and re-describe the harness as "the version that proved the method against one real target";
      **remove the "capstone" claim ENTIRELY from the harness — do NOT bring it to spancheck** (9 files: README, CLAUDE,
      DECISIONS, DEMO, MASTERY, PORTFOLIO_README, docs/CASE-STUDY)
- [ ] README `Status` updated with real numbers; **stop for approval**

## Later / maybe
- [ ] publish to PyPI (`spancheck`) — a release gate, after the audit-log schema is stable (v1.0.0)
- [ ] more adapters (a second real target beyond Suver)

---

### GitHub remote (Phase 0) — DONE
Created public + source-available, matching the siblings, and the scaffold is pushed:
**https://github.com/tjromack/spancheck** (topics: rag, llm-evaluation, hallucination-detection,
citation-verification, guardrails, python).
