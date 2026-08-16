"""
models/structured_termsheet.py — Stage 4 output (Reconstruct & Map).

This module defines the full extraction schema as Pydantic models.
Shape is authoritative against docs/source/wbcis_extraction_schema.md.

Key design decisions (all approved, see task approval message):

1.  WRAP ALL LEAF SCALARS
    Every extracted value field is wrapped in ExtractedValue[T] regardless
    of how "safe" the source seems.  Archetype internals (strike, exit,
    payout_rate) are the highest-risk fields in the pipeline — they come
    from merged-cell reconstruction and possible OCR — and are the primary
    reason the trust layer exists.

2.  ARCHETYPE DISCRIMINATED UNION
    Each structure variant carries a `type` field whose Literal value matches
    its archetype.  Pydantic's discriminated union uses `type` as the key.
    This lets the engine validate the structure strictly at construction time
    without ambiguous try-each-variant logic.

3.  NULLABLE BLANKS
    Fields documented as "frequently blank" (gross_premium, premium_pct,
    farmers_premium) use ExtractedValue[Optional[float]].  The value *inside*
    the wrapper can be None.  They are never coerced to 0.

4.  ARCHETYPE-B VARIANTS
    rainfall_multistrike has a one-strike variant (Onions) and a two-strike
    variant (Orange/Kinnow/Guava).  strike_2 / rate_2 are modelled as
    ExtractedValue[Optional[float]] — same archetype, optional fields, not
    separate archetypes.

5.  WIND TRIGGER BLOCKS
    wind_phased uses trigger_blocks (list[WindTriggerBlock]) as the sole
    phase representation.  A flat 4-phase sheet (Guava) is one block;
    Kinnow/Orange use two.  No parallel flat phases list.

6.  SOURCE META UNWRAPPED
    SourceMeta fields (file_name, is_scan, ocr_used, page_range) are plain
    Python types — they are pipeline metadata, not extracted business values.

7.  RAW + NORMALISED
    ExtractedValue carries a `raw` field for the un-normalised source string
    (e.g. "S.Madhopur" before → "Sawai Madhopur").  See models/common.py.

Schema reference: docs/source/wbcis_extraction_schema.md
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from models.common import CoverPeriod, DatePeriod, ExtractedValue


# ---------------------------------------------------------------------------
# Pipeline source metadata (§2 — source_meta)
# Not extracted business values — not wrapped in ExtractedValue.
# ---------------------------------------------------------------------------


class SourceMeta(BaseModel):
    """
    Metadata about how the document was processed by the pipeline.
    These fields describe the pipeline's own decisions, not extracted content,
    so they are NOT wrapped in ExtractedValue.

    Attributes:
        file_name:  Original filename of the source PDF.
        page_range: 1-based page numbers that contributed to this termsheet,
                    e.g. [3, 4] for a two-page annexure.
        is_scan:    True if any page required OCR (rasterised source).
        ocr_used:   True if OCR was actually invoked during extraction.
    """

    file_name: str
    page_range: list[int]
    is_scan: bool
    ocr_used: bool


# ---------------------------------------------------------------------------
# Premium block (§2.1)
# ---------------------------------------------------------------------------


class Premium(BaseModel):
    """
    Premium description block.  gross_premium, premium_pct, and
    farmers_premium are frequently blank in the WBCIS samples.
    Their value *inside* ExtractedValue may be None — never coerced to 0.

    Known data trap: Guava sample shows total_premium=0 but farmers_premium=1938.
    Capture both; flag the contradiction in Stage 5 — do not silently fix it.
    """

    total_sum_insured: ExtractedValue[float]
    gross_premium: ExtractedValue[Optional[float]]      # frequently blank in samples
    premium_pct: ExtractedValue[Optional[float]]        # frequently blank in samples
    farmers_premium: ExtractedValue[Optional[float]]    # present in Guava sample


# ---------------------------------------------------------------------------
# Document-level fields (§2)
# ---------------------------------------------------------------------------


class DocumentFields(BaseModel):
    """
    Fields extracted once per document from the header and top-level sections.

    season is str | None (not a Literal) because season labels may vary
    across states — "kharif" and "rabi" are the known values but the set
    is not considered closed for MVP.

    district and state carry a `raw` value inside ExtractedValue for the
    un-normalised form (e.g. raw="Rajsthan", value="Rajasthan").
    """

    scheme_name: ExtractedValue[str]
    scheme_year: ExtractedValue[str]
    state: ExtractedValue[str]                          # raw may be "Rajsthan"
    district: ExtractedValue[str]                       # raw may be "S.Madhopur"
    crop: ExtractedValue[str]                           # may include season, e.g. "Onion kharif"
    season: ExtractedValue[Optional[str]]               # "kharif" / "rabi" / None
    unit: ExtractedValue[str]                           # e.g. "HECTARE"
    reference_weather_station: ExtractedValue[str]      # often "As Per Notification"
    annexure_ref: ExtractedValue[str]                   # e.g. "Annexure 3"
    premium: Premium
    source_meta: SourceMeta


# ---------------------------------------------------------------------------
# Archetype A — temperature_phased (§4.A)
# ---------------------------------------------------------------------------


class TemperaturePhase(BaseModel):
    """
    One phase row in a temperature_phased peril table.
    trigger varies by phase; strike/exit/payout_rate span all phases (on parent).
    """

    label: ExtractedValue[str]                          # e.g. "I", "II", … "VI"
    period: Optional[CoverPeriod] = None
    trigger: ExtractedValue[float]


class TemperaturePhasedStructure(BaseModel):
    """
    Archetype A — temperature_phased.
    N phases (usually 6), one trigger per phase.
    strike, exit, payout_rate are single values spanning all phases.
    direction: "upward" — captured from event definition text.
    """

    type: Literal["temperature_phased"] = "temperature_phased"
    measure: ExtractedValue[str]                        # e.g. "max_temperature"
    unit: ExtractedValue[str]                           # e.g. "°C"
    direction: ExtractedValue[str]                      # "upward" from event definition
    strike: ExtractedValue[float]
    exit: ExtractedValue[float]
    payout_rate: ExtractedValue[float]
    payout_rate_unit: ExtractedValue[str]               # e.g. "Rs/°C"
    max_payout: ExtractedValue[float]
    phases: list[TemperaturePhase]


# ---------------------------------------------------------------------------
# Archetype B — rainfall_multistrike (§4.B)
# ---------------------------------------------------------------------------


class RainfallMultistrikeSubPeriod(BaseModel):
    """
    One sub-period within a Phase of rainfall_multistrike.
    Carries the date period and the specific strike, exit, rate, and max_payout.
    """

    period: DatePeriod
    strike_1: ExtractedValue[float]
    strike_2: ExtractedValue[Optional[float]]           # None in one-strike variant
    exit: ExtractedValue[float]
    rate_1: ExtractedValue[float]
    rate_2: ExtractedValue[Optional[float]]             # None in one-strike variant
    max_payout: ExtractedValue[float]


class RainfallMultistrikePhase(BaseModel):
    """
    One phase (Phase I or Phase II) within a rainfall_multistrike peril.
    Groups multiple sub-periods under a phase label.
    """

    label: ExtractedValue[str]                          # "Phase I", "Phase II"
    sub_periods: list[RainfallMultistrikeSubPeriod]


class RainfallMultistrikeStructure(BaseModel):
    """
    Archetype B — rainfall_multistrike.
    Phase I / Phase II structure with nested sub-period date columns and parameters.
    """

    type: Literal["rainfall_multistrike"] = "rainfall_multistrike"
    measure: ExtractedValue[str]                        # "aggregate_rainfall"
    direction: ExtractedValue[str]                      # "deficit" or "excess"
    unit: ExtractedValue[str]                           # "mm"
    rate_unit: ExtractedValue[str]                      # "Rs/mm"
    phases: list[RainfallMultistrikePhase]
    total_payout: ExtractedValue[float]                 # "Payout Phase I & II (Rs)"



# ---------------------------------------------------------------------------
# Archetype C — rainfall_single_payout (§4.C)
# ---------------------------------------------------------------------------


class RainfallSinglePayoutStructure(BaseModel):
    """
    Archetype C — rainfall_single_payout.
    Single flat cover with no phase structure.
    strike_2 and rate_2 are optional (absent in some samples).
    direction: "excess" or "unseasonal" from cover objective.
    payout_mode: always "single" in MVP samples.
    """

    type: Literal["rainfall_single_payout"] = "rainfall_single_payout"
    measure: ExtractedValue[str]                        # "aggregate_rainfall"
    unit: ExtractedValue[str]                           # "mm"
    direction: ExtractedValue[str]                      # "excess" or "unseasonal"
    payout_mode: ExtractedValue[str]                    # "single" in all MVP samples
    periods: list[DatePeriod]                           # sometimes multiple date columns
    strike_1: ExtractedValue[float]
    strike_2: ExtractedValue[Optional[float]]           # optional
    exit: ExtractedValue[float]
    rate_1: ExtractedValue[float]
    rate_2: ExtractedValue[Optional[float]]             # optional
    rate_unit: ExtractedValue[str]                      # e.g. "Rs/mm"
    max_payout: ExtractedValue[float]


# ---------------------------------------------------------------------------
# Archetype D — wind_phased (§4.D)
# ---------------------------------------------------------------------------


class WindPhase(BaseModel):
    """One phase row in a wind_phased trigger block."""

    label: ExtractedValue[str]                          # "I", "II", … "VI"
    period: Optional[CoverPeriod] = None
    trigger: ExtractedValue[float]


class WindTriggerBlock(BaseModel):
    """
    A grouping of wind phases that share a payout rate.

    Guava: 4 flat phases → represented as a single WindTriggerBlock.
    Kinnow / Orange: 6 phases split into 2 blocks of 3, each with its own
    payout rate (stored on the parent WindPhasedStructure — one payout_rate
    value spans all blocks in the MVP schema; if per-block rates are needed
    later, add payout_rate here).

    This list-of-blocks representation covers both cases without adding a
    separate top-level flat phases field.
    """

    block_label: ExtractedValue[str]
    period: Optional[CoverPeriod] = None                # overall period of this block
    phases: list[WindPhase]


class WindPhasedStructure(BaseModel):
    """
    Archetype D — wind_phased.
    N phases (4 or 6), sometimes grouped into 2 trigger blocks.
    strike, exit, payout_rate span all blocks/phases.
    """

    type: Literal["wind_phased"] = "wind_phased"
    measure: ExtractedValue[str]                        # "max_wind_speed"
    unit: ExtractedValue[str]                           # "km/h"
    direction: ExtractedValue[str]                      # "upward"
    strike: ExtractedValue[float]
    exit: ExtractedValue[float]
    payout_rate: ExtractedValue[float]
    payout_rate_unit: ExtractedValue[str]               # "Rs/km/h"
    max_payout: ExtractedValue[float]
    trigger_blocks: list[WindTriggerBlock]


# ---------------------------------------------------------------------------
# Discriminated union over archetype structures
# ---------------------------------------------------------------------------

PerilStructure = Annotated[
    Union[
        TemperaturePhasedStructure,
        RainfallMultistrikeStructure,
        RainfallSinglePayoutStructure,
        WindPhasedStructure,
    ],
    Field(discriminator="type"),
]
"""
Pydantic selects the correct archetype structure class using the `type`
discriminator field.  Passing an unknown `type` value raises ValidationError.
"""


# ---------------------------------------------------------------------------
# Peril envelope (§3 shared envelope)
# ---------------------------------------------------------------------------


class PerilEnvelope(BaseModel):
    """
    Shared envelope wrapping any archetype-specific structure.

    peril_id is a free string — not a Literal — because the same semantic
    label (e.g. "deficit_rainfall") can appear more than once on a single
    document (e.g. a Phase I/II block and a separate 2B section).  The
    archetype field is the real structural discriminator.

    cover_period is Optional[CoverPeriod]: set to None when dates cannot be
    parsed at all.  Within CoverPeriod, individual bounds may also be None.

    structure is a PerilStructure discriminated union.  The `type` field on
    the structure must be consistent with archetype, but this consistency is
    not enforced by a validator at MVP — it is implicitly guaranteed because
    Stage 4 construction sets both.
    """

    peril_id: str                                       # free label, not Literal
    peril_label_raw: ExtractedValue[str]                # e.g. "1. HIGH TEMPERATURE"
    archetype: Literal[
        "temperature_phased",
        "rainfall_multistrike",
        "rainfall_single_payout",
        "wind_phased",
    ]
    cover_objective: ExtractedValue[str]
    event_definition: ExtractedValue[str]
    cover_period: Optional[CoverPeriod] = None
    structure: PerilStructure


# ---------------------------------------------------------------------------
# Extraction confidence summary (§5)
# ---------------------------------------------------------------------------


class ExtractionConfidence(BaseModel):
    """
    Aggregate and per-field confidence scores for the extraction run.
    per_field keys are dotted field paths, e.g. "perils[0].structure.strike".
    """

    overall: float
    per_field: dict[str, float]


# ---------------------------------------------------------------------------
# Stage 4 top-level output
# ---------------------------------------------------------------------------


class StructuredTermsheet(BaseModel):
    """
    Stage 4 (Reconstruct & Map) boundary contract.

    Contains all extracted and structured content.  Does NOT contain
    validation flags — those are added by Stage 5 (ValidatedTermsheet).

    Shape matches docs/source/wbcis_extraction_schema.md §5 (minus flags,
    which belong to Stage 5).
    """

    document: DocumentFields
    perils: list[PerilEnvelope]
    extraction_confidence: ExtractionConfidence
