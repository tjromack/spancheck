# Field report — spancheck × AnythingLLM (healthcare corpus): an honest blocker

**Status: pre-flight blocked in this environment.** AnythingLLM stood up and most of it worked — but document
ingestion failed, so the corpus could never be embedded and the scored run could not proceed. This is written down as
a real outcome, not hidden: integrating with third-party systems sometimes hits a wall you time-box and walk away from.

## What worked
- **Container up, healthy, Anthropic-configured.** `mintplexlabs/anythingllm` (MIT) on `:3001`; logs confirm the
  Anthropic SDK is active — and unlike Kotaemon, the container's outbound HTTPS worked through the network's
  TLS-inspecting proxy (it synced remote model + pricing data).
- **The REST API and the dev API key work.** Workspace creation, `/auth`, and the chat endpoint all returned 200; the
  chat response shape is known (`textResponse`, `sources`, `metrics`) — confirming AnythingLLM is a **PARTIAL** target
  (retrieved source *chunks*, not span-level citations — the intended contrast with Kotaemon's FULL span-citations).

## The blocker
- Every document ingestion call (`/document/raw-text`, and the collector directly) failed: the backend returns
  `500 {"error":"Response could not be completed"}`, and the internal collector returns
  `400 {"msg":"Failed integrity signature check."}` to an unsigned probe. The collector *does* receive the backend's
  call (it logs its tokenizer initialising) and then fails **without surfacing the real error** in its logs.
- Setting the backend↔collector signing secret (`SIG_KEY` / `SIG_SALT`) and restarting did not resolve it. The most
  likely remaining cause is the collector's processing/embedding step hitting the TLS proxy (the recurring failure mode
  on this machine — `curl`/OS-trust works, but tools with their own TLS do not), but AnythingLLM's collector does not
  log enough to confirm it, and further debugging exceeds the pre-flight time-box.

## The fix path (not taken here — a deliberate time-box call)
- Export the network's proxy CA from the Windows trust store and mount it into the container as `NODE_EXTRA_CA_CERTS`
  so the collector's Node process trusts the proxy; **or** run on a network without TLS inspection; **or** pre-seed the
  embedder model so ingestion needs no download.

## Why this belongs in the case study
This is chapter 2 of "evaluating in the wild," and its lesson is the honest one: **not every real system cooperates,
and knowing when to stop is part of the discipline.** The contrast is the content — Kotaemon (Python) fought hard and
cracked (a FULL, scored run with real findings); AnythingLLM (Docker) stood up cleanly but its document collector is
opaquely broken behind this network's proxy. Two real systems, two different failure modes, both documented. The
pre-flight/time-box protocol is exactly what kept either from becoming an open-ended sink.
