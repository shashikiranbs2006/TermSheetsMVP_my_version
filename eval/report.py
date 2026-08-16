"""
eval/report.py — Terminal formatter for EvalResult lists.

Produces human-readable PASS / FAIL / WARN lines, then a summary.
Column-aligned for readability in narrow terminals.

Example output:
  PASS  document.crop
  PASS  document.district
  FAIL  perils[1].structure.rate_1          expected=56.25        actual=55.00
  WARN  perils[0].structure.extra_key       (extra field in actual, unverified)

  ─────────────────────────────────────────────
  PASS: 47   FAIL: 1   WARN: 2   TOTAL: 50
"""

from __future__ import annotations

import sys
from typing import IO

from eval.evaluator import EvalResult, Verdict


# ANSI colour codes — gracefully disabled when not in a TTY
def _supports_colour(stream: IO) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


_COLOURS = {
    Verdict.PASS: "\033[32m",   # green
    Verdict.FAIL: "\033[31m",   # red
    Verdict.WARN: "\033[33m",   # yellow
}
_RESET = "\033[0m"

_PATH_WIDTH = 55
_VAL_WIDTH = 20


def _colour(text: str, verdict: Verdict, use_colour: bool) -> str:
    if not use_colour:
        return text
    return f"{_COLOURS[verdict]}{text}{_RESET}"


def _fmt_value(v) -> str:
    if v is None:
        return "null"
    s = str(v)
    if len(s) > _VAL_WIDTH:
        s = s[:_VAL_WIDTH - 1] + "…"
    return s


def format_results(
    results: list[EvalResult],
    *,
    show_pass: bool = True,
    stream: IO = sys.stdout,
) -> None:
    """
    Print a formatted report to `stream`.

    Args:
        results:    List from evaluator.compare().
        show_pass:  If False, PASS lines are suppressed (show only failures).
        stream:     Output stream; defaults to stdout.
    """
    use_colour = _supports_colour(stream)

    for r in results:
        if r.verdict == Verdict.PASS and not show_pass:
            continue

        label = _colour(f"{r.verdict.value:<4}", r.verdict, use_colour)
        path  = r.path.ljust(_PATH_WIDTH)

        if r.verdict == Verdict.PASS:
            print(f"{label}  {path}", file=stream)
        elif r.verdict == Verdict.FAIL:
            exp = _fmt_value(r.expected).ljust(_VAL_WIDTH)
            act = _fmt_value(r.actual).ljust(_VAL_WIDTH)
            print(f"{label}  {path}  expected={exp}  actual={act}", file=stream)
        else:  # WARN
            note = f"  ({r.note})" if r.note else ""
            exp = _fmt_value(r.expected).ljust(_VAL_WIDTH)
            act = _fmt_value(r.actual).ljust(_VAL_WIDTH)
            print(f"{label}  {path}  expected={exp}  actual={act}{note}", file=stream)

    # Summary line
    counts = {"PASS": 0, "FAIL": 0, "WARN": 0}
    for r in results:
        counts[r.verdict.value] += 1
    total = sum(counts.values())
    bar = "-" * 60
    print(f"\n{bar}", file=stream)
    pass_s  = _colour(f"PASS: {counts['PASS']}", Verdict.PASS, use_colour)
    fail_s  = _colour(f"FAIL: {counts['FAIL']}", Verdict.FAIL, use_colour)
    warn_s  = _colour(f"WARN: {counts['WARN']}", Verdict.WARN, use_colour)
    print(f"{pass_s}   {fail_s}   {warn_s}   TOTAL: {total}", file=stream)
