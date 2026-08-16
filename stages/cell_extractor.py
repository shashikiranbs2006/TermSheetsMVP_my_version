"""
stages/cell_extractor.py — Stage 2: Extract to Cells (native path)

Extracts table cells with geometry from native PDF pages using pdfplumber.
Returns RawCells per models/raw_cells.py.  No interpretation, no schema
mapping, no LLM.  This stage answers "can Python accurately see the table?"
and nothing more.

Library decision: pdfplumber only (Camelot not available in this environment)
-----------------------------------------------------------------------
pdfplumber's find_tables() + extract_tables() combination is used:

  - extract_tables()    → clean text per cell (pdfplumber's own parser
                          handles merged-cell text correctly)
  - find_tables().rows  → per-cell bounding box (x0, top, x1, bottom)

The bounding-box-only approach via crop().extract_text() was tested but
discarded: in cells where a date string overlaps a numeric value (a
known artefact of the Orange termsheet layout — Strike/Exit values
printed inside date-column bounds), crop() picks up neighbouring text,
producing values like "Jul. 60 Jul. 80" instead of "60 80". The
extract_tables() parser handles this correctly.

Merged cells (pdfplumber returns None in the text grid):
  - None in extract_tables() text → RawCell with text=None (blank ≠ "")
  - None in find_tables() cell bbox → the cell is structurally merged;
    we still emit a RawCell with geometry=None to preserve the row/col
    slot so downstream stage 3/4 can reconstruct the merged span.

Non-table content (section headers, cover objective text, etc.):
  - Extracted via page.extract_words() after removing table regions,
    producing word-level RawCells with single-word text and tight bboxes.
  - source="pdfplumber" for all cells from this extractor.

Geometry coordinate system: pdfplumber points (72 DPI), origin top-left.
  x = x0 (left edge), y = top (top edge), width = x1-x0, height = bottom-top
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pdfplumber

from models.page_manifest import PageManifest
from models.raw_cells import RawCell, RawCells

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_PATH = Path("data/intermediates/raw_cells.json")


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _cells_from_table(
    page: pdfplumber.page.Page,
    table_index: int,
) -> list[RawCell]:
    """
    Extract RawCells from one pdfplumber table object.

    Strategy:
      - text  comes from extract_tables()[table_index]  (clean, merged-aware)
      - bbox  comes from find_tables()[table_index].rows (structural geometry)

    Both sources are indexed identically (same table, same row, same column).
    """
    found_tables = page.find_tables()
    text_tables  = page.extract_tables()

    if table_index >= len(found_tables) or table_index >= len(text_tables):
        return []

    found = found_tables[table_index]
    text_grid = text_tables[table_index]

    cells: list[RawCell] = []

    for row_idx, (struct_row, text_row) in enumerate(
        zip(found.rows, text_grid)
    ):
        for col_idx, (cell_bbox, cell_text) in enumerate(
            zip(struct_row.cells, text_row)
        ):
            # Normalise text: None stays None (blank ≠ ""); strip whitespace
            if cell_text is not None:
                stripped = cell_text.strip()
                text_val: str | None = stripped if stripped else None
            else:
                text_val = None

            # Geometry from structural cell bbox
            if cell_bbox is not None:
                x0, top, x1, bottom = cell_bbox
                x      = float(x0)
                y      = float(top)
                width  = float(x1 - x0)
                height = float(bottom - top)
            else:
                # Merged span — preserve slot with zero geometry so the
                # row/col position is not lost
                x = y = width = height = 0.0

            cells.append(RawCell(
                text=text_val,
                x=x,
                y=y,
                width=width,
                height=height,
                page_no=page.page_number,
                source="pdfplumber",
            ))

    return cells


def _non_table_cells(
    page: pdfplumber.page.Page,
    cell_bboxes: list[tuple[float, float, float, float]],
) -> list[RawCell]:
    """
    Extract word-level RawCells from page regions not covered by any table cell.
    Covers section headers, cover objectives, event definitions, un-tabled fields, etc.

    Each word becomes one RawCell with tight bbox geometry.
    """
    words = page.extract_words()
    cells: list[RawCell] = []

    for word in words:
        wx0     = float(word["x0"])
        wtop    = float(word["top"])
        wx1     = float(word["x1"])
        wbottom = float(word["bottom"])

        # Skip words that fall inside any cell bbox (already captured by table extraction)
        inside_cell = any(
            cx0 - 1.0 <= wx0 and wtop >= ctop - 1.0 and wx1 <= cx1 + 1.0 and wbottom <= cbot + 1.0
            for cx0, ctop, cx1, cbot in cell_bboxes
        )
        if inside_cell:
            continue

        text_val: str | None = word["text"].strip() or None

        cells.append(RawCell(
            text=text_val,
            x=wx0,
            y=wtop,
            width=wx1 - wx0,
            height=wbottom - wtop,
            page_no=page.page_number,
            source="pdfplumber",
        ))

    return cells


def _extract_page(page: pdfplumber.page.Page) -> list[RawCell]:
    """Extract all RawCells from a single native page."""
    found_tables = page.find_tables()

    # Collect individual cell bboxes from all tables
    cell_bboxes: list[tuple[float, float, float, float]] = []
    for ft in found_tables:
        for row in ft.rows:
            for cell in row.cells:
                if cell is not None:
                    cell_bboxes.append(cell)

    all_cells: list[RawCell] = []

    # Table cells (geometry + clean text)
    for ti in range(len(found_tables)):
        all_cells.extend(_cells_from_table(page, ti))

    # Non-table words (headers, labels, free text, un-tabled text)
    all_cells.extend(_non_table_cells(page, cell_bboxes))

    return all_cells


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_cells(
    pdf_path: str | Path,
    manifests: Sequence[PageManifest],
) -> RawCells:
    """
    Extract table and non-table cells from all native pages.

    Args:
        pdf_path:  Path to the source PDF.
        manifests: PageManifest list from Stage 1.  Only pages with
                   route="native" are processed; scanned pages are skipped.

    Returns:
        RawCells containing all extracted cells in document order.

    Raises:
        FileNotFoundError: if pdf_path does not exist.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Build set of 1-based native page numbers for O(1) lookup
    native_pages = {m.page_no for m in manifests if m.route == "native"}

    all_cells: list[RawCell] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.page_number not in native_pages:
                continue  # scanned page — skip (OCR path not implemented yet)
            all_cells.extend(_extract_page(page))

    return RawCells(cells=all_cells)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist(
    raw_cells: RawCells,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """
    Write RawCells to JSON for Stage 3 consumption.

    Args:
        raw_cells:   RawCells produced by extract_cells().
        output_path: Destination file path.

    Returns:
        The resolved output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        raw_cells.model_dump_json(indent=2), encoding="utf-8"
    )
    return output_path


# ---------------------------------------------------------------------------
# Convenience run function
# ---------------------------------------------------------------------------


def run(
    pdf_path: str | Path,
    manifests: Sequence[PageManifest],
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    quiet: bool = False,
) -> RawCells:
    """
    Extract cells, persist, print summary.

    Returns:
        The RawCells produced.
    """
    raw_cells = extract_cells(pdf_path, manifests)
    out = persist(raw_cells, output_path)

    if not quiet:
        total = len(raw_cells.cells)
        non_blank = sum(1 for c in raw_cells.cells if c.text is not None)
        blank = total - non_blank
        print(f"Extracted {total} cells: {non_blank} with text, {blank} blank/merged")
        print(f"Persisted -> {out}")

    return raw_cells
