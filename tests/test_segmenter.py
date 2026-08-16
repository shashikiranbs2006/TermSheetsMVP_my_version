"""
tests/test_segmenter.py — Tests for Stage 3: segmenter.py

Verifies:
  1. Orange_TermSheet.pdf produces exactly 4 SegmentedPeril objects.
  2. Each peril has the exact archetype assigned:
       - high_temperature    -> temperature_phased
       - deficit_rainfall    -> rainfall_multistrike
       - unseasonal_rainfall -> rainfall_single_payout
       - high_wind_speed     -> wind_phased
  3. Cell isolation: each peril's raw_cells contains only its own data
       - Temperature peril contains triggers (29.0, 31.0), NOT rainfall rates (56.25, 262.50)
       - Deficit rainfall peril contains Phase I/II and rates, NOT temperature triggers
       - Unseasonal rainfall contains single payout rates (500, 875), NOT wind triggers
       - Wind peril contains wind triggers (50, 55), NOT temperature/rainfall values
  4. Cell accounting:
       - 100% of the 330 input cells are accounted for (4 perils + header + footer == 330)
       - Header cells contain State/District/Crop/Annexure
       - Footer cells contain Premium Description / Total Sum Insured
  5. Output format is a valid SegmentedPerils Pydantic model conforming to models/segmented_peril.py.
  6. Persistence round-trip to data/intermediates/segmented_perils.json.
  7. Empty RawCells produces empty SegmentedPerils gracefully.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from models.raw_cells import RawCell, RawCells
from models.segmented_peril import SegmentedPeril, SegmentedPerils
from stages.segmenter import persist, run, segment, segment_with_accounting

# ---------------------------------------------------------------------------
# Fixture: load real raw_cells from Stage 2 output
# ---------------------------------------------------------------------------

RAW_CELLS_PATH = Path("data/intermediates/raw_cells.json")


@pytest.fixture(scope="module")
def orange_raw_cells() -> RawCells:
    if not RAW_CELLS_PATH.exists():
        pytest.skip(f"Raw cells file not found: {RAW_CELLS_PATH}")
    raw_dict = json.loads(RAW_CELLS_PATH.read_text(encoding="utf-8"))
    return RawCells.model_validate(raw_dict)


@pytest.fixture(scope="module")
def segmented_output(orange_raw_cells) -> tuple[SegmentedPerils, list[RawCell], list[RawCell]]:
    return segment_with_accounting(orange_raw_cells)


@pytest.fixture(scope="module")
def orange_segmented(segmented_output) -> SegmentedPerils:
    return segmented_output[0]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def peril_texts(peril: SegmentedPeril) -> list[str]:
    return [c.text for c in peril.raw_cells if c.text is not None]


def peril_has_exact(peril: SegmentedPeril, target: str) -> bool:
    return target in peril_texts(peril)


def peril_has_text(peril: SegmentedPeril, fragment: str) -> bool:
    # Join all peril text with spaces to match multi-word phrases across word-level cells
    joined = " ".join(peril_texts(peril)).lower()
    return fragment.lower() in joined


# ---------------------------------------------------------------------------
# 1. 4 Perils and Archetype Classification
# ---------------------------------------------------------------------------

class TestPerilCountAndClassification:
    def test_exactly_four_perils_produced(self, orange_segmented):
        assert len(orange_segmented.perils) == 4, (
            f"Expected 4 perils, got {len(orange_segmented.perils)}"
        )

    def test_peril_ids_in_document_order(self, orange_segmented):
        peril_ids = [p.peril_id for p in orange_segmented.perils]
        expected_ids = [
            "high_temperature",
            "deficit_rainfall",
            "unseasonal_rainfall",
            "high_wind_speed",
        ]
        assert peril_ids == expected_ids

    def test_peril_archetypes_correct(self, orange_segmented):
        archetypes = [p.archetype for p in orange_segmented.perils]
        expected_archetypes = [
            "temperature_phased",
            "rainfall_multistrike",
            "rainfall_single_payout",
            "wind_phased",
        ]
        assert archetypes == expected_archetypes

    def test_all_perils_are_pydantic_segmented_peril_instances(self, orange_segmented):
        assert isinstance(orange_segmented, SegmentedPerils)
        assert all(isinstance(p, SegmentedPeril) for p in orange_segmented.perils)


# ---------------------------------------------------------------------------
# 2. Cell Isolation Spot-Checks
# ---------------------------------------------------------------------------

class TestCellIsolation:
    def test_temperature_peril_contains_own_data(self, orange_segmented):
        temp_peril = orange_segmented.perils[0]
        assert temp_peril.peril_id == "high_temperature"
        # Must contain temperature triggers and strikes
        assert peril_has_exact(temp_peril, "29.0")
        assert peril_has_exact(temp_peril, "31.0")
        assert peril_has_exact(temp_peril, "33.5")
        assert peril_has_exact(temp_peril, "2083.33")
        assert peril_has_text(temp_peril, "HIGH TEMPERATURE")

    def test_temperature_peril_excludes_other_perils(self, orange_segmented):
        temp_peril = orange_segmented.perils[0]
        # Must NOT contain rainfall rates or wind triggers
        assert not peril_has_exact(temp_peril, "56.25"), "Found rainfall rate 56.25 in temperature peril"
        assert not peril_has_exact(temp_peril, "262.50"), "Found rainfall rate 262.50 in temperature peril"
        assert not peril_has_exact(temp_peril, "500"), "Found unseasonal rate 500 in temperature peril"
        assert not peril_has_text(temp_peril, "DEFICIT RAINFALL")
        assert not peril_has_text(temp_peril, "WIND SPEED")

    def test_deficit_rainfall_peril_contains_own_data(self, orange_segmented):
        rain_peril = orange_segmented.perils[1]
        assert rain_peril.peril_id == "deficit_rainfall"
        assert peril_has_exact(rain_peril, "56.25")
        assert peril_has_exact(rain_peril, "45.00")
        assert peril_has_exact(rain_peril, "262.50")
        assert peril_has_exact(rain_peril, "7500")
        assert peril_has_text(rain_peril, "Phase I")
        assert peril_has_text(rain_peril, "Phase II")

    def test_deficit_rainfall_excludes_temperature_and_wind(self, orange_segmented):
        rain_peril = orange_segmented.perils[1]
        assert not peril_has_exact(rain_peril, "29.0")
        assert not peril_has_exact(rain_peril, "31.0")
        assert not peril_has_exact(rain_peril, "2083.33")
        assert not peril_has_text(rain_peril, "HIGH TEMPERATURE")

    def test_unseasonal_rainfall_contains_own_data(self, orange_segmented):
        unseasonal_peril = orange_segmented.perils[2]
        assert unseasonal_peril.peril_id == "unseasonal_rainfall"
        assert peril_has_exact(unseasonal_peril, "25")
        assert peril_has_exact(unseasonal_peril, "40")
        assert peril_has_exact(unseasonal_peril, "60")
        assert peril_has_exact(unseasonal_peril, "500")
        assert peril_has_exact(unseasonal_peril, "875")
        assert peril_has_exact(unseasonal_peril, "25000")

    def test_wind_peril_contains_own_data(self, orange_segmented):
        wind_peril = orange_segmented.perils[3]
        assert wind_peril.peril_id == "high_wind_speed"
        assert peril_has_exact(wind_peril, "50")
        assert peril_has_exact(wind_peril, "55")
        assert peril_has_exact(wind_peril, "10")
        assert peril_has_exact(wind_peril, "70")
        assert peril_has_exact(wind_peril, "208.33")
        assert peril_has_exact(wind_peril, "12500")
        assert peril_has_text(wind_peril, "WIND SPEED")

    def test_wind_peril_excludes_earlier_perils(self, orange_segmented):
        wind_peril = orange_segmented.perils[3]
        assert not peril_has_exact(wind_peril, "56.25")
        assert not peril_has_exact(wind_peril, "29.0")
        assert not peril_has_exact(wind_peril, "500")


# ---------------------------------------------------------------------------
# 3. Cell Accounting (330 Total Input Cells)
# ---------------------------------------------------------------------------

class TestCellAccounting:
    def test_all_input_cells_accounted_for(self, orange_raw_cells, segmented_output):
        segmented, header_cells, footer_cells = segmented_output
        total_input = len(orange_raw_cells.cells)
        assert total_input == 330

        peril_cell_sum = sum(len(p.raw_cells) for p in segmented.perils)
        total_accounted = peril_cell_sum + len(header_cells) + len(footer_cells)

        assert total_accounted == total_input, (
            f"Accounting mismatch: input={total_input}, accounted={total_accounted} "
            f"(perils={peril_cell_sum}, header={len(header_cells)}, footer={len(footer_cells)})"
        )

    def test_header_cells_contain_document_metadata(self, segmented_output):
        _, header_cells, _ = segmented_output
        header_texts = [c.text for c in header_cells if c.text]
        header_str = " ".join(header_texts)
        assert "RAJASTHAN" in header_str
        assert "Jhalawar" in header_str
        assert "Orange" in header_str
        assert "HECTARE" in header_str
        assert "Annexure" in header_str

    def test_footer_cells_contain_premium_description(self, segmented_output):
        _, _, footer_cells = segmented_output
        footer_texts = [c.text for c in footer_cells if c.text]
        footer_str = " ".join(footer_texts)
        assert "Total Sum" in footer_str or "Insured" in footer_str
        assert "125000" in footer_str

    def test_peril_cell_counts_match_expectations(self, orange_segmented):
        # Temp: 90, Deficit: 89, Unseasonal: 38, Wind: 91
        p_counts = [len(p.raw_cells) for p in orange_segmented.perils]
        assert p_counts == [90, 89, 38, 91]


# ---------------------------------------------------------------------------
# 4. Persistence & Serialization
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_persist_creates_valid_json(self, orange_segmented):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "segmented_perils.json"
            persist(orange_segmented, out_path)
            assert out_path.exists()

            data = json.loads(out_path.read_text(encoding="utf-8"))
            assert "perils" in data
            assert len(data["perils"]) == 4

    def test_persist_round_trip(self, orange_segmented):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "segmented_perils.json"
            persist(orange_segmented, out_path)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            restored = SegmentedPerils.model_validate(data)

            assert len(restored.perils) == len(orange_segmented.perils)
            for orig, rest in zip(orange_segmented.perils, restored.perils):
                assert orig.peril_id == rest.peril_id
                assert orig.archetype == rest.archetype
                assert len(orig.raw_cells) == len(rest.raw_cells)


# ---------------------------------------------------------------------------
# 5. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_raw_cells_returns_empty_segmented_perils(self):
        empty_raw = RawCells(cells=[])
        res, h, f = segment_with_accounting(empty_raw)
        assert res.perils == []
        assert h == []
        assert f == []

    def test_run_function_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            run("non_existent_raw_cells.json")
