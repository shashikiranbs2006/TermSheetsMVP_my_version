"""
models/validated_termsheet.py — Stage 5 output (Validate).

Wraps StructuredTermsheet with structured validation findings.

Design note from docs/source/wbcis_extraction_schema.md §7:
  "Output = a structured validation report, not a pass/fail boolean.
   In insurance the flags *are* the product."

review_required is True when any flag with severity="error" is present,
OR when any field's confidence falls below the pipeline threshold.
Stage 5 sets this field; Stage 6 reads it to decide routing.
"""

from typing import Literal

from pydantic import BaseModel

from models.structured_termsheet import StructuredTermsheet


class ValidationFlag(BaseModel):
    """
    A single structured validation finding produced by the Stage 5 rule engine.

    Attributes:
        field_path: Dotted/bracketed path to the offending field, e.g.
                    "perils[0].structure.exit" or "document.premium.gross_premium".
                    Empty string for document-level findings with no single field.
        rule:       Machine-readable rule identifier.  Examples:
                    "monotonicity_check", "premium_contradiction",
                    "si_missing", "payout_arithmetic", "confidence_threshold".
        severity:   "error"   — must be resolved before Riskwolf emission.
                    "warning" — should be reviewed; may emit with an underwriter note.
                    "info"    — informational; no action required.
        message:    Human-readable description for the underwriter review report.
    """

    field_path: str
    rule: str
    severity: Literal["error", "warning", "info"]
    message: str


class ValidatedTermsheet(BaseModel):
    """
    Stage 5 (Validate) boundary contract.

    Attributes:
        termsheet:       The Stage 4 structured output being validated.
        flags:           All validation findings.  Empty list = no findings.
        review_required: True if any error-severity flag is present or any
                         field falls below the confidence threshold.
                         Stage 6 routes on this field.
    """

    termsheet: StructuredTermsheet
    flags: list[ValidationFlag] = []
    review_required: bool
