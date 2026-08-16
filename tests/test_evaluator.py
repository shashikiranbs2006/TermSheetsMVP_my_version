"""
tests/test_evaluator.py — Tests for the Phase 2 eval harness.

Covers all four required tests plus supporting cases:

REQUIRED:
  1. Two identical documents → all results are PASS (no FAIL, no WARN).
  2. Changing "crop": "Orange" → "Apple" in actual → FAIL at document.crop.
  3. Field present in expected but missing in actual → FAIL (not crash).
  4. Field present in actual but not in expected → WARN (documented decision).

ADDITIONAL:
  - Null in both → PASS.
  - Non-null in expected, null in actual → FAIL (pipeline lost a value).
  - Null in expected, non-null in actual → WARN (pipeline filled a blank).
  - ExtractedValue wrapper: .value mismatch → FAIL on .value path.
  - ExtractedValue wrapper: .source mismatch → WARN on .source path.
  - Float comparison with small serialisation noise → PASS.
  - Nested array: perils[1].structure.rate_1 mismatch → FAIL at correct path.
  - Orange fixture vs itself → all PASS (regression guard on the real fixture).
  - Deep missing field (inside a nested list) → FAIL at correct path.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from eval.evaluator import EvalResult, Verdict, compare, summary

# ---------------------------------------------------------------------------
# Path to the ground-truth fixture
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).parent.parent / "eval" / "fixtures" / "orange_jhalawar_gt.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def results_by_path(results: list[EvalResult]) -> dict[str, EvalResult]:
    """Index results by path for easy lookup in assertions."""
    return {r.path: r for r in results}


def fail_paths(results: list[EvalResult]) -> list[str]:
    return [r.path for r in results if r.verdict == Verdict.FAIL]


def warn_paths(results: list[EvalResult]) -> list[str]:
    return [r.path for r in results if r.verdict == Verdict.WARN]


# ---------------------------------------------------------------------------
# 1. Identical documents → all PASS
# ---------------------------------------------------------------------------

class TestIdenticalDocuments:
    def test_flat_identical(self):
        """Simplest possible case: two identical flat dicts."""
        doc = {"crop": "Orange", "district": "Jhalawar", "year": "2019-20"}
        results = compare(doc, copy.deepcopy(doc))
        assert all(r.verdict == Verdict.PASS for r in results), \
            f"Unexpected non-PASS: {[r for r in results if r.verdict != Verdict.PASS]}"

    def test_nested_identical(self):
        doc = {
            "document": {"crop": "Orange", "premium": {"total_sum_insured": 125000}},
            "perils": [{"peril_id": "high_temperature", "structure": {"strike": 4, "exit": 22}}],
        }
        results = compare(doc, copy.deepcopy(doc))
        assert not fail_paths(results), f"FAILs in identical compare: {fail_paths(results)}"

    def test_orange_fixture_vs_itself(self):
        """
        The real Orange fixture compared against itself must produce zero FAILs.
        This is the regression guard — if this breaks, the evaluator is broken.
        """
        doc = load_fixture()
        results = compare(doc, copy.deepcopy(doc))
        fails = fail_paths(results)
        assert fails == [], f"Orange fixture self-compare produced FAILs: {fails}"

    def test_null_null_is_pass(self):
        doc = {"gross_premium": None}
        results = compare(doc, copy.deepcopy(doc))
        assert results[0].verdict == Verdict.PASS

    def test_list_identical(self):
        doc = {"phases": [{"label": "I", "trigger": 29.0}, {"label": "II", "trigger": 31.0}]}
        results = compare(doc, copy.deepcopy(doc))
        assert not fail_paths(results)


# ---------------------------------------------------------------------------
# 2. Changing crop Orange → Apple → FAIL at document.crop
# ---------------------------------------------------------------------------

class TestCropMismatch:
    """
    THE KEY REGRESSION TEST.
    Proves the evaluator actually catches value drift — not just silently passes.
    """

    def test_crop_change_produces_fail(self):
        expected = {"document": {"crop": "Orange", "district": "Jhalawar"}}
        actual   = {"document": {"crop": "Apple",  "district": "Jhalawar"}}

        results = compare(expected, actual)
        by_path = results_by_path(results)

        assert "document.crop" in by_path, "No result generated for document.crop"
        assert by_path["document.crop"].verdict == Verdict.FAIL, \
            f"Expected FAIL for crop mismatch, got {by_path['document.crop'].verdict}"
        assert by_path["document.crop"].expected == "Orange"
        assert by_path["document.crop"].actual   == "Apple"

    def test_crop_change_on_real_fixture(self):
        """Same test driven off the real Orange fixture."""
        expected = load_fixture()
        actual   = copy.deepcopy(expected)

        # Navigate to the crop field — the fixture uses nested dict format
        # (raw/normalized) so we manipulate accordingly
        # In the flat fixture, document.crop is {"raw": "Orange", "normalized": "Orange"}
        crop_node = actual["document"]["crop"]
        if isinstance(crop_node, dict):
            # Normalised-form fixture — break the normalized value
            crop_node["normalized"] = "Apple"
        else:
            actual["document"]["crop"] = "Apple"

        results = compare(expected, actual)
        fails = fail_paths(results)
        assert any("document.crop" in p for p in fails), \
            f"Expected a FAIL on document.crop, got fails: {fails}"

    def test_correct_value_district_still_passes(self):
        """Changing only crop should not break unrelated fields."""
        expected = {"document": {"crop": "Orange", "district": "Jhalawar"}}
        actual   = {"document": {"crop": "Apple",  "district": "Jhalawar"}}
        by_path  = results_by_path(compare(expected, actual))

        assert by_path["document.district"].verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# 3. Field in expected but missing in actual → FAIL
# ---------------------------------------------------------------------------

class TestMissingInActual:
    def test_top_level_missing(self):
        expected = {"crop": "Orange", "district": "Jhalawar"}
        actual   = {"crop": "Orange"}  # district missing

        by_path = results_by_path(compare(expected, actual))
        assert "district" in by_path
        assert by_path["district"].verdict == Verdict.FAIL
        assert "missing in actual" in by_path["district"].note

    def test_nested_field_missing(self):
        expected = {"document": {"crop": "Orange", "premium": {"total_sum_insured": 125000}}}
        actual   = {"document": {"crop": "Orange", "premium": {}}}

        by_path = results_by_path(compare(expected, actual))
        assert by_path["document.premium.total_sum_insured"].verdict == Verdict.FAIL

    def test_missing_in_list_item(self):
        expected = {"perils": [{"peril_id": "x", "structure": {"strike": 4}}]}
        actual   = {"perils": [{"peril_id": "x", "structure": {}}]}  # strike missing

        by_path = results_by_path(compare(expected, actual))
        assert by_path["perils[0].structure.strike"].verdict == Verdict.FAIL

    def test_does_not_crash_on_missing_field(self):
        """A missing field must produce a FAIL result, never raise an exception."""
        expected = {"a": {"b": {"c": 42}}}
        actual   = {"a": {}}
        try:
            results = compare(expected, actual)
        except Exception as exc:
            pytest.fail(f"compare() raised {exc} instead of producing a FAIL result")
        assert any(r.verdict == Verdict.FAIL for r in results)

    def test_shorter_actual_list(self):
        expected = {"phases": [{"trigger": 29.0}, {"trigger": 31.0}]}
        actual   = {"phases": [{"trigger": 29.0}]}  # second item missing

        by_path = results_by_path(compare(expected, actual))
        assert by_path["phases[1]"].verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# 4. Extra field in actual (absent in expected) → WARN
# ---------------------------------------------------------------------------

class TestExtraInActual:
    """
    Decision (documented in evaluator.py):
    Extra fields in actual → WARN, not FAIL.
    The fixture may predate fields added by later pipeline versions.
    An unexpected extra field is unverified, not wrong.
    """

    def test_extra_top_level_field(self):
        expected = {"crop": "Orange"}
        actual   = {"crop": "Orange", "new_field": "surprise"}

        by_path = results_by_path(compare(expected, actual))
        assert "new_field" in by_path
        assert by_path["new_field"].verdict == Verdict.WARN
        assert "extra field" in by_path["new_field"].note

    def test_extra_nested_field(self):
        expected = {"document": {"crop": "Orange"}}
        actual   = {"document": {"crop": "Orange", "raw_text": "Orange (Kinnow)"}}

        by_path = results_by_path(compare(expected, actual))
        assert by_path["document.raw_text"].verdict == Verdict.WARN

    def test_extra_field_does_not_produce_fail(self):
        expected = {"crop": "Orange"}
        actual   = {"crop": "Orange", "extra": "data"}
        results  = compare(expected, actual)
        assert not fail_paths(results)

    def test_extra_list_item_in_actual(self):
        expected = {"phases": [{"trigger": 29.0}]}
        actual   = {"phases": [{"trigger": 29.0}, {"trigger": 31.0}]}  # extra item

        by_path = results_by_path(compare(expected, actual))
        assert "phases[1]" in by_path
        assert by_path["phases[1]"].verdict == Verdict.WARN


# ---------------------------------------------------------------------------
# ExtractedValue wrapper behaviour
# ---------------------------------------------------------------------------

class TestExtractedValueComparison:
    """
    Decision (documented in evaluator.py):
    .value mismatch → FAIL (at <path>.value)
    .source mismatch → WARN (at <path>.source)
    .confidence mismatch → WARN (at <path>.confidence)
    """

    def _ev(self, value, source="native_exact", confidence=1.0) -> dict:
        return {"value": value, "source": source, "confidence": confidence}

    def test_value_match_is_pass(self):
        expected = {"strike": self._ev(65.0)}
        actual   = {"strike": self._ev(65.0)}
        by_path  = results_by_path(compare(expected, actual))
        assert by_path["strike.value"].verdict == Verdict.PASS

    def test_value_mismatch_is_fail(self):
        expected = {"strike": self._ev(65.0)}
        actual   = {"strike": self._ev(55.0)}
        by_path  = results_by_path(compare(expected, actual))
        assert by_path["strike.value"].verdict == Verdict.FAIL
        assert by_path["strike.value"].expected == 65.0
        assert by_path["strike.value"].actual   == 55.0

    def test_source_mismatch_is_warn(self):
        expected = {"strike": self._ev(65.0, source="native_exact")}
        actual   = {"strike": self._ev(65.0, source="ocr")}
        by_path  = results_by_path(compare(expected, actual))
        assert by_path["strike.source"].verdict == Verdict.WARN
        # Value is still correct
        assert by_path["strike.value"].verdict == Verdict.PASS

    def test_confidence_mismatch_is_warn(self):
        expected = {"strike": self._ev(65.0, confidence=1.0)}
        actual   = {"strike": self._ev(65.0, confidence=0.72)}
        by_path  = results_by_path(compare(expected, actual))
        assert by_path["strike.confidence"].verdict == Verdict.WARN
        assert by_path["strike.value"].verdict == Verdict.PASS

    def test_flat_actual_vs_wrapped_expected(self):
        """
        Expected has a wrapper; actual (early pipeline) emits plain scalar.
        Should compare .value against the scalar and produce PASS if equal.
        """
        expected = {"strike": {"value": 65.0, "source": "native_exact", "confidence": 1.0}}
        actual   = {"strike": 65.0}
        by_path  = results_by_path(compare(expected, actual))
        assert by_path["strike.value"].verdict == Verdict.PASS

    def test_flat_actual_vs_wrapped_expected_fail(self):
        expected = {"strike": {"value": 65.0, "source": "native_exact", "confidence": 1.0}}
        actual   = {"strike": 55.0}
        by_path  = results_by_path(compare(expected, actual))
        assert by_path["strike.value"].verdict == Verdict.FAIL


# ---------------------------------------------------------------------------
# Null semantics
# ---------------------------------------------------------------------------

class TestNullSemantics:
    def test_both_null_is_pass(self):
        results = compare({"gross_premium": None}, {"gross_premium": None})
        assert results[0].verdict == Verdict.PASS

    def test_expected_null_actual_value_is_fail(self):
        """Pipeline invented a value that the fixture says is blank.
        Violates the PROJECT_CONTEXT.md rule 'never invent missing values'."""
        results = compare({"gross_premium": None}, {"gross_premium": 5000.0})
        assert results[0].verdict == Verdict.FAIL
        assert "invented a value" in results[0].note

    def test_expected_value_actual_null_is_fail(self):
        """Pipeline dropped a value the fixture said should be present."""
        results = compare({"total_sum_insured": 125000}, {"total_sum_insured": None})
        assert results[0].verdict == Verdict.FAIL
        assert "pipeline lost a value" in results[0].note


# ---------------------------------------------------------------------------
# Float tolerance
# ---------------------------------------------------------------------------

class TestFloatTolerance:
    def test_float_serialisation_noise_passes(self):
        """56.25 vs 56.250000001 is serialisation noise, not a real diff."""
        expected = {"rate_1": 56.25}
        actual   = {"rate_1": 56.250000001}
        results  = compare(expected, actual)
        assert results[0].verdict == Verdict.PASS

    def test_real_float_diff_fails(self):
        """56.25 vs 55.00 is a real mismatch."""
        expected = {"rate_1": 56.25}
        actual   = {"rate_1": 55.00}
        results  = compare(expected, actual)
        assert results[0].verdict == Verdict.FAIL

    def test_int_float_cross_type_passes(self):
        """Fixture may store 65 (int); pipeline may emit 65.0 (float)."""
        expected = {"strike": 65}
        actual   = {"strike": 65.0}
        results  = compare(expected, actual)
        assert results[0].verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# Nested array path accuracy
# ---------------------------------------------------------------------------

class TestPathAccuracy:
    def test_nested_array_path_correct(self):
        """FAIL at perils[1].structure.rate_1 must include the correct path."""
        expected = {
            "perils": [
                {"structure": {"rate_1": 56.25}},
                {"structure": {"rate_1": 45.00}},
            ]
        }
        actual = {
            "perils": [
                {"structure": {"rate_1": 56.25}},
                {"structure": {"rate_1": 99.99}},  # broken
            ]
        }
        by_path = results_by_path(compare(expected, actual))
        assert "perils[1].structure.rate_1" in by_path
        assert by_path["perils[1].structure.rate_1"].verdict == Verdict.FAIL
        assert by_path["perils[0].structure.rate_1"].verdict == Verdict.PASS

    def test_deep_phase_trigger_path(self):
        expected = {"perils": [{"structure": {"phases": [{"trigger": 29.0}, {"trigger": 31.0}]}}]}
        actual   = {"perils": [{"structure": {"phases": [{"trigger": 29.0}, {"trigger": 32.0}]}}]}
        by_path  = results_by_path(compare(expected, actual))
        assert by_path["perils[0].structure.phases[1].trigger"].verdict == Verdict.FAIL
        assert by_path["perils[0].structure.phases[0].trigger"].verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# summary() helper
# ---------------------------------------------------------------------------

class TestSummary:
    def test_counts_correct(self):
        results = [
            EvalResult("a", Verdict.PASS, 1, 1),
            EvalResult("b", Verdict.PASS, 2, 2),
            EvalResult("c", Verdict.FAIL, 3, 4, "mismatch"),
            EvalResult("d", Verdict.WARN, None, 5, "extra"),
        ]
        counts = summary(results)
        assert counts == {"PASS": 2, "FAIL": 1, "WARN": 1}

    def test_all_pass_summary(self):
        doc = {"x": 1, "y": 2}
        results = compare(doc, copy.deepcopy(doc))
        counts = summary(results)
        assert counts["FAIL"] == 0
        assert counts["WARN"] == 0
        assert counts["PASS"] == 2
