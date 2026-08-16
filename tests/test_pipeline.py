"""
tests/test_pipeline.py — Integration and Idempotency tests for Phase 9 (Full Pipeline).

Tests:
1. Full pipeline execution on Orange_TermSheet.pdf.
2. Verification of all intermediate artifacts written and re-readable.
3. Verification of ValidatedTermsheet with review_required=False and 0 errors.
4. Custom intermediates directory support.
5. Missing file error handling.
6. Pipeline idempotency across runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from models.page_manifest import PageManifest
from models.raw_cells import RawCells
from models.segmented_peril import SegmentedPerils
from models.structured_termsheet import StructuredTermsheet
from models.validated_termsheet import ValidatedTermsheet
from stages.pipeline import run_pipeline


@pytest.fixture(scope="module")
def orange_pdf_path() -> Path:
    p = Path("docs/source/Orange_TermSheet.pdf")
    assert p.exists(), f"Orange termsheet PDF not found at {p}"
    return p


def test_pipeline_end_to_end_execution(orange_pdf_path: Path, tmp_path: Path):
    """Run full pipeline on Orange_TermSheet.pdf into a tmp dir and verify output."""
    validated = run_pipeline(
        pdf_path=orange_pdf_path,
        intermediates_dir=tmp_path,
        quiet=True,
    )

    assert isinstance(validated, ValidatedTermsheet)
    assert validated.review_required is False
    assert len(validated.flags) == 0

    # Verify structured termsheet attributes
    ts = validated.termsheet
    assert ts.document.state.value == "Rajasthan"
    assert ts.document.district.value == "Jhalawar"
    assert ts.document.crop.value == "Orange"
    assert ts.document.premium.total_sum_insured.value == 125000
    assert len(ts.perils) == 4


def test_pipeline_all_intermediate_artifacts_persisted_and_readable(
    orange_pdf_path: Path, tmp_path: Path
):
    """Verify all 6 intermediate files are saved and validly deserialized."""
    run_pipeline(
        pdf_path=orange_pdf_path,
        intermediates_dir=tmp_path,
        quiet=True,
    )

    # 1. Page manifest
    manifest_file = tmp_path / "page_manifest.json"
    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifests = [PageManifest.model_validate(item) for item in manifest_data]
    assert len(manifests) == 1
    assert manifests[0].route == "native"

    # 2. Raw cells
    raw_cells_file = tmp_path / "raw_cells.json"
    assert raw_cells_file.exists()
    raw_cells = RawCells.model_validate_json(raw_cells_file.read_text(encoding="utf-8"))
    assert len(raw_cells.cells) == 330

    # 3. Segmented perils
    seg_file = tmp_path / "segmented_perils.json"
    assert seg_file.exists()
    segmented = SegmentedPerils.model_validate_json(seg_file.read_text(encoding="utf-8"))
    assert len(segmented.perils) == 4

    # 4. Reconstructed perils
    rec_file = tmp_path / "reconstructed_perils.json"
    assert rec_file.exists()
    rec_data = json.loads(rec_file.read_text(encoding="utf-8"))
    assert "reconstructed_perils" in rec_data
    assert len(rec_data["reconstructed_perils"]) == 4

    # 5. Mapped termsheet & agent logs
    map_file = tmp_path / "mapped_termsheet.json"
    logs_file = tmp_path / "mapping_agent_logs.json"
    assert map_file.exists()
    assert logs_file.exists()
    mapped_ts = StructuredTermsheet.model_validate_json(map_file.read_text(encoding="utf-8"))
    assert len(mapped_ts.perils) == 4
    logs_data = json.loads(logs_file.read_text(encoding="utf-8"))
    assert isinstance(logs_data, list)
    assert len(logs_data) == 4

    # 6. Validated termsheet
    val_file = tmp_path / "validated_termsheet.json"
    assert val_file.exists()
    val_ts = ValidatedTermsheet.model_validate_json(val_file.read_text(encoding="utf-8"))
    assert val_ts.review_required is False
    assert len(val_ts.flags) == 0


def test_pipeline_missing_pdf_raises_error(tmp_path: Path):
    """Pipeline raises FileNotFoundError when source PDF does not exist."""
    with pytest.raises(FileNotFoundError, match="Source PDF file not found"):
        run_pipeline(
            pdf_path="non_existent_file.pdf",
            intermediates_dir=tmp_path,
            quiet=True,
        )


def test_pipeline_idempotency_structure(orange_pdf_path: Path, tmp_path: Path):
    """Running pipeline produces deterministic structural results."""
    run1_dir = tmp_path / "run1"
    run2_dir = tmp_path / "run2"

    res1 = run_pipeline(pdf_path=orange_pdf_path, intermediates_dir=run1_dir, quiet=True)
    res2 = run_pipeline(pdf_path=orange_pdf_path, intermediates_dir=run2_dir, quiet=True)

    # Core business values must match exactly
    assert res1.review_required == res2.review_required == False
    assert len(res1.flags) == len(res2.flags) == 0

    ts1 = res1.termsheet
    ts2 = res2.termsheet

    assert ts1.document.crop.value == ts2.document.crop.value
    assert ts1.document.district.value == ts2.document.district.value
    assert ts1.document.state.value == ts2.document.state.value
    assert ts1.document.premium.total_sum_insured.value == ts2.document.premium.total_sum_insured.value

    assert len(ts1.perils) == len(ts2.perils)
    for p1, p2 in zip(ts1.perils, ts2.perils):
        assert p1.peril_id == p2.peril_id
        assert p1.archetype == p2.archetype
