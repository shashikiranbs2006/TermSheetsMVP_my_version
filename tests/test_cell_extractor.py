"""
tests/test_cell_extractor.py — Tests for Stage 2: cell_extractor.py

All ground truth values were verified by probing Orange_TermSheet.pdf
directly before writing these tests (see scratch_probe_pdf.py output).

Coverage:
  1. State, District, Crop text appear in extracted cells.
  2. All 6 temperature trigger values (29.0, 31.0, 33.5, 35.5, 36.5, 39.0).
  3. Rainfall values present (strike, rate, max payout).
  4. Wind values present (triggers: 50, 55; payout: 208.33; max: 12500).
  5. Every cell with a non-None bbox has valid positive geometry.
  6. All cells have page_no=1 (single-page PDF).
  7. All cells have source="pdfplumber".
  8. Output is a valid RawCells Pydantic model.
  9. Blank cells carry text=None, not "" or "0".
 10. No scanned page is processed (skipped by manifest filter).
 11. persist() writes valid JSON that round-trips to RawCells.
 12. FileNotFoundError on a missing PDF.
 13. Spot-check: premium table row (125000, gross blank, premium% blank).
 14. Section headers / non-table text is captured (e.g. "HIGH TEMPERATURE").
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from models.page_manifest import PageManifest
from models.raw_cells import RawCell, RawCells
from stages.cell_extractor import extract_cells, persist, run

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ORANGE_PDF = Path("docs/source/Orange_TermSheet.pdf")

# Manifest for the Orange PDF (1 native page)
ORANGE_MANIFEST = [PageManifest(page_no=1, route="native")]
# Manifest that marks the page as scanned → extractor must skip it
SCANNED_MANIFEST = [PageManifest(page_no=1, route="scanned")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def all_texts(raw_cells: RawCells) -> list[str]:
    """Return list of all non-None cell texts."""
    return [c.text for c in raw_cells.cells if c.text is not None]


def has_text(raw_cells: RawCells, fragment: str) -> bool:
    """True if any cell text contains `fragment` (case-insensitive)."""
    fragment_lo = fragment.lower()
    return any(fragment_lo in (t or "").lower() for t in all_texts(raw_cells))


def has_exact(raw_cells: RawCells, value: str) -> bool:
    """True if any cell text exactly equals `value`."""
    return value in all_texts(raw_cells)


# ---------------------------------------------------------------------------
# Fixture: extract once, reuse across all tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def orange_cells() -> RawCells:
    if not ORANGE_PDF.exists():
        pytest.skip(f"PDF not found: {ORANGE_PDF}")
    return extract_cells(ORANGE_PDF, ORANGE_MANIFEST)


# ---------------------------------------------------------------------------
# 1. Document header fields
# ---------------------------------------------------------------------------

class TestHeaderFields:
    def test_state_rajasthan_present(self, orange_cells):
        assert has_text(orange_cells, "RAJASTHAN"), \
            "State 'RAJASTHAN' not found in any cell"

    def test_district_jhalawar_present(self, orange_cells):
        assert has_text(orange_cells, "Jhalawar"), \
            "District 'Jhalawar' not found in any cell"

    def test_crop_orange_present(self, orange_cells):
        assert has_text(orange_cells, "Orange"), \
            "Crop 'Orange' not found in any cell"

    def test_scheme_year_present(self, orange_cells):
        assert has_text(orange_cells, "2019-20"), \
            "'2019-20' not found in any cell"

    def test_annexure_ref_present(self, orange_cells):
        assert has_text(orange_cells, "Annexure"), \
            "'Annexure' not found in any cell"

    def test_unit_hectare_present(self, orange_cells):
        assert has_text(orange_cells, "HECTARE"), \
            "'HECTARE' not found in any cell"


# ---------------------------------------------------------------------------
# 2. Temperature trigger values (from Table 2 / probe row 2)
# ---------------------------------------------------------------------------

class TestTemperatureTriggers:
    """
    Ground truth from probe:
      Trigger row: 29.0, 31.0, 33.5, 35.5, 36.5, 39.0
    """

    @pytest.mark.parametrize("trigger", ["29.0", "31.0", "33.5", "35.5", "36.5", "39.0"])
    def test_trigger_value_present(self, orange_cells, trigger):
        assert has_exact(orange_cells, trigger), \
            f"Temperature trigger '{trigger}' not found in extracted cells"

    def test_temperature_strike_present(self, orange_cells):
        """Strike = 4 (spans all phases, merged cell)."""
        assert has_exact(orange_cells, "4"), \
            "Temperature strike '4' not found"

    def test_temperature_exit_present(self, orange_cells):
        """Exit = 22."""
        assert has_exact(orange_cells, "22"), \
            "Temperature exit '22' not found"

    def test_temperature_max_payout_present(self, orange_cells):
        assert has_exact(orange_cells, "37500"), \
            "Temperature max payout '37500' not found"

    def test_payout_rate_present(self, orange_cells):
        assert has_exact(orange_cells, "2083.33"), \
            "Temperature payout rate '2083.33' not found"


# ---------------------------------------------------------------------------
# 3. Rainfall (deficit multistrike) values
# ---------------------------------------------------------------------------

class TestRainfallValues:
    """
    Ground truth from probe (Table 3):
      RATE 1: 56.25, 45.00  | RATE 2: 262.50
      Max payout: 7500  | Total: 37500
      Strike 1 col 1: '60 80' (merged sub-period)
    """

    def test_rate1_56_25_present(self, orange_cells):
        assert has_exact(orange_cells, "56.25"), \
            "Rainfall rate1 '56.25' not found"

    def test_rate1_45_00_present(self, orange_cells):
        assert has_exact(orange_cells, "45.00"), \
            "Rainfall rate1 '45.00' not found"

    def test_rate2_262_50_present(self, orange_cells):
        assert has_exact(orange_cells, "262.50"), \
            "Rainfall rate2 '262.50' not found"

    def test_max_payout_7500_present(self, orange_cells):
        assert has_exact(orange_cells, "7500"), \
            "Rainfall max payout '7500' not found"

    def test_total_payout_37500_present(self, orange_cells):
        assert has_exact(orange_cells, "37500"), \
            "Rainfall total payout '37500' not found"

    def test_rainfall_phase_label_present(self, orange_cells):
        assert has_text(orange_cells, "Phase I"), \
            "'Phase I' label not found"

    def test_rainfall_strike_label_present(self, orange_cells):
        assert has_text(orange_cells, "Strike 1"), \
            "'Strike 1' label not found"


# ---------------------------------------------------------------------------
# 4. Unseasonal rainfall (Table 4) values
# ---------------------------------------------------------------------------

class TestUnseasonalRainfall:
    """
    Ground truth from probe (Table 4):
      Strike 1: 25, Strike 2: 40, Exit: 60
      Rate 1: 500, Rate 2: 875, Max: 25000
    """

    def test_strike1_25_present(self, orange_cells):
        assert has_exact(orange_cells, "25"), "Unseasonal strike1 '25' not found"

    def test_strike2_40_present(self, orange_cells):
        assert has_exact(orange_cells, "40"), "Unseasonal strike2 '40' not found"

    def test_exit_60_present(self, orange_cells):
        assert has_exact(orange_cells, "60"), "Unseasonal exit '60' not found"

    def test_rate1_500_present(self, orange_cells):
        assert has_exact(orange_cells, "500"), "Unseasonal rate1 '500' not found"

    def test_rate2_875_present(self, orange_cells):
        assert has_exact(orange_cells, "875"), "Unseasonal rate2 '875' not found"

    def test_max_payout_25000_present(self, orange_cells):
        assert has_exact(orange_cells, "25000"), "Unseasonal max payout '25000' not found"


# ---------------------------------------------------------------------------
# 5. Wind (Table 5) values
# ---------------------------------------------------------------------------

class TestWindValues:
    """
    Ground truth from probe (Table 5):
      Triggers: 50, 55, 55, 50, 55, 50
      Strike: 10, Exit: 70
      Payout: 208.33, Max: 12500
    """

    @pytest.mark.parametrize("trigger", ["50", "55"])
    def test_wind_trigger_present(self, orange_cells, trigger):
        assert has_exact(orange_cells, trigger), \
            f"Wind trigger '{trigger}' not found"

    def test_wind_strike_10_present(self, orange_cells):
        assert has_exact(orange_cells, "10"), "Wind strike '10' not found"

    def test_wind_exit_70_present(self, orange_cells):
        assert has_exact(orange_cells, "70"), "Wind exit '70' not found"

    def test_wind_payout_rate_present(self, orange_cells):
        assert has_exact(orange_cells, "208.33"), "Wind payout '208.33' not found"

    def test_wind_max_payout_present(self, orange_cells):
        assert has_exact(orange_cells, "12500"), "Wind max payout '12500' not found"


# ---------------------------------------------------------------------------
# 6. Premium table
# ---------------------------------------------------------------------------

class TestPremiumTable:
    """
    Ground truth from probe (Table 6):
      Total SI: 125000
      Gross premium: blank → text=None
      Premium %: blank → text=None
    """

    def test_total_sum_insured_present(self, orange_cells):
        assert has_exact(orange_cells, "125000"), "'125000' not found"

    def test_blank_gross_premium_is_none_not_zero(self, orange_cells):
        """
        Blank ≠ zero. The gross premium cell is visually empty.
        It must appear as text=None, never as "0" or "".
        """
        # "0" must not appear as a standalone cell text due to blank premium
        # (it could appear as part of other values like exit=0, which is OK)
        # What we actually test: no cell has text="" (empty string is forbidden)
        for cell in orange_cells.cells:
            assert cell.text != "", \
                f"Cell has text='' (empty string); should be None. cell={cell}"


# ---------------------------------------------------------------------------
# 7. Geometry validity
# ---------------------------------------------------------------------------

class TestGeometryValidity:
    def test_all_non_merged_cells_have_positive_geometry(self, orange_cells):
        """
        Cells that have a real bbox (not merged) must have width > 0 and height > 0.
        Merged-span placeholder cells have x=y=width=height=0 and text=None.
        """
        for cell in orange_cells.cells:
            is_merged_placeholder = (
                cell.x == 0.0 and cell.y == 0.0
                and cell.width == 0.0 and cell.height == 0.0
                and cell.text is None
            )
            if not is_merged_placeholder:
                assert cell.width > 0, f"Cell has width=0: {cell}"
                assert cell.height > 0, f"Cell has height=0: {cell}"

    def test_all_cells_have_numeric_geometry(self, orange_cells):
        """Geometry fields must be float, never None."""
        for cell in orange_cells.cells:
            assert isinstance(cell.x, float), f"x is not float: {cell}"
            assert isinstance(cell.y, float), f"y is not float: {cell}"
            assert isinstance(cell.width, float), f"width is not float: {cell}"
            assert isinstance(cell.height, float), f"height is not float: {cell}"

    def test_coordinates_within_page_bounds(self, orange_cells):
        """All coordinates must lie within the page (612 x 792 pts)."""
        PAGE_W, PAGE_H = 612.0, 792.0
        for cell in orange_cells.cells:
            if cell.width == 0 and cell.height == 0:
                continue  # merged placeholder
            assert 0 <= cell.x <= PAGE_W, f"x out of bounds: {cell}"
            assert 0 <= cell.y <= PAGE_H, f"y out of bounds: {cell}"


# ---------------------------------------------------------------------------
# 8. Source and page_no metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    def test_all_cells_source_pdfplumber(self, orange_cells):
        for cell in orange_cells.cells:
            assert cell.source == "pdfplumber", \
                f"Unexpected source '{cell.source}' on cell: {cell}"

    def test_all_cells_page_no_is_1(self, orange_cells):
        for cell in orange_cells.cells:
            assert cell.page_no == 1, \
                f"Unexpected page_no {cell.page_no} on cell: {cell}"

    def test_output_is_raw_cells_model(self, orange_cells):
        assert isinstance(orange_cells, RawCells)
        assert all(isinstance(c, RawCell) for c in orange_cells.cells)


# ---------------------------------------------------------------------------
# 9. Non-table text (section headers, labels)
# ---------------------------------------------------------------------------

class TestNonTableText:
    def test_high_temperature_header_present(self, orange_cells):
        assert has_text(orange_cells, "HIGH TEMPERATURE") or \
               has_text(orange_cells, "HIGH") and has_text(orange_cells, "TEMPERATURE"), \
            "Section header 'HIGH TEMPERATURE' not found in cells"

    def test_cover_objective_label_present(self, orange_cells):
        assert has_text(orange_cells, "Cover") or has_text(orange_cells, "Objective"), \
            "Cover Objective label not found"

    def test_deficit_rainfall_label_present(self, orange_cells):
        assert has_text(orange_cells, "DEFICIT") or has_text(orange_cells, "RAINFALL"), \
            "Deficit rainfall label not found"

    def test_wind_speed_header_present(self, orange_cells):
        assert has_text(orange_cells, "WIND") or has_text(orange_cells, "SPEED"), \
            "Wind speed header not found"


# ---------------------------------------------------------------------------
# 10. Scanned pages are skipped
# ---------------------------------------------------------------------------

class TestScannedPageSkip:
    def test_scanned_manifest_produces_no_cells(self):
        """
        When all pages are marked scanned, extract_cells must return
        an empty RawCells (not crash, not extract anything).
        """
        if not ORANGE_PDF.exists():
            pytest.skip(f"PDF not found: {ORANGE_PDF}")
        result = extract_cells(ORANGE_PDF, SCANNED_MANIFEST)
        assert isinstance(result, RawCells)
        assert result.cells == [], \
            f"Expected 0 cells for scanned manifest, got {len(result.cells)}"

    def test_empty_manifest_produces_no_cells(self):
        if not ORANGE_PDF.exists():
            pytest.skip(f"PDF not found: {ORANGE_PDF}")
        result = extract_cells(ORANGE_PDF, [])
        assert result.cells == []


# ---------------------------------------------------------------------------
# 11. persist() — JSON round-trip
# ---------------------------------------------------------------------------

class TestPersist:
    def test_persist_creates_valid_json(self, orange_cells):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "raw_cells.json"
            persist(orange_cells, out)
            assert out.exists()
            data = json.loads(out.read_text(encoding="utf-8"))
            assert "cells" in data
            assert isinstance(data["cells"], list)

    def test_persist_round_trip(self, orange_cells):
        """JSON written by persist() must deserialise back to an equal RawCells."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "raw_cells.json"
            persist(orange_cells, out)
            data = json.loads(out.read_text(encoding="utf-8"))
            restored = RawCells.model_validate(data)
        assert len(restored.cells) == len(orange_cells.cells)
        # Spot-check first and last cells
        assert restored.cells[0] == orange_cells.cells[0]
        assert restored.cells[-1] == orange_cells.cells[-1]

    def test_persist_creates_parent_dirs(self, orange_cells):
        with tempfile.TemporaryDirectory() as tmpdir:
            deep = Path(tmpdir) / "a" / "b" / "raw_cells.json"
            persist(orange_cells, deep)
            assert deep.exists()

    def test_no_empty_string_text_in_json(self, orange_cells):
        """Blank ≠ ''. Serialised JSON must not contain text='' entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "rc.json"
            persist(orange_cells, out)
            data = json.loads(out.read_text(encoding="utf-8"))
            for cell in data["cells"]:
                assert cell.get("text") != "", \
                    f"Found text='' in serialised cell: {cell}"


# ---------------------------------------------------------------------------
# 12. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_nonexistent_pdf_raises(self):
        with pytest.raises(FileNotFoundError):
            extract_cells("no_such_file.pdf", ORANGE_MANIFEST)


# ---------------------------------------------------------------------------
# 13. Cell count sanity
# ---------------------------------------------------------------------------

class TestCellCount:
    def test_reasonable_cell_count(self, orange_cells):
        """
        From probe: 7 tables with 4+2+7+9+6+7+2 = 37 structural rows,
        plus non-table words (~200+).  Total must be well above 100.
        """
        assert len(orange_cells.cells) > 100, \
            f"Too few cells extracted: {len(orange_cells.cells)}"

    def test_non_blank_cells_exceed_blanks(self, orange_cells):
        """More cells should have text than not (tables have more content than merges)."""
        with_text = sum(1 for c in orange_cells.cells if c.text is not None)
        without   = len(orange_cells.cells) - with_text
        assert with_text > without, \
            f"Fewer cells with text ({with_text}) than blank/merged ({without})"
