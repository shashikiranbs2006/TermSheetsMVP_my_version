"""
stages/ingest_router.py — Stage 1: Ingest & Route

Reads a PDF and classifies every page as "native" (selectable text) or
"scanned" (rasterised image, needs OCR).  Returns a list[PageManifest]
and optionally persists it to disk so Stage 2 can consume it without
re-running Stage 1.

Routing rule (spec-mandated, deterministic, no agents):

    text  = page.extract_text()
    route = "native" if len(text.strip()) > 50 else "scanned"

Rationale for threshold 50 (not >0):
    A page with only a page number, watermark, or header fragment can yield
    1–30 characters from pdfplumber even when the substantive content is
    rasterised.  50 chars is safely above such artefacts while remaining
    well below any real table content (observed minimum: ~1089 chars in the
    WBCIS sample set).

No OCR is performed here.  No cell extraction.  Routing decision only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pdfplumber

from models.page_manifest import PageManifest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEXT_THRESHOLD: int = 50
"""Minimum stripped-character count for a page to be routed "native"."""

DEFAULT_OUTPUT_PATH = Path("data/intermediates/page_manifest.json")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _route_page(page: pdfplumber.page.Page) -> str:
    """Return "native" or "scanned" for a single pdfplumber page."""
    text = page.extract_text() or ""
    return "native" if len(text.strip()) > TEXT_THRESHOLD else "scanned"


def route_pdf(pdf_path: str | Path) -> list[PageManifest]:
    """
    Open a PDF and return one PageManifest per page.

    Args:
        pdf_path: Absolute or relative path to the source PDF.

    Returns:
        List of PageManifest, one per page, in document order.
        page_no is 1-based.

    Raises:
        FileNotFoundError: if pdf_path does not exist.
        pdfplumber errors: propagated as-is (no silent swallowing).
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    manifests: list[PageManifest] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            route = _route_page(page)
            manifests.append(PageManifest(page_no=i + 1, route=route))

    return manifests


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist(
    manifests: list[PageManifest],
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """
    Write the PageManifest list to JSON so Stage 2 can consume it without
    re-running Stage 1.

    Output format: list of objects {"page_no": int, "route": str}

    Args:
        manifests:   List produced by route_pdf().
        output_path: Destination file path.  Parent directories are created
                     automatically.

    Returns:
        The resolved output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = [m.model_dump() for m in manifests]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def count_by_route(manifests: Sequence[PageManifest]) -> dict[str, int]:
    """Return {"native": N, "scanned": M} counts."""
    counts: dict[str, int] = {"native": 0, "scanned": 0}
    for m in manifests:
        counts[m.route] += 1
    return counts


# ---------------------------------------------------------------------------
# CLI convenience
# ---------------------------------------------------------------------------


def run(
    pdf_path: str | Path,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    quiet: bool = False,
) -> list[PageManifest]:
    """
    Route a PDF, persist the result, and print a summary.
    Intended for direct invocation:  python -m stages.ingest_router <pdf>

    Args:
        pdf_path:    Path to the source PDF.
        output_path: Where to write page_manifest.json.
        quiet:       Suppress printed output (useful in tests).

    Returns:
        The list[PageManifest] produced.
    """
    manifests = route_pdf(pdf_path)
    out = persist(manifests, output_path)
    if not quiet:
        counts = count_by_route(manifests)
        print(f"Routed {len(manifests)} pages: "
              f"native={counts['native']}  scanned={counts['scanned']}")
        print(f"Persisted -> {out}")
    return manifests


if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else "docs/source/Orange_TermSheet.pdf"
    out = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_OUTPUT_PATH)
    run(pdf, out)
