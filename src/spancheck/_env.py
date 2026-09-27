"""Tiny, dependency-free .env loader.

Reads KEY=VALUE lines from a .env file into os.environ **without overwriting** anything already set (a real
environment variable always wins). Called at CLI/calibration startup so a key placed in `.env` "just works" — no
python-dotenv dependency, no vendor lock-in. `.env` is gitignored; a key never enters the repo.
"""
from __future__ import annotations

import os


def load_dotenv(path: str = ".env") -> None:
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass
