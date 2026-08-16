"""
main.py — WBCIS Termsheet Extraction Pipeline CLI.

Usage:
    python main.py docs/source/Orange_TermSheet.pdf
    python main.py <path-to-pdf> [--intermediates-dir <dir>] [--quiet]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stages.pipeline import run_pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WBCIS Termsheet Extraction & Validation Pipeline"
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the WBCIS Annexure 3 termsheet PDF file",
    )
    parser.add_argument(
        "--intermediates-dir",
        "-o",
        type=str,
        default="data/intermediates",
        help="Directory to store intermediate artifacts (default: data/intermediates)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress intermediate logging output",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    pdf_file = Path(args.pdf_path)
    if not pdf_file.exists():
        print(f"Error: PDF file does not exist at '{pdf_file}'", file=sys.stderr)
        return 1

    try:
        validated = run_pipeline(
            pdf_path=pdf_file,
            intermediates_dir=args.intermediates_dir,
            quiet=args.quiet,
        )
        return 0
    except Exception as exc:
        print(f"\nPipeline execution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
