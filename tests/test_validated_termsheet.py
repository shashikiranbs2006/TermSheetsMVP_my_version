"""
tests/test_validated_termsheet.py — Tests for Stage 5 ValidatedTermsheet.

Covers:
  - Valid construction with empty flags.
  - ValidationFlag with each severity level.
  - Invalid severity raises ValidationError.
  - review_required is a required field (not defaulted).
  - Serialisation round-trip.
  - Outputs (Stage 6) stub construction.
"""

import pytest
from pydantic import ValidationError

from models.outputs import Outputs
from models.validated_termsheet import ValidationFlag, ValidatedTermsheet


class TestValidationFlag:
    def test_error_severity_accepted(self):
        f = ValidationFlag(
            field_path="document.premium.total_sum_insured",
            rule="si_missing",
            severity="error",
            message="Total sum insured is missing.",
        )
        assert f.severity == "error"

    def test_warning_severity_accepted(self):
        f = ValidationFlag(
            field_path="perils[0].structure.exit",
            rule="monotonicity_check",
            severity="warning",
            message="exit > strike for a deficit cover — direction may be wrong.",
        )
        assert f.severity == "warning"

    def test_info_severity_accepted(self):
        f = ValidationFlag(
            field_path="",
            rule="premium_contradiction",
            severity="info",
            message="total_premium=0 but farmers_premium=1938.",
        )
        assert f.severity == "info"

    def test_invalid_severity_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            ValidationFlag(
                field_path="x",
                rule="r",
                severity="critical",          # not in Literal["error","warning","info"]
                message="m",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("severity",) for e in errors)

    def test_empty_field_path_accepted(self):
        """Document-level findings with no single responsible field."""
        f = ValidationFlag(field_path="", rule="r", severity="info", message="m")
        assert f.field_path == ""


class TestValidatedTermsheet:
    def test_valid_no_flags(self, valid_validated_termsheet):
        vt = valid_validated_termsheet
        assert vt.flags == []
        assert vt.review_required is False

    def test_flags_default_to_empty_list(self, valid_structured_termsheet):
        vt = ValidatedTermsheet(
            termsheet=valid_structured_termsheet,
            review_required=False,
        )
        assert vt.flags == []

    def test_with_flags(self, valid_structured_termsheet):
        flag = ValidationFlag(
            field_path="perils[0].structure.strike_1",
            rule="confidence_threshold",
            severity="warning",
            message="confidence 0.62 is below threshold 0.80.",
        )
        vt = ValidatedTermsheet(
            termsheet=valid_structured_termsheet,
            flags=[flag],
            review_required=True,
        )
        assert len(vt.flags) == 1
        assert vt.review_required is True

    def test_missing_review_required_raises(self, valid_structured_termsheet):
        """review_required has no default and must be supplied explicitly."""
        with pytest.raises(ValidationError):
            ValidatedTermsheet(termsheet=valid_structured_termsheet)

    def test_serialisation_round_trip(self, valid_validated_termsheet):
        data = valid_validated_termsheet.model_dump()
        restored = ValidatedTermsheet.model_validate(data)
        assert restored == valid_validated_termsheet


class TestOutputsStub:
    def test_outputs_with_no_riskwolf_payload(self, valid_validated_termsheet):
        out = Outputs(
            termsheet=valid_validated_termsheet,
            human_readable="Orange / Jhalawar WBCIS 2019-20\n...",
        )
        assert out.riskwolf_payload is None

    def test_outputs_with_stub_payload(self, valid_validated_termsheet):
        """Riskwolf payload is a dict stub — any dict is accepted."""
        out = Outputs(
            termsheet=valid_validated_termsheet,
            human_readable="...",
            riskwolf_payload={"todo": "replace when Riskwolf contract confirmed"},
        )
        assert out.riskwolf_payload["todo"] is not None

    def test_outputs_missing_human_readable_raises(self, valid_validated_termsheet):
        with pytest.raises(ValidationError):
            Outputs(termsheet=valid_validated_termsheet)
