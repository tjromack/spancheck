"""A tiny, deterministic demo system-under-test, so `spancheck run` is demonstrable from a clean clone with no user
code and no API key.

`system(q)` is a naive keyword-retrieval "RAG" over a fixed three-clause corpus: it retrieves the best-matching clause,
answers with it, and cites it — or abstains when nothing in the corpus matches. It is a *fake* target used to exercise
spancheck end to end; spancheck evaluates any `input -> output` callable, this is just one.

Try it:
    spancheck run examples/cases.jsonl --target spancheck.demo:system --out audit.json
    spancheck gate audit.json citation_accuracy=1.0 abstention_correct=1.0
"""
from __future__ import annotations

from ._text import content_words, words

CORPUS = [
    "Either party may terminate the agreement with 30 days written notice.",
    "Invoices are payable within 45 days of receipt.",
    "This agreement is governed by the laws of the State of Delaware.",
]


def system(q):
    """Retrieve the best-matching clause and answer with it (citing it), or abstain if nothing matches."""
    qw = set(content_words(q))
    best, best_overlap = None, 0
    for clause in CORPUS:
        overlap = len(qw & words(clause))
        if overlap > best_overlap:
            best, best_overlap = clause, overlap

    if best is None:
        return {"answer": "I don't know — that isn't in the documents.",
                "contexts": CORPUS, "abstained": True,
                "usage": {"input_tokens": 40, "output_tokens": 12}, "latency_ms": 5.0}

    return {
        "answer": best,
        "contexts": [best],
        "citations": [{"span": best, "claim": best}],
        "usage": {"input_tokens": 40, "output_tokens": 20},
        "latency_ms": 6.0,
    }
