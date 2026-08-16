"""
tests/test_mapper.py — Tests for Stage 4B: mapper.py and mapping_agent.py

Verifies:
  1. Each of the 4 perils maps into its correct archetype structure shape and passes
     full Pydantic validation on StructuredTermsheet.
  2. Hand-verified deficit_rainfall values (60/20/0/56.25, 80/30/10/45.00, 262.50, 7500, 37500)
     appear accurately in the mapped output.
  3. Date normalization: "1-Jul-19" -> "2019-07-01", "01 Feb" -> "2020-02-01".
  4. Blank/missing fields in source (gross_premium, premium_pct) produce null (None), not 0.
  5. Consistency / Idempotency: Running the mapping agent on the same reconstructed peril input
     produces consistent business values across runs.
  6. Inspectable logging: Raw agent prompts, model responses, and parsed outputs are persisted
     to data/intermediates/mapping_agent_logs.json.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from agents.mapping_agent import MappingAgent
from models.structured_termsheet import (
    RainfallMultistrikeStructure,
    RainfallSinglePayoutStructure,
    StructuredTermsheet,
    TemperaturePhasedStructure,
    WindPhasedStructure,
)
from stages.mapper import map_termsheet, persist, run

RECONSTRUCTED_PATH = Path("data/intermediates/reconstructed_perils.json")
MAPPED_PATH = Path("data/intermediates/mapped_termsheet.json")
LOGS_PATH = Path("data/intermediates/mapping_agent_logs.json")


@pytest.fixture(scope="module")
def reconstructed_data() -> dict:
    if not RECONSTRUCTED_PATH.exists():
        pytest.skip(f"Reconstructed perils file not found: {RECONSTRUCTED_PATH}")
    return json.loads(RECONSTRUCTED_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def mapped_termsheet_result(reconstructed_data) -> tuple[StructuredTermsheet, list[dict]]:
    # Run mapper once for test module
    return map_termsheet(reconstructed_data)


@pytest.fixture(scope="module")
def mapped_termsheet(mapped_termsheet_result) -> StructuredTermsheet:
    return mapped_termsheet_result[0]


@pytest.fixture(scope="module")
def agent_logs(mapped_termsheet_result) -> list[dict]:
    return mapped_termsheet_result[1]


# ---------------------------------------------------------------------------
# 1. Pydantic Model Validation & Archetype Shapes
# ---------------------------------------------------------------------------


class TestStructuredTermsheetShapes:
    def test_structured_termsheet_validates(self, mapped_termsheet):
        assert isinstance(mapped_termsheet, StructuredTermsheet)
        assert len(mapped_termsheet.perils) == 4

    def test_document_fields_mapped(self, mapped_termsheet):
        doc = mapped_termsheet.document
        assert doc.scheme_name.value == "WBCIS"
        assert doc.scheme_year.value == "2019-20"
        assert doc.state.value == "Rajasthan"
        assert doc.district.value == "Jhalawar"
        assert doc.crop.value == "Orange"
        assert doc.unit.value == "HECTARE"
        assert doc.reference_weather_station.value == "As Per Notification"
        assert doc.premium.total_sum_insured.value == 125000.0

    def test_all_four_archetype_structures_present(self, mapped_termsheet):
        p_types = [p.structure.type for p in mapped_termsheet.perils]
        expected_types = [
            "temperature_phased",
            "rainfall_multistrike",
            "rainfall_single_payout",
            "wind_phased",
        ]
        assert p_types == expected_types

        assert isinstance(mapped_termsheet.perils[0].structure, TemperaturePhasedStructure)
        assert isinstance(mapped_termsheet.perils[1].structure, RainfallMultistrikeStructure)
        assert isinstance(mapped_termsheet.perils[2].structure, RainfallSinglePayoutStructure)
        assert isinstance(mapped_termsheet.perils[3].structure, WindPhasedStructure)


# ---------------------------------------------------------------------------
# 2. Deficit Rainfall Values (Strongest Hand-Verified Test)
# ---------------------------------------------------------------------------


class TestDeficitRainfallMappedValues:
    def test_multistrike_phases_and_rates(self, mapped_termsheet):
        p = mapped_termsheet.perils[1]
        assert p.peril_id == "deficit_rainfall"
        struct = p.structure
        assert isinstance(struct, RainfallMultistrikeStructure)

        assert struct.total_payout.value == 37500.0
        assert len(struct.phases) == 2  # Phase I and Phase II

        # Phase I: 3 sub-periods
        assert len(struct.phases[0].sub_periods) == 3
        # Sub-period 1: Strike1=60, Strike2=20, Exit=0, Rate1=56.25, Rate2=262.5, Max=7500
        sp0 = struct.phases[0].sub_periods[0]
        assert sp0.strike_1.value == 60.0
        assert sp0.strike_2.value == 20.0
        assert sp0.exit.value == 0.0
        assert sp0.rate_1.value == 56.25
        assert sp0.rate_2.value == 262.5
        assert sp0.max_payout.value == 7500.0

        # Sub-period 2: Strike1=80, Strike2=30, Exit=10, Rate1=45.0, Rate2=262.5, Max=7500
        sp1 = struct.phases[0].sub_periods[1]
        assert sp1.strike_1.value == 80.0
        assert sp1.strike_2.value == 30.0
        assert sp1.exit.value == 10.0
        assert sp1.rate_1.value == 45.0
        assert sp1.rate_2.value == 262.5

        # Phase II: 2 sub-periods
        assert len(struct.phases[1].sub_periods) == 2
        # Phase II Sub-period 2: Strike1=60, Strike2=20, Exit=0, Rate1=56.25
        sp4 = struct.phases[1].sub_periods[1]
        assert sp4.strike_1.value == 60.0
        assert sp4.strike_2.value == 20.0
        assert sp4.exit.value == 0.0
        assert sp4.rate_1.value == 56.25


# ---------------------------------------------------------------------------
# 3. Date Normalization
# ---------------------------------------------------------------------------


class TestDateNormalization:
    def test_temperature_phase_dates(self, mapped_termsheet):
        temp_struct = mapped_termsheet.perils[0].structure
        assert isinstance(temp_struct, TemperaturePhasedStructure)

        ph0_period = temp_struct.phases[0].period
        assert ph0_period is not None
        assert ph0_period.start is not None and ph0_period.start.value == "2020-02-01"
        assert ph0_period.end is not None and ph0_period.end.value == "2020-02-14"

        ph5_period = temp_struct.phases[5].period
        assert ph5_period is not None
        assert ph5_period.start is not None and ph5_period.start.value == "2020-04-16"
        assert ph5_period.end is not None and ph5_period.end.value == "2020-04-30"

    def test_rainfall_dates(self, mapped_termsheet):
        rain_struct = mapped_termsheet.perils[1].structure
        assert isinstance(rain_struct, RainfallMultistrikeStructure)

        sp0_period = rain_struct.phases[0].sub_periods[0].period
        assert sp0_period.start.value == "2019-07-01"
        assert sp0_period.end.value == "2019-07-15"

    def test_unseasonal_dates(self, mapped_termsheet):
        unseasonal_struct = mapped_termsheet.perils[2].structure
        assert isinstance(unseasonal_struct, RainfallSinglePayoutStructure)

        assert len(unseasonal_struct.periods) >= 1
        p0 = unseasonal_struct.periods[0]
        assert p0.start.value == "2019-06-01"
        assert p0.end.value == "2019-06-15"


# ---------------------------------------------------------------------------
# 4. Blank ≠ Zero Handling
# ---------------------------------------------------------------------------


class TestBlankHandling:
    def test_gross_premium_is_null_not_zero(self, mapped_termsheet):
        prem = mapped_termsheet.document.premium
        assert prem.gross_premium.value is None
        assert prem.gross_premium.value != 0.0

    def test_premium_pct_is_null_not_zero(self, mapped_termsheet):
        prem = mapped_termsheet.document.premium
        assert prem.premium_pct.value is None
        assert prem.premium_pct.value != 0.0


# ---------------------------------------------------------------------------
# 5. Agent Consistency (Idempotency)
# ---------------------------------------------------------------------------


class TestAgentConsistency:
    def test_repeated_run_produces_consistent_values(self, reconstructed_data):
        agent = MappingAgent()
        p_unseasonal = [p for p in reconstructed_data["reconstructed_perils"] if p["peril_id"] == "unseasonal_rainfall"][0]

        res1 = agent.map_peril(p_unseasonal, scheme_year="2019-20")
        res2 = agent.map_peril(p_unseasonal, scheme_year="2019-20")

        assert res1.get("strike_1") == res2.get("strike_1") == 25
        assert res1.get("strike_2") == res2.get("strike_2") == 40
        assert res1.get("exit") == res2.get("exit") == 60
        assert res1.get("rate_1") == res2.get("rate_1") == 500
        assert res1.get("max_payout") == res2.get("max_payout") == 25000


# ---------------------------------------------------------------------------
# 6. Logging & Persistence
# ---------------------------------------------------------------------------


class TestLoggingAndPersistence:
    def test_agent_logs_recorded(self, agent_logs):
        assert len(agent_logs) == 4
        for log in agent_logs:
            assert "prompt" in log
            assert "raw_response" in log
            assert "parsed_output" in log
            assert log["model_id"] == MappingAgent().model_id

    def test_persist_output(self, mapped_termsheet, agent_logs):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_p = Path(tmpdir) / "mapped_termsheet.json"
            log_p = Path(tmpdir) / "mapping_agent_logs.json"

            persist(mapped_termsheet, agent_logs, out_p, log_p)
            assert out_p.exists()
            assert log_p.exists()

            saved_ts = json.loads(out_p.read_text(encoding="utf-8"))
            assert "document" in saved_ts
            assert "perils" in saved_ts
            assert len(saved_ts["perils"]) == 4
