# External showcase — pointing spancheck at other people's real projects

spancheck was dogfooded on one product pipeline (`dogfood/`). This is the field report of pointing it at **real,
published, third-party RAG applications** — to show its core claim (corpus- and system-agnostic) empirically, and to
generate honest findings for the case study.

**Framing (non-negotiable).** The hero of this exercise is **spancheck's generality**, not any target's quality. Every
run is a neutral, reproducible measurement on a small authored test set. Where a finding is unflattering to a target, it
is stated as a measured observation with the audit log attached, and the target may be described generically. No target
is endorsed; none is disparaged. Public/synthetic corpora only, source cited — the same hard rules as the rest of the
project.

**Scope boundary.** This is a *field report* (2–3 systems, ~20–30 cases each), **not** a benchmark or leaderboard — the
case study is explicit that spancheck is not benchmark-grade. Keep it that way.

---

## The corpus (public, cited)

`showcase/corpus/` — five public healthcare articles from Wikipedia (CC BY-SA, source + retrieval date in each file):
Medicare, Medicaid, Health insurance in the United States, HIPAA, Prior authorization. Multi-document and related, so
citations must attribute to the *right* article (exercises spancheck's source-scoped provenance).

## The per-target protocol

```
0.  PRE-FLIGHT (timeboxed ~2–3 hrs; fail fast)
    □ OSS + license permits use? Public/synthetic data only?
    □ What does it emit: answer only / + contexts / + span-level citations?  → sets which metrics apply.
    □ Stand it up on ONE doc + our Anthropic key; ask one question; capture the raw output.
    □ Verdict: FULL (span citations) / PARTIAL (contexts only) / SKIP (won't run in the timebox).
1.  CORPUS      □ use showcase/corpus/ (or a target-appropriate public set); cite the source.
2.  TEST SET    □ ~20–30 cases: answerable · unanswerable (the abstention half) · adversarial · conflict (multi-doc).
3.  ADAPTER     □ question -> {answer, contexts, citations[{span, source_id}], usage, latency_ms}.
4.  SMOKE       □ 1–2 cases offline/stub first — catch mapping bugs before paying.
5.  REAL RUN    □ run on the real model; VERIFY the provider/model actually executed (not a fallback).
6.  EVIDENCE    □ commit the audit log under showcase/<target>/.
7.  ANALYSIS    □ honest, small-set caveat, neutral tone; note where a spancheck limit shaped a result.
8.  FIELD REPORT□ one short write-up per target: setup · corpus · what spancheck measured · the finding · repro command.
9.  DONE        □ adapter + cases + committed audit log + a 1-paragraph finding + a one-line reproduce command.
```

## Target status

| Target | License | Emits | Status |
|---|---|---|---|
| **Kotaemon** (Cinnamon Labs) | Apache-2.0 | span-level citations (`CiteEvidence`: verbatim source substrings) | ✅ **Scored** — 21 healthcare cases on claude-sonnet-5. Provenance + attribution **18/18 source-scoped**; caught a fabricated citation + a failed abstention on an adversarial case; surfaced a metric-design finding. See [`../showcase/kotaemon/FINDINGS.md`](../showcase/kotaemon/FINDINGS.md). |
| **AnythingLLM** (Mintplex Labs) | MIT | retrieved **source chunks** via REST API (not span-level citations) | 🟡 **PARTIAL** — runs as a Docker container, Anthropic-configured, healthy; API needs a dev key (one manual UI step). spancheck will score abstention, groundedness, cost/latency, and source attribution. A deliberate contrast to Kotaemon's FULL span-citations. Capture script ready (`showcase/anythingllm/`). |

## Appendix — reproducible Kotaemon setup (the hard-won recipe)

Kotaemon has no PyPI wheel and needs its **locked** environment; a fresh resolve or a hand-picked pin set breaks. On
this machine (Windows, Python 3.13 default, a TLS-inspecting proxy) the working recipe was:

```bash
# 1. Python 3.11 (Kotaemon's stack requires <3.12; provisioned via uv)
git clone --depth 1 https://github.com/Cinnamon/kotaemon.git      # Apache-2.0
cd kotaemon
export UV_NATIVE_TLS=1                                            # uv's rustls must trust the proxy CA
uv sync --native-tls                                             # installs the EXACT locked versions (py3.11 .venv)
uv pip install --native-tls --python .venv/Scripts/python.exe truststore

# 2. In the driver script, before any Kotaemon import:
import truststore; truststore.inject_into_ssl()                  # fixes tiktoken/anthropic TLS through the proxy
os.environ["THEFLOW_SETTINGS_MODULE"] = "theflow.settings.default"  # avoid the app's flowsettings.py (needs ktem)

# 3. Run its real citation pipeline (no vector DB needed — feed retrieved context in):
from kotaemon.llms import LCAnthropicChat
# load kotaemon/indices/qa/citation.py directly to bypass indices/__init__ (pulls the vector stack)
chat = LCAnthropicChat(api_key=KEY, model_name="claude-sonnet-5", temperature=None)  # 5-family rejects temperature
CitationPipeline(llm=chat).run(context=<retrieved text>, question=<q>)  # -> CiteEvidence.evidences (verbatim substrings)
```

The cloned repo and its `.venv` live **outside** this repo (`~/showcase-targets/kotaemon`); only our adapter, cases,
audit logs and findings are committed here.
