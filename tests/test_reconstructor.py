"""
tests/test_reconstructor.py — Tests for Stage 4A: reconstructor.py

Verifies:
  1. deficit_rainfall (rainfall_multistrike):
       - Reconstructs Phase I (3 sub-periods) and Phase II (2 sub-periods)
       - Sub-periods have exact matching strikes, exits, rates (56.25/45.00, 262.50), and max payouts (7500)
       - Total payout is 37500
  2. temperature_phased:
       - Reconstructs 6 phases (I..VI) in exact order with triggers [29.0, 31.0, 33.5, 35.5, 36.5, 39.0]
       - Strike (4), Exit (22), Payout Rate (2083.33), Max Payout (37500) captured
  3. wind_phased:
       - Reconstructs 2 trigger blocks (Block 1: Oct-Nov, Block 2: Feb-Mar)
       - Block 1 triggers: [50, 55, 55], Block 2 triggers: [50, 55, 50]
       - Parameters strike=10, exit=70, rate=208.33, max=12500 attached to both blocks
  4. unseasonal_rainfall (rainfall_single_payout):
       - Flat parameters captured: Strike 1=25, Strike 2=40, Exit=60, Rate 1=500, Rate 2=875, Max=25000
       - Confirms single payout does not require phase/sub-period hierarchy
  5. Geometric tolerance:
       - Cells misaligned by +/- 2.5 points still cluster into correct row/column bounds
  6. Persistence & Serialization:
       - Output JSON is persisted to data/intermediates/reconstructed_perils.json
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from models.raw_cells import RawCell
from models.segmented_peril import SegmentedPeril, SegmentedPerils
from stages.reconstructor import (
    cluster_rows,
    match_cell_to_columns,
    persist,
    reconstruct_all,
    reconstruct_multistrike,
    reconstruct_peril,
    reconstruct_single_payout,
    reconstruct_temperature,
    reconstruct_wind,
    run,
)

SEGMENTED_PATH = Path("data/intermediates/segmented_perils.json")


@pytest.fixture(scope="module")
def segmented_perils() -> SegmentedPerils:
    if not SEGMENTED_PATH.exists():
        pytest.skip(f"Segmented perils file not found: {SEGMENTED_PATH}")
    data = json.loads(SEGMENTED_PATH.read_text(encoding="utf-8"))
    return SegmentedPerils.model_validate(data)


@pytest.fixture(scope="module")
def perils_dict(segmented_perils) -> dict[str, SegmentedPeril]:
    return {p.peril_id: p for p in segmented_perils.perils}


@pytest.fixture(scope="module")
def all_reconstructed(segmented_perils) -> dict[str, Any]:
    return reconstruct_all(segmented_perils)


# ---------------------------------------------------------------------------
# 1. Deficit Rainfall (rainfall_multistrike) — Highest Complexity
# ---------------------------------------------------------------------------


class TestDeficitRainfallReconstruction:
    def test_phases_structure(self, perils_dict):
        p = perils_dict["deficit_rainfall"]
        rec = reconstruct_multistrike(p)

        assert rec["peril_id"] == "deficit_rainfall"
        assert rec["archetype"] == "rainfall_multistrike"
        assert len(rec["phases"]) == 2

        phase1 = rec["phases"][0]
        phase2 = rec["phases"][1]

        assert "PHASE I" in phase1["label"].upper()
        assert "PHASE II" in phase2["label"].upper()
        assert len(phase1["sub_periods"]) == 3
        assert len(phase2["sub_periods"]) == 2

    def test_subperiod_dates(self, perils_dict):
        p = perils_dict["deficit_rainfall"]
        rec = reconstruct_multistrike(p)

        p1_sp = rec["phases"][0]["sub_periods"]
        assert "01-Jul" in p1_sp[0]["period_raw"] or "15-Jul" in p1_sp[0]["period_raw"]
        assert "16-Jul" in p1_sp[1]["period_raw"] or "31-Jul" in p1_sp[1]["period_raw"]
        assert "1-Aug" in p1_sp[2]["period_raw"] or "15 Aug" in p1_sp[2]["period_raw"]

        p2_sp = rec["phases"][1]["sub_periods"]
        assert "16 Aug" in p2_sp[0]["period_raw"] or "31 Aug" in p2_sp[0]["period_raw"]
        assert "01 Sep" in p2_sp[1]["period_raw"] or "15 Sept" in p2_sp[1]["period_raw"]

    def test_subperiod_rates_and_payouts(self, perils_dict):
        p = perils_dict["deficit_rainfall"]
        rec = reconstruct_multistrike(p)

        p1_sp = rec["phases"][0]["sub_periods"]
        p2_sp = rec["phases"][1]["sub_periods"]

        # Sub-period 0: rate_1 = 56.25, rate_2 = 262.50, max = 7500
        assert p1_sp[0]["values"]["RATE 1 (Rs./ mm)"] == "56.25"
        assert p1_sp[0]["values"]["RATE 2 (Rs./ mm)"] == "262.50"
        assert p1_sp[0]["values"]["Max payout(Rs)"] == "7500"

        # Sub-period 1: rate_1 = 45.00
        assert p1_sp[1]["values"]["RATE 1 (Rs./ mm)"] == "45.00"
        assert p1_sp[1]["values"]["RATE 2 (Rs./ mm)"] == "262.50"

        # Sub-period 2: rate_1 = 45.00
        assert p1_sp[2]["values"]["RATE 1 (Rs./ mm)"] == "45.00"

        # Phase II Sub-period 0 (SP 3): rate_1 = 45.00
        assert p2_sp[0]["values"]["RATE 1 (Rs./ mm)"] == "45.00"

        # Phase II Sub-period 1 (SP 4): rate_1 = 56.25
        assert p2_sp[1]["values"]["RATE 1 (Rs./ mm)"] == "56.25"

    def test_merged_strikes_and_exits(self, perils_dict):
        p = perils_dict["deficit_rainfall"]
        rec = reconstruct_multistrike(p)

        p1_sp = rec["phases"][0]["sub_periods"]
        p2_sp = rec["phases"][1]["sub_periods"]

        # Merged '60 80' mapped to SP0 (60) and SP1 (80)
        assert p1_sp[0]["values"]["Strike 1 (mm)"] == "60"
        assert p1_sp[1]["values"]["Strike 1 (mm)"] == "80"
        assert p1_sp[2]["values"]["Strike 1 (mm)"] == "80"
        assert p2_sp[0]["values"]["Strike 1 (mm)"] == "80"
        assert p2_sp[1]["values"]["Strike 1 (mm)"] == "60"

        # Merged '20 30' mapped to SP0 (20) and SP1 (30)
        assert p1_sp[0]["values"]["Strike 2 (mm)"] == "20"
        assert p1_sp[1]["values"]["Strike 2 (mm)"] == "30"
        assert p1_sp[2]["values"]["Strike 2 (mm)"] == "30"
        assert p2_sp[0]["values"]["Strike 2 (mm)"] == "30"
        assert p2_sp[1]["values"]["Strike 2 (mm)"] == "20"

        # Merged '0 10' mapped to SP0 (0) and SP1 (10)
        assert p1_sp[0]["values"]["EXIT (mm)"] == "0"
        assert p1_sp[1]["values"]["EXIT (mm)"] == "10"
        assert p1_sp[2]["values"]["EXIT (mm)"] == "10"
        assert p2_sp[0]["values"]["EXIT (mm)"] == "10"
        assert p2_sp[1]["values"]["EXIT (mm)"] == "0"

    def test_total_payout(self, perils_dict):
        p = perils_dict["deficit_rainfall"]
        rec = reconstruct_multistrike(p)
        assert rec["total_payout_raw"] == "37500"


# ---------------------------------------------------------------------------
# 2. Temperature Phased
# ---------------------------------------------------------------------------


class TestTemperaturePhasedReconstruction:
    def test_phases_and_triggers(self, perils_dict):
        p = perils_dict["high_temperature"]
        rec = reconstruct_temperature(p)

        assert rec["peril_id"] == "high_temperature"
        assert rec["archetype"] == "temperature_phased"
        assert len(rec["phases"]) == 6

        labels = [ph["label"] for ph in rec["phases"]]
        assert labels == ["I", "II", "III", "IV", "V", "VI"]

        triggers = [ph["trigger_raw"] for ph in rec["phases"]]
        assert triggers == ["29.0", "31.0", "33.5", "35.5", "36.5", "39.0"]

    def test_common_parameters(self, perils_dict):
        p = perils_dict["high_temperature"]
        rec = reconstruct_temperature(p)
        params = rec["parameters"]

        assert any("Strike" in k and "4" in v for k, v in params.items())
        assert any("Exit" in k and "22" in v for k, v in params.items())
        assert any("Payout" in k and "2083.33" in v for k, v in params.items())
        assert any("Max" in k and "37500" in v for k, v in params.items())


# ---------------------------------------------------------------------------
# 3. Wind Phased
# ---------------------------------------------------------------------------


class TestWindPhasedReconstruction:
    def test_trigger_blocks_structure(self, perils_dict):
        p = perils_dict["high_wind_speed"]
        rec = reconstruct_wind(p)

        assert rec["peril_id"] == "high_wind_speed"
        assert rec["archetype"] == "wind_phased"
        assert len(rec["trigger_blocks"]) == 2

        b1 = rec["trigger_blocks"][0]
        b2 = rec["trigger_blocks"][1]

        assert len(b1["phases"]) == 3
        assert len(b2["phases"]) == 3

        b1_triggers = [ph["trigger_raw"] for ph in b1["phases"]]
        b2_triggers = [ph["trigger_raw"] for ph in b2["phases"]]

        assert b1_triggers == ["50", "55", "55"]
        assert b2_triggers == ["50", "55", "50"]

    def test_wind_parameters(self, perils_dict):
        p = perils_dict["high_wind_speed"]
        rec = reconstruct_wind(p)

        b1 = rec["trigger_blocks"][0]
        b2 = rec["trigger_blocks"][1]

        for block in [b1, b2]:
            params = block["parameters"]
            assert any("Strike" in k and "10" in v for k, v in params.items())
            assert any("Exit" in k and "70" in v for k, v in params.items())
            assert any("Payout" in k and "208.33" in v for k, v in params.items())
            assert any("Max" in k and "12500" in v for k, v in params.items())

    def test_single_block_wind_structure(self):
        """Single block wind with 4 sequential phases (e.g. SampleTermsheets Page 10 Guava)."""
        cells = [
            RawCell(text="Phase", x=206.2, y=178.9, width=63.8, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="I", x=270.0, y=178.9, width=62.0, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="II", x=332.0, y=178.9, width=61.9, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="III", x=393.9, y=178.9, width=55.3, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="IV", x=449.2, y=178.9, width=55.3, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="Period", x=206.2, y=190.6, width=63.8, height=23.3, page_no=10, source="pdfplumber"),
            RawCell(text="01 July to 15\nJuly", x=270.0, y=190.6, width=62.0, height=23.3, page_no=10, source="pdfplumber"),
            RawCell(text="16 July to 31\nJuly", x=332.0, y=190.6, width=61.9, height=23.3, page_no=10, source="pdfplumber"),
            RawCell(text="01-Aug. to\n15 Aug.", x=393.9, y=190.6, width=55.3, height=23.3, page_no=10, source="pdfplumber"),
            RawCell(text="16-Aug. to\n31 Aug.", x=449.2, y=190.6, width=55.3, height=23.3, page_no=10, source="pdfplumber"),
            RawCell(text="Trigger (km/h)", x=206.2, y=213.8, width=63.8, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="40", x=270.0, y=213.8, width=62.0, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="45", x=332.0, y=213.8, width=61.9, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="45", x=393.9, y=213.8, width=55.3, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="40", x=449.2, y=213.8, width=55.3, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="Strike (km/h)", x=206.2, y=225.5, width=63.8, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="5", x=270.0, y=225.5, width=234.5, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="Exit (km/h)", x=206.2, y=237.1, width=63.8, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="40", x=270.0, y=237.1, width=234.5, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="Payout(Rs/km/h)", x=206.2, y=248.8, width=63.8, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="950.71", x=270.0, y=248.8, width=234.5, height=11.6, page_no=10, source="pdfplumber"),
            RawCell(text="Max payout(Rs)", x=206.2, y=260.4, width=63.8, height=11.7, page_no=10, source="pdfplumber"),
            RawCell(text="33275", x=270.0, y=260.4, width=234.5, height=11.7, page_no=10, source="pdfplumber"),
        ]
        p = SegmentedPeril(peril_id="high_wind_speed", raw_cells=cells, archetype="wind_phased")
        rec = reconstruct_wind(p)

        assert rec["peril_id"] == "high_wind_speed"
        assert len(rec["trigger_blocks"]) == 1
        b = rec["trigger_blocks"][0]
        assert b["block_label"] == "block_1"
        assert len(b["phases"]) == 4
        assert [ph["label"] for ph in b["phases"]] == ["I", "II", "III", "IV"]
        assert [ph["trigger_raw"] for ph in b["phases"]] == ["40", "45", "45", "40"]
        params = b["parameters"]
        assert params.get("Strike (km/h)") == "5"
        assert params.get("Exit (km/h)") == "40"
        assert params.get("Payout(Rs/km/h)") == "950.71"
        assert params.get("Max payout(Rs)") == "33275"

    def test_empty_wind_peril_returns_zero_blocks(self):
        p = SegmentedPeril(peril_id="high_wind_speed", raw_cells=[], archetype="wind_phased")
        rec = reconstruct_wind(p)
        assert rec["trigger_blocks"] == []


# ---------------------------------------------------------------------------
# 4. Unseasonal Rainfall (rainfall_single_payout)
# ---------------------------------------------------------------------------


class TestUnseasonalRainfallReconstruction:
    def test_single_payout_parameters(self, perils_dict):
        p = perils_dict["unseasonal_rainfall"]
        rec = reconstruct_single_payout(p)

        assert rec["peril_id"] == "unseasonal_rainfall"
        assert rec["archetype"] == "rainfall_single_payout"
        params = rec["parameters"]

        assert params.get("Strike 1 (mm)") == "25"
        assert params.get("Strike 2 (mm)") == "40"
        assert params.get("EXIT (mm)") == "60"
        assert params.get("RATE 1 (Rs./ mm)") == "500"
        assert params.get("RATE 2 (Rs./ mm)") == "875"
        assert params.get("Max payout(Rs)") == "25000"


# ---------------------------------------------------------------------------
# 5. Geometric Tolerance Handling
# ---------------------------------------------------------------------------


class TestGeometricTolerance:
    def test_row_clustering_with_y_jitter(self):
        # Create 3 cells with slight y variations within 2.5 pts (e.g. 100.0, 101.5, 99.0)
        c1 = RawCell(text="A", x=10.0, y=100.0, width=50.0, height=10.0, page_no=1)
        c2 = RawCell(text="B", x=70.0, y=101.5, width=50.0, height=10.0, page_no=1)
        c3 = RawCell(text="C", x=130.0, y=99.0, width=50.0, height=10.0, page_no=1)
        # Next row cell
        c4 = RawCell(text="D", x=10.0, y=120.0, width=50.0, height=10.0, page_no=1)

        rows = cluster_rows([c1, c2, c3, c4], y_tolerance=3.0)
        assert len(rows) == 2
        assert len(rows[0]) == 3
        assert [c.text for c in rows[0]] == ["A", "B", "C"]
        assert rows[1][0].text == "D"

    def test_column_matching_with_x_jitter(self):
        # Column bounds: [100.0, 150.0] and [150.0, 200.0]
        col_bounds = [(100.0, 150.0), (150.0, 200.0)]

        # Cell slightly shifted left by 2 points (x=98.0, width=50.0 -> x1=148.0)
        c_shifted = RawCell(text="Val", x=98.0, y=100.0, width=50.0, height=10.0, page_no=1)
        matched = match_cell_to_columns(c_shifted, col_bounds)
        assert matched == [0]

        # Merged cell spanning both columns
        c_merged = RawCell(text="Merged", x=100.0, y=100.0, width=100.0, height=10.0, page_no=1)
        matched_merged = match_cell_to_columns(c_merged, col_bounds)
        assert matched_merged == [0, 1]


# ---------------------------------------------------------------------------
# 6. Persistence & Master Runner
# ---------------------------------------------------------------------------


class TestReconstructionPersistence:
    def test_reconstruct_all(self, all_reconstructed):
        perils_list = all_reconstructed["reconstructed_perils"]
        assert len(perils_list) == 4
        ids = [p["peril_id"] for p in perils_list]
        assert ids == ["high_temperature", "deficit_rainfall", "unseasonal_rainfall", "high_wind_speed"]

    def test_persist_round_trip(self, all_reconstructed):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "reconstructed.json"
            persist(all_reconstructed, out_file)
            assert out_file.exists()

            data = json.loads(out_file.read_text(encoding="utf-8"))
            assert "reconstructed_perils" in data
            assert len(data["reconstructed_perils"]) == 4

    def test_run_function(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "reconstructed_perils.json"
            res = run(SEGMENTED_PATH, out_file, quiet=True)
            assert out_file.exists()
            assert len(res["reconstructed_perils"]) == 4
