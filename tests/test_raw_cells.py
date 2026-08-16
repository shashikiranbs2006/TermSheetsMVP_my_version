"""
tests/test_raw_cells.py — Tests for Stage 2 RawCell / RawCells contracts.

Covers:
  - Valid RawCell with all fields.
  - text=None for genuinely blank cells (blank ≠ "").
  - source=None when provenance is unknown.
  - RawCells container with mixed cells.
  - Invalid source value rejection.
"""

import pytest
from pydantic import ValidationError

from models.raw_cells import RawCell, RawCells


class TestRawCellValid:
    def test_full_cell(self):
        cell = RawCell(
            text="65",
            x=10.0, y=20.0, width=50.0, height=15.0,
            page_no=3,
            source="pdfplumber",
        )
        assert cell.text == "65"
        assert cell.source == "pdfplumber"

    def test_blank_text_is_none_not_empty_string(self):
        """Blank ≠ '' — a genuinely blank cell must carry None, not ''."""
        cell = RawCell(text=None, x=0.0, y=0.0, width=10.0, height=5.0, page_no=1)
        assert cell.text is None

    def test_omitted_text_defaults_to_none(self):
        cell = RawCell(x=0.0, y=0.0, width=10.0, height=5.0, page_no=1)
        assert cell.text is None

    def test_source_none_allowed(self):
        """source may be None when provenance cannot be determined."""
        cell = RawCell(x=0.0, y=0.0, width=10.0, height=5.0, page_no=1, source=None)
        assert cell.source is None

    def test_camelot_source(self):
        cell = RawCell(x=0.0, y=0.0, width=10.0, height=5.0, page_no=1, source="camelot")
        assert cell.source == "camelot"

    def test_ocr_source(self):
        cell = RawCell(x=0.0, y=0.0, width=10.0, height=5.0, page_no=1, source="ocr")
        assert cell.source == "ocr"

    def test_serialisation_round_trip(self):
        cell = RawCell(text="hello", x=1.0, y=2.0, width=3.0, height=4.0, page_no=2, source="ocr")
        restored = RawCell.model_validate(cell.model_dump())
        assert restored == cell


class TestRawCellInvalid:
    def test_invalid_source_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            RawCell(x=0.0, y=0.0, width=10.0, height=5.0, page_no=1, source="tesseract")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source",) for e in errors)

    def test_missing_page_no_raises(self):
        with pytest.raises(ValidationError):
            RawCell(x=0.0, y=0.0, width=10.0, height=5.0)

    def test_missing_geometry_raises(self):
        with pytest.raises(ValidationError):
            RawCell(page_no=1)


class TestRawCells:
    def test_empty_cells_list_accepted(self):
        rc = RawCells(cells=[])
        assert rc.cells == []

    def test_mixed_cells(self):
        cells = [
            RawCell(text="65", x=0.0, y=0.0, width=10.0, height=5.0, page_no=1, source="pdfplumber"),
            RawCell(text=None, x=10.0, y=0.0, width=10.0, height=5.0, page_no=1, source="pdfplumber"),
        ]
        rc = RawCells(cells=cells)
        assert len(rc.cells) == 2
        assert rc.cells[1].text is None
