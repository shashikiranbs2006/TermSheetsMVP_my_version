"""
tests/test_review_report.py — Tests for Stage 6: Human Review & Provenance Report.

Covers:
1. Real clean Orange validated_termsheet.json renders a prominent, intentional
   "no fields require review" state (no empty tables, clear pass banner).
2. Synthetic low-confidence field (< 0.75) is surfaced in underwriter action items.
3. Field with BOTH a ValidationFlag and low confidence combines both findings cleanly.
4. General / unmapped validation flags are rendered in the action items section.
5. Edge case: empty perils list handled gracefully without exceptions.
6. Report persistence and CLI runner verification.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from models.common import ExtractedValue
from models.structured_termsheet import StructuredTermsheet
from models.validated_termsheet import ValidatedTermsheet, ValidationFlag
from stages.review_report import generate_review_report, persist, run

VALIDATED_PATH = Path("data/intermediates/validated_termsheet.json")


@pytest.fixture(scope="module")
def real_validated_termsheet() -> ValidatedTermsheet:
    if not VALIDATED_PATH.exists():
        pytest.skip(f"Validated termsheet not found at: {VALIDATED_PATH}")
    data = json.loads(VALIDATED_PATH.read_text(encoding="utf-8"))
    return ValidatedTermsheet.model_validate(data)


# ---------------------------------------------------------------------------
# 1. Real Orange Clean Validation Report
# ---------------------------------------------------------------------------


class TestRealOrangeReviewReport:
    def test_real_orange_clean_report_renders_clear_no_review_state(
        self, real_validated_termsheet: ValidatedTermsheet
    ):
        """
        Explicitly verify that the real clean Orange termsheet renders an intentional,
        professional 'no fields require review' state rather than an empty table.
        """
        report = generate_review_report(real_validated_termsheet)

        # Header and Document context
        assert "# WBCIS Termsheet Human Review & Provenance Report" in report
        assert "Orange" in report
        assert "Jhalawar" in report
        assert "Rajasthan" in report

        # Executive status
        assert "PASS — CLEAN EXTRACTION (NO REVIEW REQUIRED)" in report
        assert "All extracted parameters meet the confidence threshold" in report

        # Section 1 Underwriter Action Items
        assert "## 1. Underwriter Action Items" in report
        assert "No fields require human review." in report
        assert "0 validation errors or warnings" in report

        # Ensure no broken or empty review table is rendered
        assert "| Field Path | Extracted Value |" not in report

        # Metrics Table
        assert "| **Review Required** | `NO` |" in report
        assert "| **Native PDF Exact** |" in report
        assert "| **Agent Inferred (Bedrock)** |" in report

        # Provenance Log
        assert "## 2. Non-Native Provenance Log (AI / OCR Mapped Fields)" in report
        assert "high_temperature" in report
        assert "deficit_rainfall" in report
        assert "unseasonal_rainfall" in report
        assert "high_wind_speed" in report

        # Per-Peril Breakdown
        assert "## 3. Per-Peril Extraction & Provenance Breakdown" in report
        assert "temperature_phased" in report
        assert "rainfall_multistrike" in report

        # Audit Rules Log
        assert "## 4. Deterministic Audit Rules Log" in report
        assert "✅ PASS (0 flags)" in report


# ---------------------------------------------------------------------------
# 2. Synthetic Test: Low Confidence Surfaced in Action Items
# ---------------------------------------------------------------------------


class TestLowConfidenceSurfacing:
    def test_single_low_confidence_field_surfaced_in_action_items(
        self, real_validated_termsheet: ValidatedTermsheet
    ):
        broken = real_validated_termsheet.model_copy(deep=True)
        broken.review_required = True

        # Lower confidence of a peril parameter
        p_temp = broken.termsheet.perils[0]
        p_temp.structure.phases[0].trigger.confidence = 0.65

        report = generate_review_report(broken, confidence_threshold=0.75)

        # Executive status shows review required
        assert "EXECUTIVE STATUS: REVIEW REQUIRED" in report

        # Section 1 table present
        assert "## 1. Underwriter Action Items" in report
        assert "| Field Path | Extracted Value | Confidence | Source | Validation Findings / Review Reason |" in report
        assert "`perils[0].structure.phases[0].trigger`" in report
        assert "0.65" in report
        assert "Low confidence (0.65 < 0.75)" in report


# ---------------------------------------------------------------------------
# 3. Synthetic Test: Combined ValidationFlag & Low Confidence
# ---------------------------------------------------------------------------


class TestCombinedFlagAndConfidence:
    def test_field_with_flag_and_low_confidence_combines_findings(
        self, real_validated_termsheet: ValidatedTermsheet
    ):
        broken = real_validated_termsheet.model_copy(deep=True)
        broken.review_required = True

        field_path = "document.premium.total_sum_insured"
        broken.termsheet.document.premium.total_sum_insured.confidence = 0.60

        broken.flags = [
            ValidationFlag(
                field_path=field_path,
                rule="sum_insured_check",
                severity="error",
                message="Total sum insured must be greater than 0",
            )
        ]

        report = generate_review_report(broken, confidence_threshold=0.75)

        assert "`document.premium.total_sum_insured`" in report
        assert "0.60" in report
        assert "Low confidence (0.60 < 0.75)" in report
        assert "[ERROR] sum_insured_check: Total sum insured must be greater than 0" in report


# ---------------------------------------------------------------------------
# 4. Synthetic Test: Unmapped General Flags
# ---------------------------------------------------------------------------


class TestUnmappedFlags:
    def test_general_flag_rendered_in_unmapped_section(
        self, real_validated_termsheet: ValidatedTermsheet
    ):
        broken = real_validated_termsheet.model_copy(deep=True)
        broken.review_required = True
        broken.flags = [
            ValidationFlag(
                field_path="",
                rule="completeness_check",
                severity="error",
                message="Document header missing mandatory crop notification",
            )
        ]

        report = generate_review_report(broken)
        assert "General / Unmapped Document Flags" in report
        assert "Document header missing mandatory crop notification" in report


# ---------------------------------------------------------------------------
# 5. Edge Case: Empty Perils List
# ---------------------------------------------------------------------------


class TestEmptyPerilsEdgeCase:
    def test_empty_perils_list_renders_cleanly_without_exceptions(
        self, real_validated_termsheet: ValidatedTermsheet
    ):
        broken = real_validated_termsheet.model_copy(deep=True)
        broken.termsheet.perils = []

        report = generate_review_report(broken)
        assert "# WBCIS Termsheet Human Review & Provenance Report" in report
        assert "*No perils extracted in this document.*" in report


# ---------------------------------------------------------------------------
# 6. Persistence & Run
# ---------------------------------------------------------------------------


class TestReportPersistence:
    def test_persist_and_run(self, real_validated_termsheet: ValidatedTermsheet):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_p = Path(tmpdir) / "review_report.md"
            val_p = Path(tmpdir) / "validated_termsheet.json"

            val_p.write_text(real_validated_termsheet.model_dump_json(indent=2), encoding="utf-8")

            report_str = run(val_p, out_p)
            assert out_p.exists()
            saved_content = out_p.read_text(encoding="utf-8")
            assert saved_content == report_str
            assert len(saved_content) > 500
