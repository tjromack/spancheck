"""Scaffold smoke tests — the package installs, imports, and the CLI surface resolves.

These are deliberately minimal: they assert the shape is in place, not that any metric works
(the metrics land in Phase 1+; see TODO.md). Real behavioural tests — with the citation-span
verifier tested deepest — arrive with the code they cover.
"""
import subprocess
import sys

import pytest

import abstain


def test_version_is_exposed():
    assert isinstance(abstain.__version__, str) and abstain.__version__


def test_public_api_is_declared():
    # The public surface is named now so the build target is unambiguous.
    assert set(abstain.__all__) == {"Case", "evaluate", "adapter", "Run", "Scorecard", "gate", "diff"}


def test_declared_api_raises_informative_error_until_implemented():
    # Referencing a not-yet-built name fails loudly with guidance, not a bare ImportError.
    with pytest.raises(NotImplementedError):
        _ = abstain.evaluate


def test_unknown_attribute_still_raises_attribute_error():
    with pytest.raises(AttributeError):
        _ = abstain.does_not_exist


def test_cli_version_runs():
    out = subprocess.run([sys.executable, "-m", "abstain.cli", "--version"],
                         capture_output=True, text=True)
    assert out.returncode == 0
    assert "abstain" in out.stdout
