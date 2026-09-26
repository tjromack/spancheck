"""The provider seam for the LLM-judge — no vendor is hard-coded (design pin #2).

A provider is any callable `provider(prompt: str) -> str` returning the model's raw text (ideally the JSON the prompt
asks for). The judge defaults to `provider=None`, which takes a deterministic offline path — so tests and CI never need
a key. A real model is opt-in via a caller-supplied callable; `anthropic_provider()` is a convenience that imports the
SDK **lazily**, only when called, so this package keeps no hard dependency on any vendor.
"""
from __future__ import annotations

import os


def anthropic_provider(model: str = "claude-sonnet-5", api_key: str | None = None, max_tokens: int = 512):
    """An optional provider backed by the Anthropic SDK. Imported lazily — calling this needs `anthropic` installed
    and an API key (arg or ANTHROPIC_API_KEY). Used for the keyed judge-calibration run; never imported otherwise."""
    def call(prompt: str) -> str:
        import anthropic  # lazy: no hard dependency, no import cost unless a real judge is used
        client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")

    call.model = model  # so a verdict can record which model produced it
    return call
