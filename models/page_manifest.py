"""
models/page_manifest.py — Stage 1 output (Ingest & Route).

One PageManifest record per PDF page.  The pipeline reads this list to decide
whether a page feeds the native pdfplumber path or the OCR path.
No extraction logic lives here — this is a data contract only.
"""

from typing import Literal

from pydantic import BaseModel


class PageManifest(BaseModel):
    """
    Routing decision for a single PDF page.

    Attributes:
        page_no: 1-based page number within the source PDF.
        route:   "native"  — page contains selectable text; use pdfplumber/Camelot.
                 "scanned" — page is rasterised; OCR required before extraction.

    Validation:
        Any value for route other than "native" or "scanned" raises
        pydantic.ValidationError at construction time.
    """

    page_no: int
    route: Literal["native", "scanned"]
