"""Package-shape smoke tests: it imports, exposes its public surface, and the CLI resolves.

Behavioural coverage of the measurement core lives in test_core.py.
"""
import subprocess
import sys

import pytest

import spancheck


def test_version_is_exposed():
    assert isinstance(spancheck.__version__, str) and spancheck.__version__


def test_public_surface_is_importable():
    for name in ["Case", "evaluate", "adapter", "Run", "Scorecard", "gate", "diff"]:
        assert hasattr(spancheck, name), f"missing public name: {name}"


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError):
        _ = spancheck.does_not_exist


def test_cli_version_runs():
    out = subprocess.run([sys.executable, "-m", "spancheck.cli", "--version"],
                         capture_output=True, text=True)
    assert out.returncode == 0
    assert "spancheck" in out.stdout
