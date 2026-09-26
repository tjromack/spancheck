"""spancheck CLI — a thin wrapper over the library (design pin #1: library-first, CLI-second).

Scaffold stage: the command surface is declared so the shape is fixed, but the subcommands
are not wired to an implementation yet (Phase 5, after the library lands). Running any
subcommand today prints where it is in the build.
"""
from __future__ import annotations

import argparse
import sys

from . import __version__

_PENDING = "not implemented yet — scaffold stage; see TODO.md"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spancheck",
        description="Score a grounded-answer system on citation accuracy, abstention correctness, "
                    "hallucination rate, cost and latency — with a compliance-readable audit log.",
    )
    p.add_argument("--version", action="version", version=f"spancheck {__version__}")
    sub = p.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run a test set against a target and capture an audit log")
    run.add_argument("cases", help="path to the cases file (jsonl)")
    run.add_argument("--target", required=True, help="module:callable adapter for the system under test")
    run.add_argument("--out", default="audit.json", help="where to write the audit log")

    score = sub.add_parser("score", help="recompute metrics from a cached audit log (no network)")
    score.add_argument("audit", help="path to a captured audit log")

    g = sub.add_parser("gate", help="pass/fail a run against thresholds (for CI)")
    g.add_argument("audit", help="path to a captured audit log")
    g.add_argument("--baseline", help="optional baseline audit log for regression gating")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    print(f"spancheck {args.command}: {_PENDING}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
