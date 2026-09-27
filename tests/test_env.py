"""The tiny .env loader: it reads keys into os.environ, never overwrites a real env var, and no-ops when absent."""
from __future__ import annotations

import os

from spancheck._env import load_dotenv


def test_loads_keys_without_overwriting_existing(tmp_path, monkeypatch):
    monkeypatch.delenv("SPANCHECK_TEST_NEW", raising=False)
    monkeypatch.setenv("SPANCHECK_TEST_EXISTING", "real")
    env = tmp_path / ".env"
    env.write_text('SPANCHECK_TEST_NEW=from_file\nSPANCHECK_TEST_EXISTING="ignored"\n# a comment\n\n', encoding="utf-8")
    load_dotenv(str(env))
    assert os.environ["SPANCHECK_TEST_NEW"] == "from_file"      # picked up
    assert os.environ["SPANCHECK_TEST_EXISTING"] == "real"      # real env var wins


def test_missing_file_is_a_noop():
    load_dotenv("definitely_not_a_real_file.env")  # must not raise
