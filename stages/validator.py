"""
stages/validator.py — Stage 5: Independent Deterministic Validation Engine

Evaluates a StructuredTermsheet against insurance domain and mathematical
rules without invoking any LLM, producing a typed ValidatedTermsheet.

Rule Categories:
  1. completeness_check    — verifies presence of required document and peril fields
  2. strike_exit_sanity    — verifies sensible direction relationships between strikes and exits
  3. payout_arithmetic     — verifies phase max_payout sums reconcile with total_payout
  4. premium_contradiction — detects gross_premium=0 while farmers_premium > 0 (Guava trap)
  5. sum_insured_check     — verifies total_sum_insured exists and is > 0
  6. confidence_threshold  — flags fields with confidence below threshold (0.75) and triggers review_required

Design Principles:
  - Completely deterministic: Pure Python + Pydantic.
  - Read-only: Does NOT mutate, alter, or "fix" any values.
  - Review routing: Sets review_required=True if any error-severity flag is present or
    if any field's extraction confidence falls below threshold.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.common import ExtractedValue
from models.structured_termsheet import (
    RainfallMultistrikeStructure,
    RainfallSinglePayoutStructure,
    StructuredTermsheet,
    TemperaturePhasedStructure,
    WindPhasedStructure,
)
from models.validated_termsheet import ValidatedTermsheet, ValidationFlag

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAPPED_PATH = Path("data/intermediates/mapped_termsheet.json")
DEFAULT_OUTPUT_PATH = Path("data/intermediates/validated_termsheet.json")
DEFAULT_CONFIDENCE_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# Helper: Extract ExtractedValue or Raw Value
# ---------------------------------------------------------------------------


def _get_val(obj: Any) -> Any:
    """Extract .value if obj is an ExtractedValue, else return obj."""
    if isinstance(obj, ExtractedValue):
        return obj.value
    if isinstance(obj, dict) and "value" in obj and "source" in obj:
        return obj.get("value")
    return obj


# ---------------------------------------------------------------------------
# Check 1: Completeness
# ---------------------------------------------------------------------------


def check_completeness(termsheet: StructuredTermsheet) -> list[ValidationFlag]:
    flags: list[ValidationFlag] = []
    doc = termsheet.document

    required_doc_fields = [
        ("document.scheme_name", doc.scheme_name),
        ("document.scheme_year", doc.scheme_year),
        ("document.state", doc.state),
        ("document.district", doc.district),
        ("document.crop", doc.crop),
        ("document.unit", doc.unit),
        ("document.reference_weather_station", doc.reference_weather_station),
    ]

    for path, field in required_doc_fields:
        val = _get_val(field)
        if val is None or str(val).strip() == "":
            flags.append(
                ValidationFlag(
                    field_path=path,
                    rule="completeness_check",
                    severity="error",
                    message=f"Required document field '{path}' is missing or blank",
                )
            )

    if not termsheet.perils:
        flags.append(
            ValidationFlag(
                field_path="perils",
                rule="completeness_check",
                severity="error",
                message="Termsheet contains no peril cover envelopes",
            )
        )

    for i, peril in enumerate(termsheet.perils):
        p_prefix = f"perils[{i}]"
        if not peril.peril_id:
            flags.append(
                ValidationFlag(
                    field_path=f"{p_prefix}.peril_id",
                    rule="completeness_check",
                    severity="error",
                    message="Peril is missing 'peril_id'",
                )
            )
        if not _get_val(peril.cover_objective):
            flags.append(
                ValidationFlag(
                    field_path=f"{p_prefix}.cover_objective",
                    rule="completeness_check",
                    severity="warning",
                    message="Peril is missing 'cover_objective'",
                )
            )

        struct = peril.structure
        if isinstance(struct, TemperaturePhasedStructure):
            if not struct.phases:
                flags.append(
                    ValidationFlag(
                        field_path=f"{p_prefix}.structure.phases",
                        rule="completeness_check",
                        severity="error",
                        message="Temperature phased peril has no phases defined",
                    )
                )
        elif isinstance(struct, RainfallMultistrikeStructure):
            if not struct.phases:
                flags.append(
                    ValidationFlag(
                        field_path=f"{p_prefix}.structure.phases",
                        rule="completeness_check",
                        severity="error",
                        message="Rainfall multistrike peril has no phases defined",
                    )
                )
        elif isinstance(struct, RainfallSinglePayoutStructure):
            if not struct.periods:
                flags.append(
                    ValidationFlag(
                        field_path=f"{p_prefix}.structure.periods",
                        rule="completeness_check",
                        severity="error",
                        message="Rainfall single payout peril has no periods defined",
                    )
                )
        elif isinstance(struct, WindPhasedStructure):
            if not struct.trigger_blocks:
                flags.append(
                    ValidationFlag(
                        field_path=f"{p_prefix}.structure.trigger_blocks",
                        rule="completeness_check",
                        severity="error",
                        message="Wind phased peril has no trigger blocks defined",
                    )
                )

    return flags


# ---------------------------------------------------------------------------
# Check 2: Strike / Exit Sanity
# ---------------------------------------------------------------------------


def check_strike_exit_sanity(termsheet: StructuredTermsheet) -> list[ValidationFlag]:
    flags: list[ValidationFlag] = []

    for i, peril in enumerate(termsheet.perils):
        p_prefix = f"perils[{i}].structure"
        struct = peril.structure

        if isinstance(struct, RainfallMultistrikeStructure):
            direction = str(_get_val(struct.direction)).lower()
            for ph_idx, phase in enumerate(struct.phases):
                for sp_idx, sp in enumerate(phase.sub_periods):
                    s1 = _get_val(sp.strike_1)
                    s2 = _get_val(sp.strike_2)
                    ex = _get_val(sp.exit)
                    sp_prefix = f"{p_prefix}.phases[{ph_idx}].sub_periods[{sp_idx}]"

                    if direction == "deficit":
                        # Deficit rainfall: exit < strike_1 (and exit < strike_2 < strike_1 if strike_2 exists)
                        if s1 is not None and ex is not None and ex >= s1:
                            flags.append(
                                ValidationFlag(
                                    field_path=f"{sp_prefix}.exit",
                                    rule="strike_exit_sanity",
                                    severity="error",
                                    message=f"Deficit rainfall exit ({ex}) must be less than strike_1 ({s1})",
                                )
                            )
                        if s1 is not None and s2 is not None and s2 >= s1:
                            flags.append(
                                ValidationFlag(
                                    field_path=f"{sp_prefix}.strike_2",
                                    rule="strike_exit_sanity",
                                    severity="error",
                                    message=f"Deficit rainfall strike_2 ({s2}) must be less than strike_1 ({s1})",
                                )
                            )
                        if s2 is not None and ex is not None and ex > s2:
                            flags.append(
                                ValidationFlag(
                                    field_path=f"{sp_prefix}.exit",
                                    rule="strike_exit_sanity",
                                    severity="error",
                                    message=f"Deficit rainfall exit ({ex}) must be less than or equal to strike_2 ({s2})",
                                )
                            )

        elif isinstance(struct, (TemperaturePhasedStructure, WindPhasedStructure)):
            direction = str(_get_val(struct.direction)).lower()
            strike = _get_val(struct.strike)
            exit_val = _get_val(struct.exit)

            if direction == "upward":
                # Upward deviation: strike < exit
                if strike is not None and exit_val is not None and strike >= exit_val:
                    flags.append(
                        ValidationFlag(
                            field_path=f"{p_prefix}.strike",
                            rule="strike_exit_sanity",
                            severity="error",
                            message=f"Upward peril strike ({strike}) must be less than exit ({exit_val})",
                        )
                    )

        elif isinstance(struct, RainfallSinglePayoutStructure):
            direction = str(_get_val(struct.direction)).lower()
            s1 = _get_val(struct.strike_1)
            s2 = _get_val(struct.strike_2)
            ex = _get_val(struct.exit)

            if direction in ("unseasonal", "excess"):
                # Unseasonal / Excess rainfall: strike_1 < strike_2 < exit
                if s1 is not None and ex is not None and s1 >= ex:
                    flags.append(
                        ValidationFlag(
                            field_path=f"{p_prefix}.strike_1",
                            rule="strike_exit_sanity",
                            severity="error",
                            message=f"Excess/unseasonal rainfall strike_1 ({s1}) must be less than exit ({ex})",
                        )
                    )
                if s1 is not None and s2 is not None and s1 >= s2:
                    flags.append(
                        ValidationFlag(
                            field_path=f"{p_prefix}.strike_2",
                            rule="strike_exit_sanity",
                            severity="error",
                            message=f"Excess/unseasonal rainfall strike_1 ({s1}) must be less than strike_2 ({s2})",
                        )
                    )
                if s2 is not None and ex is not None and s2 >= ex:
                    flags.append(
                        ValidationFlag(
                            field_path=f"{p_prefix}.strike_2",
                            rule="strike_exit_sanity",
                            severity="error",
                            message=f"Excess/unseasonal rainfall strike_2 ({s2}) must be less than exit ({ex})",
                        )
                    )

    return flags


# ---------------------------------------------------------------------------
# Check 3: Payout Arithmetic
# ---------------------------------------------------------------------------


def check_payout_arithmetic(termsheet: StructuredTermsheet) -> list[ValidationFlag]:
    flags: list[ValidationFlag] = []

    for i, peril in enumerate(termsheet.perils):
        p_prefix = f"perils[{i}].structure"
        struct = peril.structure

        if isinstance(struct, RainfallMultistrikeStructure):
            total_payout = _get_val(struct.total_payout)
            if total_payout is not None and struct.phases:
                sub_period_payouts = [
                    _get_val(sp.max_payout)
                    for ph in struct.phases
                    for sp in ph.sub_periods
                    if _get_val(sp.max_payout) is not None
                ]
                sum_payouts = sum(sub_period_payouts)

                if abs(sum_payouts - float(total_payout)) > 0.01:
                    flags.append(
                        ValidationFlag(
                            field_path=f"{p_prefix}.total_payout",
                            rule="payout_arithmetic",
                            severity="error",
                            message=(
                                f"Sum of sub-period max payouts ({sum_payouts:.2f}) does not reconcile with "
                                f"total_payout ({float(total_payout):.2f})"
                            ),
                        )
                    )

        elif isinstance(struct, (TemperaturePhasedStructure, WindPhasedStructure)):
            strike = _get_val(struct.strike)
            exit_val = _get_val(struct.exit)
            payout_rate = _get_val(struct.payout_rate)
            max_payout = _get_val(struct.max_payout)

            if all(v is not None for v in (strike, exit_val, payout_rate, max_payout)):
                span = float(exit_val) - float(strike)
                expected_max = span * float(payout_rate)
                # Allow minor fractional rounding tolerance (e.g. 2083.33 * 18 = 37499.94 vs 37500.0)
                if abs(expected_max - float(max_payout)) > 1.0:
                    flags.append(
                        ValidationFlag(
                            field_path=f"{p_prefix}.max_payout",
                            rule="payout_arithmetic",
                            severity="error",
                            message=(
                                f"Payout calculation mismatch: rate ({payout_rate}) * (exit - strike) ({span}) = "
                                f"{expected_max:.2f}, expected max_payout = {float(max_payout):.2f}"
                            ),
                        )
                    )

    return flags


# ---------------------------------------------------------------------------
# Check 4: Premium Contradictions
# ---------------------------------------------------------------------------


def check_premium_contradictions(termsheet: StructuredTermsheet) -> list[ValidationFlag]:
    flags: list[ValidationFlag] = []
    prem = termsheet.document.premium

    gross = _get_val(prem.gross_premium)
    farmers = _get_val(prem.farmers_premium)

    # Contradiction: gross_premium is explicitly zero, but farmer pays a positive amount
    if gross is not None and gross == 0.0 and farmers is not None and farmers > 0.0:
        flags.append(
            ValidationFlag(
                field_path="document.premium.gross_premium",
                rule="premium_contradiction",
                severity="error",
                message=(
                    f"Contradiction in premium block: gross_premium is 0.0 but farmers_premium is {farmers:.2f}. "
                    "Flagged per WBCIS data integrity rules."
                ),
            )
        )

    return flags


# ---------------------------------------------------------------------------
# Check 5: Sum Insured Check
# ---------------------------------------------------------------------------


def check_sum_insured(termsheet: StructuredTermsheet) -> list[ValidationFlag]:
    flags: list[ValidationFlag] = []
    prem = termsheet.document.premium

    si = _get_val(prem.total_sum_insured)
    if si is None:
        flags.append(
            ValidationFlag(
                field_path="document.premium.total_sum_insured",
                rule="sum_insured_check",
                severity="error",
                message="total_sum_insured is missing or null",
            )
        )
    elif not isinstance(si, (int, float)) or si <= 0:
        flags.append(
            ValidationFlag(
                field_path="document.premium.total_sum_insured",
                rule="sum_insured_check",
                severity="error",
                message=f"total_sum_insured ({si}) must be a positive number greater than 0",
            )
        )

    return flags


# ---------------------------------------------------------------------------
# Check 6: Confidence Threshold
# ---------------------------------------------------------------------------


def _walk_extracted_values(data: Any, path: str = "") -> list[tuple[str, ExtractedValue]]:
    """Recursively discover all ExtractedValue instances and their paths."""
    found: list[tuple[str, ExtractedValue]] = []
    if isinstance(data, ExtractedValue):
        found.append((path, data))
    elif isinstance(data, dict):
        for k, v in data.items():
            child_path = f"{path}.{k}" if path else k
            found.extend(_walk_extracted_values(v, child_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            child_path = f"{path}[{i}]"
            found.extend(_walk_extracted_values(item, child_path))
    elif hasattr(data, "__dict__"):
        for k, v in data.__dict__.items():
            if k.startswith("_"):
                continue
            child_path = f"{path}.{k}" if path else k
            found.extend(_walk_extracted_values(v, child_path))
    return found


def check_confidence_threshold(
    termsheet: StructuredTermsheet,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[ValidationFlag]:
    """
    Flags any leaf scalar whose confidence score is strictly below the threshold.
    """
    flags: list[ValidationFlag] = []
    extracted_nodes = _walk_extracted_values(termsheet)

    for path, ev in extracted_nodes:
        # If value is present and confidence is strictly below threshold
        if ev.value is not None and ev.confidence is not None and ev.confidence < threshold:
            flags.append(
                ValidationFlag(
                    field_path=path,
                    rule="confidence_threshold",
                    severity="warning",
                    message=(
                        f"Field '{path}' extraction confidence ({ev.confidence:.2f}) is below "
                        f"threshold ({threshold:.2f}). Human underwriter review recommended."
                    ),
                )
            )

    return flags


# ---------------------------------------------------------------------------
# Main Validator Pipeline
# ---------------------------------------------------------------------------


def validate_termsheet(
    termsheet: StructuredTermsheet | dict | str | Path,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> ValidatedTermsheet:
    """
    Run all independent deterministic validation checks against a StructuredTermsheet.

    Args:
        termsheet: StructuredTermsheet instance, dict, or path to mapped JSON.
        confidence_threshold: Threshold below which review_required is triggered.

    Returns:
        ValidatedTermsheet with all findings and review_required flag.
    """
    if isinstance(termsheet, (str, Path)):
        p = Path(termsheet)
        if not p.exists():
            raise FileNotFoundError(f"Mapped termsheet not found at: {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        ts = StructuredTermsheet.model_validate(data)
    elif isinstance(termsheet, dict):
        ts = StructuredTermsheet.model_validate(termsheet)
    elif isinstance(termsheet, StructuredTermsheet):
        ts = termsheet
    else:
        raise TypeError(f"Unsupported termsheet type: {type(termsheet)}")

    all_flags: list[ValidationFlag] = []

    # Execute all 6 check suites
    all_flags.extend(check_completeness(ts))
    all_flags.extend(check_strike_exit_sanity(ts))
    all_flags.extend(check_payout_arithmetic(ts))
    all_flags.extend(check_premium_contradictions(ts))
    all_flags.extend(check_sum_insured(ts))
    all_flags.extend(check_confidence_threshold(ts, threshold=confidence_threshold))

    # review_required is True if any error exists OR any confidence flag was raised
    has_errors = any(flag.severity == "error" for flag in all_flags)
    has_low_confidence = any(flag.rule == "confidence_threshold" for flag in all_flags)

    review_required = has_errors or has_low_confidence

    return ValidatedTermsheet(
        termsheet=ts,
        flags=all_flags,
        review_required=review_required,
    )


def persist(
    validated: ValidatedTermsheet,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Persist ValidatedTermsheet to JSON disk artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_text = validated.model_dump_json(indent=2)
    output_path.write_text(json_text, encoding="utf-8")
    return output_path


def run(
    input_path: Path = DEFAULT_MAPPED_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> ValidatedTermsheet:
    """Main Stage 5 execution entry point."""
    validated = validate_termsheet(input_path, confidence_threshold=confidence_threshold)
    persist(validated, output_path)

    err_count = sum(1 for f in validated.flags if f.severity == "error")
    warn_count = sum(1 for f in validated.flags if f.severity == "warning")

    print(
        f"Validation complete: {len(validated.flags)} flags ({err_count} errors, {warn_count} warnings), "
        f"review_required={validated.review_required}"
    )
    return validated


if __name__ == "__main__":
    run()
