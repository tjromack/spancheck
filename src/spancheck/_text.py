"""Shared text helpers used by graders and the citation-span verifier.

Kept in one place so the deterministic checks agree on what a "word" is and how text is normalised.
Stdlib only.
"""
from __future__ import annotations

import re

WORD = re.compile(r"[a-z0-9]+")

STOP = set("the a an and or of to in on for is are was were be been it its this that with as at by from "
           "your you our we i they he she them his her their not no do does did have has had will would can "
           "could should may might must shall into over under about than then so if but".split())


def norm(s) -> str:
    """Lowercase and collapse all whitespace to single spaces — the normalisation used for span provenance."""
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def words(s) -> set:
    """All word tokens (lowercased) — used as the haystack when checking coverage."""
    return set(WORD.findall((s or "").lower()))


def content_words(s):
    """Meaningful tokens: lowercased words that aren't stopwords and are longer than two characters."""
    return [w for w in WORD.findall((s or "").lower()) if w not in STOP and len(w) > 2]


_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def sentences(text):
    """Split text into sentences (on ., !, ? and newlines), dropping fragments shorter than 16 chars."""
    return [s.strip() for s in _SENT.split(text or "") if len(s.strip()) > 15]
