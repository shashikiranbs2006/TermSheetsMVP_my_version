"""
tests/test_validator.py — Test suite for Stage 5: Independent Deterministic Validation

Tests:
  1. Real Orange TermsSheet: data/intermediates/mapped_termsheet.json validates cleanly
     with 0 errors and review_required=False.
  2. Synthetic Test 1 (Completeness): missing required document or peril fields triggers completeness_check error.
  3. Synthetic Test 2 (Strike/Exit Sanity): broken strike > exit or deficit exit > strike triggers strike_exit_sanity error.
  4. Synthetic Test 3 (Payout Arithmetic): sub-period max_payout sum mismatch triggers payout_arithmetic error.
  5. Synthetic Test 4 (Premium Contradiction): gross_premium=0 but farmers_premium > 0 triggers premium_contradiction error.
  6. Synthetic Test 5 (Sum Insured): total_sum_insured <= 0 or missing triggers sum_insured_check error.
  7. Synthetic Test 6 (Confidence Threshold): a single field with confidence < 0.75 triggers confidence_threshold warning and sets review_required=True.
  8. Read-only guarantee: validator does not mutate or alter the input termsheet data.
"""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest

from models.common import ExtractedValue
from models.structured_termsheet import StructuredTermsheet
from stages.validator import (
    check_completeness,
    check_confidence_threshold,
    check_payout_arithmetic,
    check_premium_contradictions,
    check_strike_exit_sanity,
    check_sum_insured,
    persist,
    run,
    validate_termsheet,
)

MAPPED_PATH = Path("data/intermediates/mapped_termsheet.json")


@pytest.fixture(scope="module")
def real_termsheet() -> StructuredTermsheet:
    if not MAPPED_PATH.exists():
        pytest.skip(f"Mapped termsheet not found at: {MAPPED_PATH}")
    data = json.loads(MAPPED_PATH.read_text(encoding="utf-8"))
    return StructuredTermsheet.model_validate(data)


# ---------------------------------------------------------------------------
# 1. Real Orange Termsheet Clean Validation
# ---------------------------------------------------------------------------


class TestRealOrangeValidation:
    def test_real_orange_passes_all_checks_cleanly(self, real_termsheet):
        validated = validate_termsheet(real_termsheet)

        # There should be 0 error flags on real Orange data
        errors = [f for f in validated.flags if f.severity == "error"]
        assert len(errors) == 0, f"Unexpected errors on real Orange data: {errors}"

        # review_required should be False because confidence is 0.95-1.0 and no errors
        assert validated.review_required is False
        assert len(validated.flags) == 0

    def test_persist_validated_termsheet(self, real_termsheet):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_p = Path(tmpdir) / "validated_termsheet.json"
            validated = validate_termsheet(real_termsheet)
            persist(validated, out_p)
            assert out_p.exists()

            saved = json.loads(out_p.read_text(encoding="utf-8"))
            assert "termsheet" in saved
            assert "flags" in saved
            assert "review_required" in saved
            assert saved["review_required"] is False


# ---------------------------------------------------------------------------
# 2. Synthetic Test 1: Completeness
# ---------------------------------------------------------------------------


class TestCompletenessRule:
    def test_missing_crop_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        broken.document.crop = ExtractedValue(value=None, source="native_exact", confidence=1.0)

        flags = check_completeness(broken)
        crop_flags = [f for f in flags if f.field_path == "document.crop"]
        assert len(crop_flags) == 1
        assert crop_flags[0].rule == "completeness_check"
        assert crop_flags[0].severity == "error"

    def test_empty_perils_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        broken.perils = []

        flags = check_completeness(broken)
        assert any(f.rule == "completeness_check" and f.severity == "error" for f in flags)


# ---------------------------------------------------------------------------
# 3. Synthetic Test 2: Strike / Exit Sanity
# ---------------------------------------------------------------------------


class TestStrikeExitSanityRule:
    def test_deficit_rainfall_exit_greater_than_strike_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        # For deficit rainfall, exit must be lower than strike_1. Set exit = 100 > strike_1 (60)
        p_rain = [p for p in broken.perils if p.peril_id == "deficit_rainfall"][0]
        p_rain.structure.phases[0].sub_periods[0].exit = ExtractedValue(value=100.0, source="agent_inferred", confidence=0.95)

        flags = check_strike_exit_sanity(broken)
        rain_flags = [f for f in flags if f.rule == "strike_exit_sanity"]
        assert len(rain_flags) >= 1
        assert rain_flags[0].severity == "error"
        assert "must be less than strike_1" in rain_flags[0].message

    def test_temperature_strike_greater_than_exit_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        # Upward peril: strike (e.g. 25) > exit (22) is invalid
        p_temp = [p for p in broken.perils if p.peril_id == "high_temperature"][0]
        p_temp.structure.strike = ExtractedValue(value=25.0, source="agent_inferred", confidence=0.95)

        flags = check_strike_exit_sanity(broken)
        temp_flags = [f for f in flags if f.rule == "strike_exit_sanity"]
        assert len(temp_flags) >= 1
        assert temp_flags[0].severity == "error"
        assert "must be less than exit" in temp_flags[0].message


# ---------------------------------------------------------------------------
# 4. Synthetic Test 3: Payout Arithmetic
# ---------------------------------------------------------------------------


class TestPayoutArithmeticRule:
    def test_multistrike_phase_sum_mismatch_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        # Real: 5 * 7500 = 37500. Change total_payout to 45000.0
        p_rain = [p for p in broken.perils if p.peril_id == "deficit_rainfall"][0]
        p_rain.structure.total_payout = ExtractedValue(value=45000.0, source="agent_inferred", confidence=0.95)

        flags = check_payout_arithmetic(broken)
        arith_flags = [f for f in flags if f.rule == "payout_arithmetic"]
        assert len(arith_flags) == 1
        assert arith_flags[0].severity == "error"
        assert "does not reconcile" in arith_flags[0].message

    def test_temperature_rate_span_mismatch_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        # Real: 2083.33 * (22 - 4) = 37500. Change max_payout to 50000.0
        p_temp = [p for p in broken.perils if p.peril_id == "high_temperature"][0]
        p_temp.structure.max_payout = ExtractedValue(value=50000.0, source="agent_inferred", confidence=0.95)

        flags = check_payout_arithmetic(broken)
        arith_flags = [f for f in flags if f.rule == "payout_arithmetic"]
        assert len(arith_flags) == 1
        assert arith_flags[0].severity == "error"
        assert "Payout calculation mismatch" in arith_flags[0].message


# ---------------------------------------------------------------------------
# 5. Synthetic Test 4: Premium Contradictions
# ---------------------------------------------------------------------------


class TestPremiumContradictionRule:
    def test_gross_zero_with_farmers_positive_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        # Guava sample scenario: total_premium=0.0, farmers_premium=1938.0
        broken.document.premium.gross_premium = ExtractedValue(value=0.0, source="native_exact", confidence=1.0)
        broken.document.premium.farmers_premium = ExtractedValue(value=1938.0, source="native_exact", confidence=1.0)

        flags = check_premium_contradictions(broken)
        prem_flags = [f for f in flags if f.rule == "premium_contradiction"]
        assert len(prem_flags) == 1
        assert prem_flags[0].severity == "error"
        assert "gross_premium is 0.0 but farmers_premium is 1938.00" in prem_flags[0].message

    def test_null_gross_and_null_farmer_does_not_flag(self, real_termsheet):
        # Real Orange data has gross=null, farmer=null -> should not flag
        flags = check_premium_contradictions(real_termsheet)
        assert len(flags) == 0


# ---------------------------------------------------------------------------
# 6. Synthetic Test 5: Sum Insured Check
# ---------------------------------------------------------------------------


class TestSumInsuredRule:
    def test_zero_or_negative_sum_insured_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        broken.document.premium.total_sum_insured = ExtractedValue(value=0.0, source="native_exact", confidence=1.0)

        flags = check_sum_insured(broken)
        si_flags = [f for f in flags if f.rule == "sum_insured_check"]
        assert len(si_flags) == 1
        assert si_flags[0].severity == "error"
        assert "must be a positive number greater than 0" in si_flags[0].message

    def test_missing_sum_insured_flags_error(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        broken.document.premium.total_sum_insured = ExtractedValue(value=None, source="native_exact", confidence=1.0)

        flags = check_sum_insured(broken)
        si_flags = [f for f in flags if f.rule == "sum_insured_check"]
        assert len(si_flags) == 1
        assert si_flags[0].severity == "error"
        assert "is missing or null" in si_flags[0].message


# ---------------------------------------------------------------------------
# 7. Synthetic Test 6: Confidence Threshold & Review Required
# ---------------------------------------------------------------------------


class TestConfidenceThresholdRule:
    def test_single_low_confidence_field_sets_review_required(self, real_termsheet):
        broken = real_termsheet.model_copy(deep=True)
        # Set one field's confidence to 0.60 (below threshold 0.75)
        p_wind = [p for p in broken.perils if p.peril_id == "high_wind_speed"][0]
        p_wind.structure.strike.confidence = 0.60

        validated = validate_termsheet(broken, confidence_threshold=0.75)
        conf_flags = [f for f in validated.flags if f.rule == "confidence_threshold"]
        assert len(conf_flags) >= 1
        assert conf_flags[0].severity == "warning"
        assert "0.60" in conf_flags[0].message
        assert validated.review_required is True

    def test_clean_high_confidence_sets_review_required_false(self, real_termsheet):
        validated = validate_termsheet(real_termsheet, confidence_threshold=0.75)
        assert validated.review_required is False


# ---------------------------------------------------------------------------
# 8. Read-Only / Immutability Guarantee
# ---------------------------------------------------------------------------


class TestReadOnlyGuarantee:
    def test_validator_does_not_mutate_termsheet(self, real_termsheet):
        original_dump = real_termsheet.model_dump()
        _ = validate_termsheet(real_termsheet)
        after_dump = real_termsheet.model_dump()

        assert original_dump == after_dump
