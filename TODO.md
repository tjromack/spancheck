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
- [~] `spancheck score <audit.json>` — the **library** recompute is done (`rescore` / `cost_latency` / `audit_log`);
      the CLI wrapper is wired in **Phase 5** (library-first, CLI-second)
- [x] 49 tests pass. **← stop for approval before Phase 4**

## Phase 4 — the LLM-judge (optional, calibrated, file-based prompts)
- [ ] judge prompts as version-controlled files (design pin #5); score records prompt version + model
- [ ] calibration harness: judge vs a human gold set, agreement reported (no number invented — measured)
- [ ] **stop for approval**

## Phase 5 — CLI + GitHub Action (thin wrappers)
- [ ] `spancheck run` / `spancheck score` / `spancheck gate` (argparse; three-lines-of-Python parity)
- [ ] `action.yml` shelling to the CLI; a workflow that fails a PR on a regression (uses `gate`)
- [ ] **stop for approval**

## Phase 6 — dogfood + case study + the harness copy pass
- [ ] run `spancheck` end-to-end against Suver's published case study as a black box → real scorecard + audit log
- [ ] `docs/CASE-STUDY.md` — framed as the evolution of the harness (AB-DEC 003), with the measured numbers
- [ ] the harness copy pass — **only now** that the API is stable: move "points at any LLM via a thin adapter" +
      "capstone" claims here; re-describe the harness as "the version that proved the method against one real target"
- [ ] README `Status` updated with real numbers; **stop for approval**

## Later / maybe
- [ ] publish to PyPI (`spancheck`) — a release gate, after the audit-log schema is stable (v1.0.0)
- [ ] more adapters (a second real target beyond Suver)

---

### GitHub remote (Phase 0) — DONE
Created public + source-available, matching the siblings, and the scaffold is pushed:
**https://github.com/tjromack/spancheck** (topics: rag, llm-evaluation, hallucination-detection,
citation-verification, guardrails, python).
