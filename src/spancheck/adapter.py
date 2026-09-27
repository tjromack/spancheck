"""The thin adapter contract — the seam between spancheck and any system under test.

Design pin #2 (no provider lock-in) and #3 (every metric computable offline from a captured run) both live here:
a system's answer is normalised **once** into a typed `Output` that carries everything the metrics need
(the answer, the retrieved contexts, the citations, token/cost usage, and latency), so scoring never has to
call the system again.

`spancheck` never hard-codes a vendor. A caller supplies a plain `input -> answer` callable; `adapter()` wraps it,
times it, and normalises whatever it returns. The return may be:

  - a **str** — just the answer text;
  - a **dict** — with any of `answer`/`text`, `contexts`/`context`, `citations`, `usage`, `latency_ms`, `abstained`;
  - an **Output** — already normalised (idempotent).

Rewritten from evallab's loose "str-or-dict" handling into a pinned dataclass so cost/latency and citations are
first-class and always present (see LINEAGE.md, DECISIONS.md AB-DEC 006).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict


@dataclass
class Output:
    """The normalised result of one system call — the single shape every grader reads.

    `citations` is carried through as-is in Phase 1; its shape is firmed up by the citation-span verifier
    (Phase 2). `abstained` is an explicit signal when the system provides one; when it is None the graders
    infer abstention from the answer text.
    """
    answer: str = ""
    contexts: list = field(default_factory=list)   # retrieved context passages the answer should be grounded in
    citations: list = field(default_factory=list)  # citations backing the answer (span shape fixed in Phase 2)
    sources: dict = field(default_factory=dict)     # {source_id: full text} — enables source-scoped provenance
    usage: dict = field(default_factory=dict)       # e.g. {"input_tokens", "output_tokens", "cost_usd"}
    latency_ms: float | None = None                 # wall-clock for the call; filled by adapter/evaluate if absent
    abstained: bool | None = None                   # explicit abstention signal, if the system emits one
    raw: object = None                              # the untouched original return, for the audit log

    def to_dict(self) -> dict:
        d = asdict(self)
        # `raw` may not be JSON-serialisable; keep a string fallback for the audit log rather than crash.
        try:
            import json
            json.dumps(d["raw"])
        except (TypeError, ValueError):
            d["raw"] = repr(self.raw)
        return d


def normalize(value) -> Output:
    """Coerce a system's return (str | dict | Output) into an Output. Idempotent on Output."""
    if isinstance(value, Output):
        return value
    if isinstance(value, dict):
        answer = value.get("answer", value.get("text", ""))
        ctx = value.get("contexts", value.get("context", []))
        if not isinstance(ctx, list):
            ctx = [ctx] if ctx else []
        citations = value.get("citations", [])
        if not isinstance(citations, list):
            citations = [citations]
        sources = value.get("sources", {}) or {}
        if isinstance(sources, dict):
            sources = {str(k): str(v) for k, v in sources.items()}
        else:
            sources = {}
        return Output(
            answer="" if answer is None else str(answer),
            contexts=[str(c) for c in ctx],
            citations=citations,
            sources=sources,
            usage=dict(value.get("usage", {}) or {}),
            latency_ms=value.get("latency_ms"),
            abstained=value.get("abstained"),
            raw=value,
        )
    # a bare string (or anything else) is just the answer text
    return Output(answer="" if value is None else str(value), raw=value)


def adapter(fn, *, capture_time: bool = True):
    """Wrap a caller's `input -> result` callable so it returns a normalised, timed `Output`.

    Using `adapter()` is optional — `evaluate()` normalises and times its system either way — but it lets a caller
    attach usage/citations at the source and hand `evaluate` a system that already speaks the contract.
    """
    def run(inp) -> Output:
        start = time.perf_counter()
        result = fn(inp)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        out = normalize(result)
        if capture_time and out.latency_ms is None:
            out.latency_ms = round(elapsed_ms, 3)
        return out
    return run
