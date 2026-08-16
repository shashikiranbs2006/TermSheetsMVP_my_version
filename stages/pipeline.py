"""
stages/pipeline.py — End-to-end WBCIS Termsheet Extraction Pipeline.

Sequentially orchestrates all 6 stages:
1. Ingest & Route       (stages.ingest_router)
2. Extract to Cells     (stages.cell_extractor)
3. Segment & Classify   (stages.segmenter)
4. Reconstruct          (stages.reconstructor)
5. Schema Mapping       (stages.mapper)
6. Validate & Audit     (stages.validator)
7. Underwriter Report   (stages.review_report)

All intermediate artifacts are persisted to disk to maintain step-by-step
checkpointing and reproducibility.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from models.validated_termsheet import ValidatedTermsheet
from stages import (
    cell_extractor,
    ingest_router,
    mapper,
    reconstructor,
    review_report,
    segmenter,
    validator,
)


def run_pipeline(
    pdf_path: str | Path,
    intermediates_dir: str | Path = "data/intermediates",
    *,
    quiet: bool = False,
) -> ValidatedTermsheet:
    """
    Execute the full WBCIS Termsheet extraction and validation pipeline.

    Args:
        pdf_path: Path to the source Annexure 3 PDF.
        intermediates_dir: Directory where intermediate JSON artifacts are saved.
        quiet: If True, suppress console logging during stage execution.

    Returns:
        ValidatedTermsheet: The final validated termsheet model.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Source PDF file not found: {pdf_path}")

    int_dir = Path(intermediates_dir)
    int_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = int_dir / "page_manifest.json"
    raw_cells_path = int_dir / "raw_cells.json"
    segmented_path = int_dir / "segmented_perils.json"
    reconstructed_path = int_dir / "reconstructed_perils.json"
    mapped_path = int_dir / "mapped_termsheet.json"
    agent_logs_path = int_dir / "mapping_agent_logs.json"
    validated_path = int_dir / "validated_termsheet.json"

    start_time = time.perf_counter()
    if not quiet:
        print("=" * 70)
        print(f"Starting WBCIS Termsheet Pipeline for: {pdf_path.name}")
        print(f"Intermediates directory: {int_dir}")
        print("=" * 70)

    # --- Stage 1: Ingest & Route ---
    t0 = time.perf_counter()
    if not quiet:
        print("\n[Stage 1/6] Ingest & Route...")
    manifests = ingest_router.run(pdf_path, output_path=manifest_path, quiet=quiet)
    if not quiet:
        print(f"Stage 1 completed in {time.perf_counter() - t0:.2f}s")

    # --- Stage 2: Extract to Cells ---
    t0 = time.perf_counter()
    if not quiet:
        print("\n[Stage 2/6] Extract Table Cells...")
    raw_cells = cell_extractor.run(
        pdf_path, manifests, output_path=raw_cells_path, quiet=quiet
    )
    if not quiet:
        print(f"Stage 2 completed in {time.perf_counter() - t0:.2f}s")

    # --- Stage 3: Segment & Classify ---
    t0 = time.perf_counter()
    if not quiet:
        print("\n[Stage 3/6] Segment Perils & Classify Archetypes...")
    segmented = segmenter.run(raw_cells, output_path=segmented_path, quiet=quiet)
    if not quiet:
        print(f"Stage 3 completed in {time.perf_counter() - t0:.2f}s")

    # --- Stage 4A: Deterministic Reconstruction ---
    t0 = time.perf_counter()
    if not quiet:
        print("\n[Stage 4A/6] Deterministic Geometry Reconstruction...")
    reconstructed = reconstructor.run(
        segmented, output_path=reconstructed_path, quiet=quiet
    )
    if not quiet:
        print(f"Stage 4A completed in {time.perf_counter() - t0:.2f}s")

    # --- Stage 4B: Schema Mapping (Strands + Bedrock) ---
    t0 = time.perf_counter()
    if not quiet:
        print("\n[Stage 4B/6] Agent Schema Mapping (Strands + Bedrock)...")
    mapped_termsheet = mapper.run(
        reconstructed_path=reconstructed_path,
        output_path=mapped_path,
        logs_path=agent_logs_path,
        quiet=quiet,
    )
    if not quiet:
        print(f"Stage 4B completed in {time.perf_counter() - t0:.2f}s")

    # --- Stage 5: Rule Validation ---
    t0 = time.perf_counter()
    if not quiet:
        print("\n[Stage 5/6] Rule Engine Validation...")
    validated = validator.run(
        input_path=mapped_path,
        output_path=validated_path,
    )
    if not quiet:
        print(f"Stage 5 completed in {time.perf_counter() - t0:.2f}s")

    # --- Stage 6: Human Review & Provenance Report ---
    t0 = time.perf_counter()
    report_path = int_dir / "review_report.md"
    if not quiet:
        print("\n[Stage 6/6] Generating Human Review & Provenance Report...")
    _ = review_report.run(
        validated_termsheet_path=validated_path,
        output_path=report_path,
    )
    if not quiet:
        print(f"Stage 6 completed in {time.perf_counter() - t0:.2f}s")

    elapsed = time.perf_counter() - start_time
    if not quiet:
        print("\n" + "=" * 70)
        print(f"Pipeline completed successfully in {elapsed:.2f}s")
        print(f"Final Artifact: {validated_path}")
        print(f"Review Report : {report_path}")
        print(f"Review Required: {validated.review_required}")
        print(f"Validation Flags: {len(validated.flags)}")
        print("=" * 70)

    return validated
