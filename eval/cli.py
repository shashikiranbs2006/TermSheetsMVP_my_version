"""
eval/cli.py — CLI entry point for the eval harness.

Usage:
    python -m eval.cli <expected.json> <actual.json> [--failures-only]

    python -m eval.cli eval/fixtures/orange_jhalawar_gt.json actual_output.json
    python -m eval.cli eval/fixtures/orange_jhalawar_gt.json actual_output.json --failures-only

Exit codes:
    0 — no FAILs (WARNs are allowed)
    1 — one or more FAILs
    2 — argument / file error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.evaluator import compare, summary
from eval.report import format_results


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    failures_only = "--failures-only" in args
    positional = [a for a in args if not a.startswith("--")]

    if len(positional) != 2:
        print(
            "Usage: python -m eval.cli <expected.json> <actual.json> [--failures-only]",
            file=sys.stderr,
        )
        return 2

    expected_path, actual_path = Path(positional[0]), Path(positional[1])

    for p in (expected_path, actual_path):
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            return 2

    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        actual   = json.loads(actual_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON — {exc}", file=sys.stderr)
        return 2

    results = compare(expected, actual)
    format_results(results, show_pass=not failures_only)

    counts = summary(results)
    return 1 if counts["FAIL"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
