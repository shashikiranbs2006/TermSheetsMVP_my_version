"""
tests/test_structured_termsheet.py — Tests for Stage 4 StructuredTermsheet.

Covers:
  - Valid StructuredTermsheet round-trip (using conftest factories).
  - Missing required field inside a peril structure raises ValidationError.
  - Confidence rule: confidence=None + source="native_exact" → defaults to 1.0.
  - Confidence rule: confidence=None + source="ocr" → raises ValidationError.
  - Confidence rule: confidence=None + source="agent_inferred" → raises ValidationError.
  - confidence out of [0.0, 1.0] range raises ValidationError.
  - archetype discriminator rejects an unknown structure type.
  - All four archetype structures construct successfully.
  - Blank premium fields may be None (blank ≠ 0).
  - cover_period=None is accepted on a PerilEnvelope.
  - raw field on ExtractedValue stores un-normalised text alongside normalised value.
"""

import pytest
from pydantic import ValidationError

from models.common import CoverPeriod, DatePeriod, ExtractedValue
from models.structured_termsheet import (
    DocumentFields,
    ExtractionConfidence,
    PerilEnvelope,
    Premium,
    RainfallMultistrikePhase,
    RainfallMultistrikeStructure,
    RainfallSinglePayoutStructure,
    SourceMeta,
    StructuredTermsheet,
    TemperaturePhase,
    TemperaturePhasedStructure,
    WindPhase,
    WindPhasedStructure,
    WindTriggerBlock,
)
from tests.conftest import (
    ev_inferred,
    ev_native,
    ev_ocr,
    make_document,
    make_multistrike_structure,
    make_peril_envelope,
    make_structured_termsheet,
)


# ---------------------------------------------------------------------------
# ExtractedValue — confidence rule tests  (the most important contract tests)
# ---------------------------------------------------------------------------


class TestExtractedValueConfidenceRule:
    """
    Confidence rule (locked in task approval):
      - source="native_exact"   → confidence defaults to 1.0; omitting it is allowed.
      - source="ocr"            → confidence required; None raises ValidationError.
      - source="agent_inferred" → confidence required; None raises ValidationError.
    """

    def test_native_exact_confidence_defaults_to_1(self):
        """
        RULE: native_exact + confidence=None → confidence becomes 1.0.
        Rationale: native text extraction is certain by definition; requiring
        the caller to write confidence=1.0 on every field is noise, not safety.
        """
        ev = ExtractedValue(value="Rajasthan", source="native_exact")
        assert ev.confidence == 1.0

    def test_native_exact_explicit_confidence_preserved(self):
        """Explicit confidence on native_exact is accepted if provided."""
        ev = ExtractedValue(value="Rajasthan", source="native_exact", confidence=0.95)
        assert ev.confidence == 0.95

    def test_ocr_confidence_none_raises(self):
        """
        RULE: ocr + confidence=None → ValidationError.
        Rationale: OCR is uncertain; the caller must state their uncertainty.
        """
        with pytest.raises(ValidationError) as exc_info:
            ExtractedValue(value="65", source="ocr")
        assert "confidence is required" in str(exc_info.value)

    def test_agent_inferred_confidence_none_raises(self):
        """
        RULE: agent_inferred + confidence=None → ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            ExtractedValue(value=65.0, source="agent_inferred")
        assert "confidence is required" in str(exc_info.value)

    def test_ocr_with_explicit_confidence_accepted(self):
        ev = ExtractedValue(value="65", source="ocr", confidence=0.87)
        assert ev.confidence == 0.87

    def test_agent_inferred_with_explicit_confidence_accepted(self):
        ev = ExtractedValue(value=65.0, source="agent_inferred", confidence=0.72)
        assert ev.confidence == 0.72

    def test_confidence_above_1_raises(self):
        with pytest.raises(ValidationError):
            ExtractedValue(value="x", source="ocr", confidence=1.1)

    def test_confidence_below_0_raises(self):
        with pytest.raises(ValidationError):
            ExtractedValue(value="x", source="ocr", confidence=-0.01)

    def test_confidence_exactly_0_accepted(self):
        ev = ExtractedValue(value="x", source="ocr", confidence=0.0)
        assert ev.confidence == 0.0

    def test_confidence_exactly_1_accepted(self):
        ev = ExtractedValue(value="x", source="ocr", confidence=1.0)
        assert ev.confidence == 1.0

    def test_null_value_with_none_confidence_native_exact(self):
        """
        A blank source field: value=None (blank cell), source=native_exact.
        This is the "blank ≠ 0" scenario — value may be None, confidence
        still defaults to 1.0 because the extraction itself was certain
        (the field was certainly blank).
        """
        ev = ExtractedValue(value=None, source="native_exact")
        assert ev.value is None
        assert ev.confidence == 1.0

    def test_raw_field_stores_unnormalised_text(self):
        """raw preserves the source string before normalisation."""
        ev = ExtractedValue(value="Rajasthan", raw="Rajsthan", source="native_exact")
        assert ev.raw == "Rajsthan"
        assert ev.value == "Rajasthan"

    def test_raw_field_none_when_no_normalisation(self):
        ev = ExtractedValue(value="Rajasthan", source="native_exact")
        assert ev.raw is None


# ---------------------------------------------------------------------------
# StructuredTermsheet — valid construction
# ---------------------------------------------------------------------------


class TestStructuredTermsheetValid:
    def test_factory_produces_valid_termsheet(self, valid_structured_termsheet):
        ts = valid_structured_termsheet
        assert ts.document.scheme_name.value == "Weather Based Crop Insurance Scheme"
        assert ts.perils[0].archetype == "rainfall_multistrike"

    def test_serialisation_round_trip(self, valid_structured_termsheet):
        data = valid_structured_termsheet.model_dump()
        restored = StructuredTermsheet.model_validate(data)
        assert restored == valid_structured_termsheet

    def test_cover_period_none_accepted(self):
        """cover_period=None is valid — dates may be unparseable."""
        peril = make_peril_envelope()
        peril_data = peril.model_dump()
        peril_data["cover_period"] = None
        restored = PerilEnvelope.model_validate(peril_data)
        assert restored.cover_period is None

    def test_blank_premium_fields_are_none_not_zero(self):
        """
        Blank ≠ zero.  gross_premium=None inside ExtractedValue is valid.
        """
        premium = Premium(
            total_sum_insured=ev_native(30000.0),
            gross_premium=ev_native(None),
            premium_pct=ev_native(None),
            farmers_premium=ev_native(None),
        )
        assert premium.gross_premium.value is None
        assert premium.premium_pct.value is None

    def test_multiple_perils_on_one_document(self):
        ts = StructuredTermsheet(
            document=make_document(),
            perils=[make_peril_envelope(), make_peril_envelope()],
            extraction_confidence=ExtractionConfidence(overall=0.9, per_field={}),
        )
        assert len(ts.perils) == 2


# ---------------------------------------------------------------------------
# StructuredTermsheet — missing required peril field raises ValidationError
# ---------------------------------------------------------------------------


class TestStructuredTermsheetMissingField:
    def test_missing_strike_1_raises(self):
        """
        A RainfallMultistrikePhase without strike_1 must be rejected.
        This is the "missing required peril field" contract test.
        """
        with pytest.raises(ValidationError) as exc_info:
            RainfallMultistrikePhase(
                label=ev_native("Phase I"),
                sub_periods=[DatePeriod(start=ev_native("2019-06-25"), end=ev_native("2019-08-15"))],
                # strike_1 deliberately omitted
                strike_2=ev_native(None),
                exit=ev_native(0.0),
                rate_1=ev_native(100.0),
                rate_2=ev_native(None),
                rate_unit=ev_native("Rs/mm"),
                max_payout=ev_native(15000.0),
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("strike_1",) for e in errors)

    def test_missing_total_payout_on_multistrike_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            RainfallMultistrikeStructure(
                measure=ev_native("aggregate_rainfall"),
                unit=ev_native("mm"),
                direction=ev_native("deficit"),
                phases=[],
                # total_payout deliberately omitted
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("total_payout",) for e in errors)

    def test_missing_perils_list_raises(self):
        with pytest.raises(ValidationError):
            StructuredTermsheet(
                document=make_document(),
                # perils deliberately omitted
                extraction_confidence=ExtractionConfidence(overall=0.9, per_field={}),
            )

    def test_missing_document_raises(self):
        with pytest.raises(ValidationError):
            StructuredTermsheet(
                # document deliberately omitted
                perils=[make_peril_envelope()],
                extraction_confidence=ExtractionConfidence(overall=0.9, per_field={}),
            )


# ---------------------------------------------------------------------------
# Archetype discriminated union — structure type must match
# ---------------------------------------------------------------------------


class TestArchetypeDiscriminator:
    def test_wrong_structure_type_raises(self):
        """
        Passing a structure dict with type='banana' must be rejected by the
        discriminated union — not silently ignored or defaulted.
        """
        with pytest.raises(ValidationError):
            PerilEnvelope(
                peril_id="p",
                peril_label_raw=ev_native("TEST"),
                archetype="rainfall_multistrike",
                cover_objective=ev_native("test"),
                event_definition=ev_native("test"),
                structure={"type": "banana"},
            )

    def test_correct_structure_type_accepted(self):
        envelope = make_peril_envelope()
        assert envelope.structure.type == "rainfall_multistrike"


# ---------------------------------------------------------------------------
# All four archetype structures — smoke tests
# ---------------------------------------------------------------------------


class TestAllArchetypes:
    def test_temperature_phased_structure(self):
        s = TemperaturePhasedStructure(
            measure=ev_native("max_temperature"),
            unit=ev_native("°C"),
            direction=ev_native("upward"),
            strike=ev_native(4.0),
            exit=ev_native(25.0),
            payout_rate=ev_native(1428.57),
            payout_rate_unit=ev_native("Rs/°C"),
            max_payout=ev_native(30000.0),
            phases=[
                TemperaturePhase(
                    label=ev_native("I"),
                    period=CoverPeriod(start=ev_native("2020-02-01"), end=ev_native("2020-02-14")),
                    trigger=ev_native(28.5),
                ),
            ],
        )
        assert s.type == "temperature_phased"
        assert s.phases[0].trigger.value == 28.5

    def test_rainfall_multistrike_structure(self):
        s = make_multistrike_structure()
        assert s.type == "rainfall_multistrike"
        assert s.phases[0].strike_2.value is None  # one-strike variant

    def test_rainfall_single_payout_structure(self):
        s = RainfallSinglePayoutStructure(
            measure=ev_native("aggregate_rainfall"),
            unit=ev_native("mm"),
            direction=ev_native("excess"),
            payout_mode=ev_native("single"),
            periods=[DatePeriod(start=ev_native("2019-06-01"), end=ev_native("2019-06-20"))],
            strike_1=ev_native(20.0),
            strike_2=ev_native(45.0),
            exit=ev_native(60.0),
            rate_1=ev_native(279.6),
            rate_2=ev_native(1087.33),
            rate_unit=ev_native("Rs/mm"),
            max_payout=ev_native(23300.0),
        )
        assert s.type == "rainfall_single_payout"

    def test_wind_phased_structure(self):
        s = WindPhasedStructure(
            measure=ev_native("max_wind_speed"),
            unit=ev_native("km/h"),
            direction=ev_native("upward"),
            strike=ev_native(5.0),
            exit=ev_native(40.0),
            payout_rate=ev_native(553.57),
            payout_rate_unit=ev_native("Rs/km/h"),
            max_payout=ev_native(19375.0),
            trigger_blocks=[
                WindTriggerBlock(
                    block_label=ev_native("block_1"),
                    period=CoverPeriod(
                        start=ev_native("2019-10-15"),
                        end=ev_native("2019-11-30"),
                    ),
                    phases=[
                        WindPhase(
                            label=ev_native("I"),
                            period=CoverPeriod(
                                start=ev_native("2019-10-15"),
                                end=ev_native("2019-10-31"),
                            ),
                            trigger=ev_native(50.0),
                        )
                    ],
                )
            ],
        )
        assert s.type == "wind_phased"
        assert s.trigger_blocks[0].phases[0].trigger.value == 50.0

    def test_wind_phased_single_block_flat_representation(self):
        """
        A flat 4-phase wind peril (Guava) is represented as a single
        trigger_blocks element.  This test confirms that representation is valid.
        """
        s = WindPhasedStructure(
            measure=ev_native("max_wind_speed"),
            unit=ev_native("km/h"),
            direction=ev_native("upward"),
            strike=ev_native(5.0),
            exit=ev_native(40.0),
            payout_rate=ev_native(553.57),
            payout_rate_unit=ev_native("Rs/km/h"),
            max_payout=ev_native(19375.0),
            trigger_blocks=[
                WindTriggerBlock(
                    block_label=ev_native("flat"),
                    phases=[
                        WindPhase(label=ev_native(f"Phase {i}"), trigger=ev_native(float(45 + i)))
                        for i in range(4)
                    ],
                )
            ],
        )
        assert len(s.trigger_blocks) == 1
        assert len(s.trigger_blocks[0].phases) == 4
