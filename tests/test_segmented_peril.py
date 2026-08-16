"""
tests/test_segmented_peril.py — Tests for Stage 3 SegmentedPeril / SegmentedPerils.

Covers:
  - Valid construction with each of the four archetypes.
  - Invalid archetype string raises ValidationError.
  - peril_id is a free string — any value is accepted.
  - raw_cells may be empty (segmenter found the section boundary but extracted nothing).
  - SegmentedPerils container.
"""

import pytest
from pydantic import ValidationError

from models.raw_cells import RawCell
from models.segmented_peril import SegmentedPeril, SegmentedPerils


def _cell():
    return RawCell(x=0.0, y=0.0, width=10.0, height=5.0, page_no=1, source="pdfplumber")


class TestSegmentedPerilValid:
    def test_all_four_archetypes_accepted(self):
        archetypes = [
            "temperature_phased",
            "rainfall_multistrike",
            "rainfall_single_payout",
            "wind_phased",
        ]
        for arch in archetypes:
            sp = SegmentedPeril(peril_id="test", raw_cells=[_cell()], archetype=arch)
            assert sp.archetype == arch

    def test_peril_id_is_free_string(self):
        """peril_id accepts any string — including duplicates within a doc."""
        for label in ["deficit_rainfall", "2b_excess_rainfall", "high_temperature", "wind_speed_1"]:
            sp = SegmentedPeril(peril_id=label, raw_cells=[], archetype="rainfall_multistrike")
            assert sp.peril_id == label

    def test_empty_raw_cells_accepted(self):
        """Segmenter may identify a peril section boundary before any cells are extracted."""
        sp = SegmentedPeril(peril_id="p1", raw_cells=[], archetype="wind_phased")
        assert sp.raw_cells == []

    def test_multiple_cells(self):
        cells = [_cell(), _cell()]
        sp = SegmentedPeril(peril_id="p", raw_cells=cells, archetype="rainfall_single_payout")
        assert len(sp.raw_cells) == 2

    def test_serialisation_round_trip(self):
        sp = SegmentedPeril(peril_id="x", raw_cells=[_cell()], archetype="temperature_phased")
        restored = SegmentedPeril.model_validate(sp.model_dump())
        assert restored == sp


class TestSegmentedPerilInvalid:
    def test_unknown_archetype_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            SegmentedPeril(peril_id="p", raw_cells=[], archetype="banana_peril")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("archetype",) for e in errors)

    def test_empty_archetype_raises(self):
        with pytest.raises(ValidationError):
            SegmentedPeril(peril_id="p", raw_cells=[], archetype="")

    def test_missing_archetype_raises(self):
        with pytest.raises(ValidationError):
            SegmentedPeril(peril_id="p", raw_cells=[])


class TestSegmentedPerils:
    def test_empty_perils_list_accepted(self):
        sps = SegmentedPerils(perils=[])
        assert sps.perils == []

    def test_multiple_perils(self):
        sps = SegmentedPerils(perils=[
            SegmentedPeril(peril_id="a", raw_cells=[], archetype="rainfall_multistrike"),
            SegmentedPeril(peril_id="a", raw_cells=[], archetype="rainfall_single_payout"),
        ])
        assert len(sps.perils) == 2
        # Same peril_id is allowed (e.g. two deficit_rainfall perils on one doc)
        assert sps.perils[0].peril_id == sps.perils[1].peril_id
