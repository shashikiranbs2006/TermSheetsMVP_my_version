"""
tests/conftest.py — Shared pytest fixtures and factory helpers.

Factories produce the minimal valid objects needed across test modules.
Every factory returns a dict of constructor kwargs so callers can easily
override individual fields for negative tests.
"""

import pytest

from models.common import CoverPeriod, DatePeriod, ExtractedValue
from models.raw_cells import RawCell
from models.structured_termsheet import (
    DocumentFields,
    ExtractionConfidence,
    PerilEnvelope,
    Premium,
    RainfallMultistrikePhase,
    RainfallMultistrikeStructure,
    SourceMeta,
    StructuredTermsheet,
)
from models.validated_termsheet import ValidatedTermsheet


# ---------------------------------------------------------------------------
# ExtractedValue factory helpers
# ---------------------------------------------------------------------------


def ev_native(value, raw=None):
    """ExtractedValue with source='native_exact'.  confidence defaults to 1.0."""
    return ExtractedValue(value=value, raw=raw, source="native_exact")


def ev_ocr(value, confidence, raw=None):
    """ExtractedValue with source='ocr'.  confidence is required."""
    return ExtractedValue(value=value, raw=raw, source="ocr", confidence=confidence)


def ev_inferred(value, confidence, raw=None):
    """ExtractedValue with source='agent_inferred'.  confidence is required."""
    return ExtractedValue(
        value=value, raw=raw, source="agent_inferred", confidence=confidence
    )


# ---------------------------------------------------------------------------
# RawCell factory
# ---------------------------------------------------------------------------


def make_raw_cell(**overrides) -> dict:
    base = dict(text="65", x=10.0, y=20.0, width=50.0, height=15.0, page_no=3, source="pdfplumber")
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# Premium factory
# ---------------------------------------------------------------------------


def make_premium() -> Premium:
    return Premium(
        total_sum_insured=ev_native(30000.0),
        gross_premium=ev_native(None),        # blank in many samples
        premium_pct=ev_native(None),          # blank in many samples
        farmers_premium=ev_native(None),
    )


# ---------------------------------------------------------------------------
# SourceMeta factory
# ---------------------------------------------------------------------------


def make_source_meta() -> SourceMeta:
    return SourceMeta(
        file_name="orange_jhalawar_2019.pdf",
        page_range=[3, 4],
        is_scan=False,
        ocr_used=False,
    )


# ---------------------------------------------------------------------------
# DocumentFields factory
# ---------------------------------------------------------------------------


def make_document() -> DocumentFields:
    return DocumentFields(
        scheme_name=ev_native("Weather Based Crop Insurance Scheme"),
        scheme_year=ev_native("2019-20"),
        state=ev_native("Rajasthan", raw="Rajsthan"),
        district=ev_native("Jhalawar"),
        crop=ev_native("Orange"),
        season=ev_native(None),
        unit=ev_native("HECTARE"),
        reference_weather_station=ev_native("As Per Notification"),
        annexure_ref=ev_native("Annexure 3"),
        premium=make_premium(),
        source_meta=make_source_meta(),
    )


# ---------------------------------------------------------------------------
# Minimal rainfall_multistrike peril factory
# ---------------------------------------------------------------------------


def make_multistrike_phase(label: str = "Phase I") -> RainfallMultistrikePhase:
    return RainfallMultistrikePhase(
        label=ev_native(label),
        sub_periods=[
            DatePeriod(
                start=ev_native("2019-06-25"),
                end=ev_native("2019-08-15"),
            )
        ],
        strike_1=ev_native(65.0),
        strike_2=ev_native(None),       # one-strike variant
        exit=ev_native(0.0),
        rate_1=ev_native(100.0),
        rate_2=ev_native(None),         # one-strike variant
        rate_unit=ev_native("Rs/mm"),
        max_payout=ev_native(15000.0),
    )


def make_multistrike_structure() -> RainfallMultistrikeStructure:
    return RainfallMultistrikeStructure(
        measure=ev_native("aggregate_rainfall"),
        unit=ev_native("mm"),
        direction=ev_native("deficit"),
        phases=[make_multistrike_phase("Phase I"), make_multistrike_phase("Phase II")],
        total_payout=ev_native(30000.0),
    )


def make_peril_envelope() -> PerilEnvelope:
    return PerilEnvelope(
        peril_id="deficit_rainfall",
        peril_label_raw=ev_native("1. DEFICIT RAINFALL"),
        archetype="rainfall_multistrike",
        cover_objective=ev_native("To protect against deficit rainfall"),
        event_definition=ev_native("Aggregate rainfall below strike level"),
        cover_period=CoverPeriod(
            start=ev_native("2019-06-25"),
            end=ev_native("2019-10-15"),
        ),
        structure=make_multistrike_structure(),
    )


# ---------------------------------------------------------------------------
# StructuredTermsheet factory
# ---------------------------------------------------------------------------


def make_structured_termsheet() -> StructuredTermsheet:
    return StructuredTermsheet(
        document=make_document(),
        perils=[make_peril_envelope()],
        extraction_confidence=ExtractionConfidence(
            overall=0.92,
            per_field={"document.scheme_name": 1.0, "perils[0].structure.strike_1": 0.85},
        ),
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_structured_termsheet() -> StructuredTermsheet:
    return make_structured_termsheet()


@pytest.fixture
def valid_validated_termsheet(valid_structured_termsheet) -> ValidatedTermsheet:
    return ValidatedTermsheet(
        termsheet=valid_structured_termsheet,
        flags=[],
        review_required=False,
    )
