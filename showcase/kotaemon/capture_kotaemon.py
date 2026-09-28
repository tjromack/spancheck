"""Capture Kotaemon's real answer+citation output over our healthcare corpus, for spancheck to score offline.

Runs in Kotaemon's own venv (see docs/EXTERNAL-SHOWCASE.md for setup). For each question it:
  1. retrieves the top-k passages from the corpus with a small built-in BM25 (the "(a)" design: our retrieval),
  2. answers with Kotaemon's LCAnthropicChat over Kotaemon's own QA prompt (DEFAULT_QA_TEXT_PROMPT), and
  3. cites with Kotaemon's real CitationPipeline (CiteEvidence: verbatim source substrings),
then tags each citation with the source document it was found in (source-scoped provenance) and writes capture.json.

Kotaemon's answer prompt is reproduced verbatim and attributed. No spancheck import here — this only captures outputs.
"""
from __future__ import annotations

import json, math, os, re, sys, time, importlib.util
from collections import Counter
from pathlib import Path

import truststore
truststore.inject_into_ssl()
os.environ["THEFLOW_SETTINGS_MODULE"] = "theflow.settings.default"

SPAN = r"C:\ai\spancheck"
for line in open(os.path.join(SPAN, ".env"), encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

KT = os.path.expanduser(r"~\showcase-targets\kotaemon\libs\kotaemon")
sys.path.insert(0, KT)
from kotaemon.base import HumanMessage
from kotaemon.llms import LCAnthropicChat
spec = importlib.util.spec_from_file_location("kt_citation", os.path.join(KT, "kotaemon", "indices", "qa", "citation.py"))
_m = importlib.util.module_from_spec(spec); spec.loader.exec_module(_m)
CitationPipeline = _m.CitationPipeline

# Kotaemon's own QA prompt (kotaemon/indices/qa/citation_qa.py::DEFAULT_QA_TEXT_PROMPT), reproduced verbatim.
QA_PROMPT = (
    "Use the following pieces of context to answer the question at the end in detail with clear explanation. "
    "If you don't know the answer, just say that you don't know, don't try to make up an answer. Give answer in "
    "English.\n\n{context}\nQuestion: {question}\nHelpful Answer:"
)

# ---- corpus + a tiny BM25 (no dependency) ----
CORPUS_DIR = Path(SPAN) / "showcase" / "corpus"
LABELS = {"medicare.md": "Medicare", "medicaid.md": "Medicaid",
          "health-insurance-us.md": "Health insurance (US)", "hipaa.md": "HIPAA",
          "prior-authorization.md": "Prior authorization"}
SOURCES = {label: (CORPUS_DIR / f).read_text(encoding="utf-8") for f, label in LABELS.items()}

_tok = lambda s: re.findall(r"[a-z0-9]+", s.lower())


def chunks_of(text):
    body = "\n".join(l for l in text.splitlines() if not l.startswith("#") and not l.startswith("_Source"))
    return [c.strip() for c in re.split(r"\n\s*\n", body) if len(c.strip()) > 80]


CHUNKS = []  # (label, text)
for label, text in SOURCES.items():
    for c in chunks_of(text):
        CHUNKS.append((label, c))


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [_tok(d) for d in docs]; self.N = len(docs)
        self.avgdl = sum(len(d) for d in self.docs) / max(1, self.N)
        df = {}
        for d in self.docs:
            for w in set(d): df[w] = df.get(w, 0) + 1
        self.idf = {w: math.log(1 + (self.N - v + 0.5) / (v + 0.5)) for w, v in df.items()}

    def score(self, q, i):
        c = Counter(self.docs[i]); dl = len(self.docs[i]); s = 0.0
        for w in _tok(q):
            if w not in c: continue
            f = c[w]
            s += self.idf.get(w, 0) * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def topk(self, q, k):
        return sorted(range(self.N), key=lambda i: self.score(q, i), reverse=True)[:k]


bm25 = BM25([c for _, c in CHUNKS])


def source_of(evidence):
    """Which corpus document contains this evidence span (normalised)?"""
    ev = re.sub(r"\s+", " ", evidence).strip().lower()
    for label, text in SOURCES.items():
        if ev and ev in re.sub(r"\s+", " ", text).lower():
            return label
    return None


def main():
    chat = LCAnthropicChat(api_key=os.environ["ANTHROPIC_API_KEY"], model_name="claude-sonnet-5", temperature=None)
    citer = CitationPipeline(llm=chat)
    cases = [json.loads(l) for l in (Path(SPAN) / "showcase" / "kotaemon" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    lim = int(os.environ.get("CAPTURE_LIMIT", "0"))
    if lim:
        cases = cases[:lim]

    captured = []
    for i, case in enumerate(cases, 1):
        q = case["input"]
        idxs = bm25.topk(q, 4)
        retrieved = [CHUNKS[j] for j in idxs]
        context = "\n\n".join(f"[{label}] {text}" for label, text in retrieved)

        t0 = time.perf_counter()
        answer = chat([HumanMessage(content=QA_PROMPT.format(context=context, question=q))]).text
        cite = citer.run(context=context, question=q)
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        citations = []
        if cite is not None:
            for ev in cite.evidences:
                citations.append({"span": ev, "source_id": source_of(ev)})

        captured.append({
            "id": case["id"], "input": q, "category": case.get("category", "default"),
            "expected": case.get("expected"), "meta": case.get("meta") or {},
            "output": {
                "answer": answer,
                "contexts": [text for _, text in retrieved],
                "sources": SOURCES,
                "citations": citations,
                "latency_ms": latency_ms,
                "raw": {"provider": "anthropic", "model": "claude-sonnet-5", "retrieved_sources": [l for l, _ in retrieved]},
            },
        })
        print(f"  [{i}/{len(cases)}] {case['id']}: {len(citations)} citations, {latency_ms}ms")

    out = Path(SPAN) / "showcase" / "kotaemon" / "capture.json"
    out.write_text(json.dumps(captured, indent=2), encoding="utf-8")
    print(f"\nwrote {out} ({len(captured)} cases)")


if __name__ == "__main__":
    main()
