"""
models/raw_cells.py — Stage 2 output (Extract to Cells).

One RawCell per extracted table cell.  Geometry coordinates (x, y, width,
height) are in the coordinate system of the extraction tool (points for
pdfplumber; pixels for OCR paths).  The coordinate system is not normalised
here — that is a Stage 3/4 concern.

Design notes:
  - text is Optional[str]: genuinely blank cells carry None, never "".
    Blank ≠ empty string — these are different things in table extraction.
  - source is Optional: set to None only when provenance cannot be
    determined.  Callers should avoid producing None source where possible.
"""

from typing import Literal, Optional

from pydantic import BaseModel


class RawCell(BaseModel):
    """
    A single extracted table cell with geometry and extraction provenance.

    Attributes:
        text:    Cell content.  None for genuinely blank cells.
        x:       Left edge of bounding box in tool coordinate space.
        y:       Top edge of bounding box in tool coordinate space.
        width:   Bounding box width.
        height:  Bounding box height.
        page_no: 1-based page number the cell was extracted from.
        source:  Extraction tool that produced this cell.  None if unknown.
    """

    text: Optional[str] = None
    x: float
    y: float
    width: float
    height: float
    page_no: int
    source: Optional[Literal["pdfplumber", "camelot", "ocr"]] = None


class RawCells(BaseModel):
    """
    Stage 2 top-level output.  All cells extracted from a single document,
    preserving original order.
    """

    cells: list[RawCell]
