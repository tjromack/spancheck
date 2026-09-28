# showcase/ — spancheck pointed at other people's real projects

A field report: running spancheck against real, published, third-party RAG applications to demonstrate that it is
system- and corpus-agnostic. Methodology, framing rules, and target status are in
[`../docs/EXTERNAL-SHOWCASE.md`](../docs/EXTERNAL-SHOWCASE.md).

- **`corpus/`** — five public healthcare documents from **Wikipedia (CC BY-SA)**, each with its source URL and
  retrieval date. Test-fixture data only; attribution is in every file.
- **`<target>/`** (added per target) — our adapter, cases, committed audit log, and a short `FINDINGS.md`. Third-party
  project code is **not** vendored here; it is cloned separately (see the runbook).

Framing: the hero is spancheck's generality, not any target's quality — neutral, reproducible, small-set measurements.
This is a field report, not a benchmark.
