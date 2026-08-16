"""
eval/evaluator.py — Field-by-field comparator for WBCIS pipeline output.

Compares two plain JSON dicts (expected, actual) and returns a list of
EvalResult objects — one per leaf scalar encountered in the expected tree.

Design decisions (Phase 2, approved):

  VALUE vs PROVENANCE
    .value mismatch inside an ExtractedValue wrapper → FAIL
    .source / .confidence mismatch                  → WARN
    Rationale: provenance drift alone should not block a pipeline run;
    only business-value divergence is a hard failure.

  ARRAY ORDERING
    Index-based.  perils[0] vs perils[0].  No content-hash reordering.
    Over-engineering the ordering problem is deferred.

  EXTRA FIELDS IN ACTUAL (present in actual, absent in expected)
    → WARN, not FAIL.
    The fixture may predate fields added later (e.g. a new `raw` key).
    An unexpected extra field is unverified, not wrong.

  MISSING FIELD IN ACTUAL (present in expected, absent in actual)
    → FAIL.
    The pipeline dropped something it must produce.

  NULL HANDLING
    null in both                         → PASS (both agree the field is blank).
    null in expected, non-null in actual → FAIL (pipeline invented a value;
                                                 violates "never invent missing
                                                 values" rule in PROJECT_CONTEXT.md).
    non-null in expected, null in actual → FAIL (pipeline lost a value).

ExtractedValue detection heuristic:
    A dict node is treated as an ExtractedValue wrapper when it contains
    a "source" key whose value is one of the three known source literals.
    This works for model-shaped output.  For flat fixture JSON (like the
    Orange ground-truth which has no wrappers), every scalar is compared
    directly as a leaf.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


@dataclass
class EvalResult:
    """
    The outcome for one leaf comparison.

    Attributes:
        path:     Dotted/bracketed path, e.g. "perils[1].structure.rate_1".
        verdict:  PASS, FAIL, or WARN.
        expected: Value from the expected (ground-truth) document.
        actual:   Value found in the actual (pipeline) document.
        note:     Human-readable reason for non-PASS verdicts.
    """
    path: str
    verdict: Verdict
    expected: Any
    actual: Any
    note: str = ""


# ---------------------------------------------------------------------------
# Known ExtractedValue source literals
# ---------------------------------------------------------------------------

_EV_SOURCES = {"native_exact", "ocr", "agent_inferred"}

def _is_extracted_value(node: Any) -> bool:
    """
    Return True if node looks like an ExtractedValue wrapper.
    Detected by the presence of a "source" key whose value is one of the
    three known source literals.
    """
    return (
        isinstance(node, dict)
        and node.get("source") in _EV_SOURCES
    )


# ---------------------------------------------------------------------------
# Core recursive walker
# ---------------------------------------------------------------------------

def _walk(
    expected: Any,
    actual: Any,
    path: str,
    results: list[EvalResult],
) -> None:
    """
    Recursively walk `expected`, compare every leaf against `actual`.
    Appends EvalResult entries to `results` in place.
    """

    # --- ExtractedValue wrapper in expected -------------------------------
    if _is_extracted_value(expected):
        _compare_extracted_value(expected, actual, path, results)
        return

    # --- ExtractedValue wrapper in actual (expected is scalar / flat fixture) ---
    if _is_extracted_value(actual):
        if isinstance(expected, dict) and "normalized" in expected:
            _walk(expected.get("normalized"), actual.get("value"), f"{path}.normalized", results)
            if "raw" in expected:
                _walk(expected.get("raw"), actual.get("raw"), f"{path}.raw", results)
            return
        _walk(expected, actual.get("value"), path, results)
        return

    # --- Dict node (non-ExtractedValue) -----------------------------------
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            results.append(EvalResult(
                path=path,
                verdict=Verdict.FAIL,
                expected=expected,
                actual=actual,
                note="expected a dict, got a different type",
            ))
            return

        for key, exp_val in expected.items():
            child_path = f"{path}.{key}" if path else key
            if key not in actual:
                results.append(EvalResult(
                    path=child_path,
                    verdict=Verdict.FAIL,
                    expected=exp_val,
                    actual=None,
                    note="field present in expected but missing in actual",
                ))
            else:
                _walk(exp_val, actual[key], child_path, results)

        # Extra keys in actual → WARN
        for key in actual:
            if key not in expected:
                child_path = f"{path}.{key}" if path else key
                results.append(EvalResult(
                    path=child_path,
                    verdict=Verdict.WARN,
                    expected=None,
                    actual=actual[key],
                    note="extra field in actual not present in expected (unverified)",
                ))
        return

    # --- List node --------------------------------------------------------
    if isinstance(expected, list):
        if not isinstance(actual, list):
            results.append(EvalResult(
                path=path,
                verdict=Verdict.FAIL,
                expected=expected,
                actual=actual,
                note="expected a list, got a different type",
            ))
            return

        for i, exp_item in enumerate(expected):
            item_path = f"{path}[{i}]"
            if i >= len(actual):
                results.append(EvalResult(
                    path=item_path,
                    verdict=Verdict.FAIL,
                    expected=exp_item,
                    actual=None,
                    note=f"expected list has index [{i}] but actual list is shorter",
                ))
            else:
                _walk(exp_item, actual[i], item_path, results)

        # Extra items in actual list → WARN
        for i in range(len(expected), len(actual)):
            item_path = f"{path}[{i}]"
            results.append(EvalResult(
                path=item_path,
                verdict=Verdict.WARN,
                expected=None,
                actual=actual[i],
                note="extra item in actual list not present in expected (unverified)",
            ))
        return

    # --- Leaf scalar ------------------------------------------------------
    _compare_leaf(expected, actual, path, results)


def _compare_leaf(expected: Any, actual: Any, path: str, results: list[EvalResult]) -> None:
    """Compare a single scalar leaf value."""

    if expected is None and actual is None:
        results.append(EvalResult(path=path, verdict=Verdict.PASS, expected=None, actual=None))
        return

    if expected is None and actual is not None:
        results.append(EvalResult(
            path=path,
            verdict=Verdict.FAIL,
            expected=None,
            actual=actual,
            note="expected null but actual has a value (pipeline invented a value; "
                 "violates 'never invent missing values' rule)",
        ))
        return

    if expected is not None and actual is None:
        results.append(EvalResult(
            path=path,
            verdict=Verdict.FAIL,
            expected=expected,
            actual=None,
            note="expected a value but actual is null (pipeline lost a value)",
        ))
        return

    # Both non-null — compare with numeric tolerance for floats
    if _values_equal(expected, actual):
        results.append(EvalResult(path=path, verdict=Verdict.PASS, expected=expected, actual=actual))
    else:
        results.append(EvalResult(
            path=path,
            verdict=Verdict.FAIL,
            expected=expected,
            actual=actual,
            note="value mismatch",
        ))


def _values_equal(a: Any, b: Any) -> bool:
    """
    Equality check with a small float tolerance (1e-6 relative) to absorb
    floating-point serialisation noise (e.g. 56.25 vs 56.250000001).
    String comparison is exact and case-sensitive.
    """
    if type(a) != type(b):
        # Allow int/float cross-comparison (56 == 56.0)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            fa, fb = float(a), float(b)
            if fa == 0.0 and fb == 0.0:
                return True
            if fa == 0.0 or fb == 0.0:
                return abs(fa - fb) < 1e-9
            return abs(fa - fb) / max(abs(fa), abs(fb)) < 1e-6
        return False
    if isinstance(a, float):
        if a == 0.0 and b == 0.0:
            return True
        if a == 0.0 or b == 0.0:
            return abs(a - b) < 1e-9
        return abs(a - b) / max(abs(a), abs(b)) < 1e-6
    return a == b


def _compare_extracted_value(
    expected: dict,
    actual: Any,
    path: str,
    results: list[EvalResult],
) -> None:
    """
    Compare an ExtractedValue wrapper.
    .value → FAIL on mismatch.
    .source / .confidence → WARN on mismatch.
    """
    if not isinstance(actual, dict):
        # Actual is a plain scalar where expected is a wrapped value.
        # Compare .value against the bare scalar.
        exp_val = expected.get("value")
        _compare_leaf(exp_val, actual, f"{path}.value", results)
        return

    # Both are dicts — compare .value (FAIL), .source/.confidence (WARN)
    exp_value = expected.get("value")
    act_value = actual.get("value") if isinstance(actual, dict) else actual

    _compare_leaf(exp_value, act_value, f"{path}.value", results)

    # source — WARN only
    if "source" in expected and "source" in actual:
        if expected["source"] != actual["source"]:
            results.append(EvalResult(
                path=f"{path}.source",
                verdict=Verdict.WARN,
                expected=expected["source"],
                actual=actual["source"],
                note="source provenance differs (not a pipeline value error)",
            ))
        else:
            results.append(EvalResult(
                path=f"{path}.source",
                verdict=Verdict.PASS,
                expected=expected["source"],
                actual=actual["source"],
            ))

    # confidence — WARN only
    if "confidence" in expected and "confidence" in actual:
        exp_c = expected.get("confidence")
        act_c = actual.get("confidence")
        if not _values_equal(exp_c, act_c) if (exp_c is not None and act_c is not None) else exp_c != act_c:
            results.append(EvalResult(
                path=f"{path}.confidence",
                verdict=Verdict.WARN,
                expected=exp_c,
                actual=act_c,
                note="confidence score differs (not a pipeline value error)",
            ))
        else:
            results.append(EvalResult(
                path=f"{path}.confidence",
                verdict=Verdict.PASS,
                expected=exp_c,
                actual=act_c,
            ))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compare(expected: dict, actual: dict) -> list[EvalResult]:
    """
    Compare two JSON documents field-by-field.

    Args:
        expected: Ground-truth document (e.g. loaded from eval/fixtures/).
        actual:   Pipeline output to be validated.

    Returns:
        List of EvalResult, one per leaf encountered in expected (plus WARN
        entries for extra keys found only in actual).

    Notes:
        - Input dicts are not mutated.
        - Order of results follows depth-first traversal of expected.
        - Both dicts may contain nested dicts, lists, and scalars.
          ExtractedValue wrappers (dicts with a "source" key) are handled
          specially: .value → FAIL on mismatch, .source/.confidence → WARN.
    """
    results: list[EvalResult] = []
    _walk(copy.deepcopy(expected), copy.deepcopy(actual), path="", results=results)
    return results


def summary(results: list[EvalResult]) -> dict[str, int]:
    """Return counts of PASS / FAIL / WARN across a result list."""
    counts: dict[str, int] = {"PASS": 0, "FAIL": 0, "WARN": 0}
    for r in results:
        counts[r.verdict.value] += 1
    return counts
