"""
models/common.py — Shared primitive types used by every stage-boundary model.

Design decisions (see docs/PROJECT_CONTEXT.md + task approval):

ExtractedValue[T]
  Every leaf scalar extracted from a termsheet is wrapped in this type so that
  provenance and confidence are co-located with the value.

  Confidence rule (locked):
    - source="native_exact"   → confidence defaults to 1.0 if omitted; never None after construction.
    - source="ocr"            → confidence is required; None raises ValidationError.
    - source="agent_inferred" → confidence is required; None raises ValidationError.

  raw field:
    Stores the un-normalised string exactly as it appeared in the source document,
    e.g. "S.Madhopur" before normalisation to "Sawai Madhopur".
    May be None when no normalisation was applied (source and value are identical).

CoverPeriod
  Optional date range. start/end are themselves Optional[ExtractedValue[str]]
  so that a cover_period object can exist with one or both bounds missing.
  The *parent* field (e.g. PerilEnvelope.cover_period) is Optional[CoverPeriod];
  it is set to None when dates cannot be parsed at all.

DatePeriod
  A non-optional date range used inside archetype sub-period lists where both
  bounds are expected to be present (though value inside ExtractedValue may be
  null if extraction fails).
"""

from __future__ import annotations

from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, field_validator, model_validator

T = TypeVar("T")


class ExtractedValue(BaseModel, Generic[T]):
    """
    Provenance wrapper for every leaf scalar extracted from a termsheet.

    Attributes:
        value:      The normalised, typed value.  May be None for legitimately
                    blank source fields.  Blank ≠ zero — never coerce to 0.
        raw:        Un-normalised source string.  None when value required no
                    normalisation.
        source:     Provenance of the extracted value.
        confidence: Extraction confidence in [0.0, 1.0].  See confidence rule above.
    """

    value: Optional[T] = None
    raw: Optional[str] = None
    source: Literal["native_exact", "ocr", "agent_inferred"]
    confidence: Optional[float] = None

    @field_validator("confidence")
    @classmethod
    def _confidence_in_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {v!r}")
        return v

    @model_validator(mode="after")
    def _apply_confidence_rule(self) -> "ExtractedValue[T]":
        """
        Enforce the confidence rule:
          native_exact  → default to 1.0 (maximum certainty by definition).
          ocr / agent_inferred → explicit float required; caller must state
                                 their uncertainty.
        """
        if self.source == "native_exact":
            if self.confidence is None:
                self.confidence = 1.0
        else:
            if self.confidence is None:
                raise ValueError(
                    f"confidence is required when source='{self.source}'. "
                    "Only source='native_exact' may omit it "
                    "(it will default to 1.0)."
                )
        return self


class CoverPeriod(BaseModel):
    """
    Date range for a cover window.  Both bounds are individually optional
    because date parsing may fail for one bound but succeed for the other.
    ISO-8601 strings ("YYYY-MM-DD") are expected inside the ExtractedValue.
    """

    start: Optional[ExtractedValue[str]] = None
    end: Optional[ExtractedValue[str]] = None


class DatePeriod(BaseModel):
    """
    A date range used inside archetype sub-period lists (e.g. Phase I
    sub-periods in rainfall_multistrike).  Both bounds are expected to be
    present, so neither is Optional at the field level — though the string
    *value* inside ExtractedValue may be None if extraction fails.
    """

    start: ExtractedValue[str]
    end: ExtractedValue[str]
