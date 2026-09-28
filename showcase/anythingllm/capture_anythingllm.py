"""Capture AnythingLLM's real answer + retrieved sources over our healthcare corpus, for spancheck to score offline.

AnythingLLM (Mintplex Labs) runs as a Docker container exposing a REST API; it is configured to use Anthropic
(claude-sonnet-5) with its built-in embedder + LanceDB. We drive it entirely over local HTTP (no TLS proxy in play —
the container makes the Anthropic calls itself). It returns an answer + the retrieved **source chunks** (not span-level
citations), so this is a PARTIAL target: spancheck scores abstention, groundedness, cost/latency, and source
attribution. Contrast with Kotaemon (FULL, span-level citations).

Prereq: an API key in `spancheck/.anythingllm_key` (generated in the UI → Settings → Tools → Developer API). No
spancheck import here — this only captures outputs. Run from the spancheck repo root:

    python showcase/anythingllm/capture_anythingllm.py
"""
from __future__ import annotations

import json, os, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://localhost:3001/api/v1"
KEY = (ROOT / ".anythingllm_key").read_text(encoding="utf-8").strip()
HDR = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

LABELS = {"medicare.md": "Medicare", "medicaid.md": "Medicaid",
          "health-insurance-us.md": "Health insurance (US)", "hipaa.md": "HIPAA",
          "prior-authorization.md": "Prior authorization"}
SOURCES = {label: (ROOT / "showcase" / "corpus" / f).read_text(encoding="utf-8") for f, label in LABELS.items()}


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=HDR, method=method)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:300]}


def source_of(chunk_text):
    ev = " ".join((chunk_text or "").split()).lower()[:200]
    for label, text in SOURCES.items():
        if ev and ev[:80] in " ".join(text.split()).lower():
            return label
    return None


def main():
    # 1. fresh workspace
    slug = "spancheck-healthcare"
    api("DELETE", f"/workspace/{slug}")  # ignore if absent
    st, ws = api("POST", "/workspace/new", {"name": "spancheck healthcare"})
    slug = (ws.get("workspace") or {}).get("slug", slug)
    print(f"workspace: {slug} (status {st})")
    # query mode + no LLM general knowledge, so it abstains when the docs don't answer
    api("POST", f"/workspace/{slug}/update", {"chatMode": "query", "openAiTemp": 0})

    # 2. add corpus as raw text, then embed
    locations = []
    for f, label in LABELS.items():
        st, doc = api("POST", "/document/raw-text",
                      {"textContent": SOURCES[label], "metadata": {"title": label, "docSource": label}})
        loc = ((doc.get("documents") or [{}])[0]).get("location")
        if loc:
            locations.append(loc)
        print(f"  added {label}: {loc} (status {st})")
    st, _ = api("POST", f"/workspace/{slug}/update-embeddings", {"adds": locations})
    print(f"embedded {len(locations)} docs (status {st})")

    # 3. run the cases
    cases = [json.loads(l) for l in (ROOT / "showcase" / "anythingllm" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    lim = int(os.environ.get("CAPTURE_LIMIT", "0"))
    if lim:
        cases = cases[:lim]

    captured = []
    for i, case in enumerate(cases, 1):
        q = case["input"]
        t0 = time.perf_counter()
        st, resp = api("POST", f"/workspace/{slug}/chat", {"message": q, "mode": "query"})
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        if i == 1:
            print("  (raw first response keys:", list(resp.keys()), ")")
        answer = resp.get("textResponse", resp.get("error", ""))
        srcs = resp.get("sources", []) or []
        contexts = [s.get("text") or s.get("chunk") or "" for s in srcs]
        # AnythingLLM returns retrieved chunks, not span citations — tag each with the doc it came from.
        citations = [{"span": (s.get("text") or s.get("chunk") or ""), "source_id": source_of(s.get("text") or s.get("chunk") or "")} for s in srcs]
        captured.append({
            "id": case["id"], "input": q, "category": case.get("category", "default"),
            "expected": case.get("expected"), "meta": case.get("meta") or {},
            "output": {"answer": answer, "contexts": contexts, "sources": SOURCES,
                       "citations": citations, "latency_ms": latency_ms,
                       "raw": {"provider": "anthropic", "model": "claude-sonnet-5", "n_sources": len(srcs)}},
        })
        print(f"  [{i}/{len(cases)}] {case['id']}: {len(srcs)} sources, {latency_ms}ms")

    out = ROOT / "showcase" / "anythingllm" / "capture.json"
    out.write_text(json.dumps(captured, indent=2), encoding="utf-8")
    print(f"\nwrote {out} ({len(captured)} cases)")


if __name__ == "__main__":
    main()
