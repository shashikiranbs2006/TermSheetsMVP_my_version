"""
stages/segmenter.py — Stage 3: Segment & Classify

Takes RawCells from Stage 2 and slices them into discrete peril sections
based on section header text markers and vertical (y-coordinate) boundaries.
Classifies each section with its peril archetype.
Emits SegmentedPerils conforming to models/segmented_peril.py.

Deterministic spine:
  - Section headers in WBCIS termsheets are literal text markers:
      * "1. HIGH TEMPERATURE"      -> archetype: temperature_phased
      * "2. DEFICIT RAINFALL"       -> archetype: rainfall_multistrike
      * "2 B: UNSEASONAL RAINFALL"  -> archetype: rainfall_single_payout
      * "3. HIGH WIND SPEED"        -> archetype: wind_phased
  - Classification is a direct deterministic regex lookup on the header text.
  - Cell assignment uses (page_no, y) ranges between consecutive section headers.

Cell accounting:
  - Document-level header cells (before the first peril header, e.g. State, Crop, RWS)
    and footer cells (from "Premium Description" downward) belong to document-level metadata,
    not any peril section.
  - Peril sections receive all table and word cells strictly within their vertical bounds.
  - 100% of input cells are accounted for (sum of perils + header + footer == total input cells).

Boundary Constraint:
  - This stage identifies WHICH cells belong to WHICH peril and WHAT archetype it is.
  - It does NOT extract numeric values into schema fields (that belongs to Stage 4).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Sequence

from models.raw_cells import RawCell, RawCells
from models.segmented_peril import SegmentedPeril, SegmentedPerils

# ---------------------------------------------------------------------------
# Constants & Header Matchers
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_PATH = Path("data/intermediates/segmented_perils.json")

HEADER_PATTERNS = [
    ("high_temperature", "temperature_phased", re.compile(r"\bHIGH\s+TEMPERATURE\b", re.IGNORECASE)),
    ("deficit_rainfall", "rainfall_multistrike", re.compile(r"\b(DEFICIT|DEFICEIT)\s+RAINFALL\b", re.IGNORECASE)),
    ("unseasonal_rainfall", "rainfall_single_payout", re.compile(r"\b(UNSEASONAL|UNSEASIONAL)\s+RAINFALL\b", re.IGNORECASE)),
    ("high_wind_speed", "wind_phased", re.compile(r"\b(HIGH\s+WIND\s+SPEED|HIGH\s+WIND)\b", re.IGNORECASE)),
]

FOOTER_PATTERN = re.compile(r"\b(PREMIUM\s+DESCRIPTION|TOTAL\s+SUM\s+INSURED)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Segmentation Core
# ---------------------------------------------------------------------------


def segment_with_accounting(
    raw_cells: RawCells,
) -> tuple[SegmentedPerils, list[RawCell], list[RawCell]]:
    """
    Segment RawCells into discrete perils while tracking non-peril cells
    (document header and footer).

    Args:
        raw_cells: RawCells container from Stage 2.

    Returns:
        tuple of (SegmentedPerils, header_cells, footer_cells).
        - SegmentedPerils: List of SegmentedPeril objects with assigned archetype and raw_cells.
        - header_cells: Cells preceding the first peril (Document metadata).
        - footer_cells: Cells following the last peril (Premium block).
    """
    cells = raw_cells.cells
    if not cells:
        return SegmentedPerils(perils=[]), [], []

    # Assign effective position (page_no, y) to preserve table row order
    # for merged cells with (0,0) geometry.
    effective_positions: list[tuple[int, float]] = []
    last_pno = 1
    last_y = 0.0
    for c in cells:
        if c.page_no > 0:
            last_pno = c.page_no
        if c.y > 0.0:
            last_y = c.y
        effective_positions.append((last_pno, last_y))

    # Cluster non-empty text cells by vertical position on each page
    text_items = []
    for idx, (c, (pno, y)) in enumerate(zip(cells, effective_positions)):
        if c.text and c.text.strip():
            text_items.append((pno, y, c.x, c.text.strip(), idx))

    sorted_text = sorted(text_items, key=lambda item: (item[0], item[1], item[2]))

    lines: list[tuple[int, float, str]] = []
    curr_line: list[tuple[int, float, float, str, int]] = []
    curr_pno: int | None = None
    curr_y: float | None = None

    for item in sorted_text:
        pno, y, x, text, idx = item
        if curr_pno != pno or (curr_y is not None and abs(y - curr_y) > 4.0):
            if curr_line:
                line_str = " ".join(t[3] for t in curr_line)
                min_y = min(t[1] for t in curr_line)
                lines.append((curr_pno, min_y, line_str))
            curr_line = [item]
            curr_pno = pno
            curr_y = y
        else:
            curr_line.append(item)
            curr_y = min(curr_y, y) if curr_y is not None else y

    if curr_line and curr_pno is not None:
        line_str = " ".join(t[3] for t in curr_line)
        min_y = min(t[1] for t in curr_line)
        lines.append((curr_pno, min_y, line_str))

    # Detect section boundaries
    detected_headers: list[tuple[str, str, int, float]] = []
    footer_pos: tuple[int, float] | None = None

    for pno, y, line_text in lines:
        for peril_id, arch, pattern in HEADER_PATTERNS:
            if pattern.search(line_text):
                # Avoid duplicate triggers for the same peril (e.g. secondary mention in objective)
                if not any(h[0] == peril_id for h in detected_headers):
                    detected_headers.append((peril_id, arch, pno, y))
                break
        if FOOTER_PATTERN.search(line_text) and footer_pos is None:
            footer_pos = (pno, y)

    # Sort detected headers by document position (page_no, y)
    detected_headers.sort(key=lambda h: (h[2], h[3]))

    # Partition cells into header, perils, and footer
    peril_buckets: list[list[RawCell]] = [[] for _ in detected_headers]
    header_cells: list[RawCell] = []
    footer_cells: list[RawCell] = []

    for idx, (c, (pno, y)) in enumerate(zip(cells, effective_positions)):
        pos = (pno, y)
        if not detected_headers or pos < (detected_headers[0][2], detected_headers[0][3]):
            header_cells.append(c)
        elif footer_pos and pos >= footer_pos:
            footer_cells.append(c)
        else:
            assigned = False
            for i in range(len(detected_headers)):
                start_pos = (detected_headers[i][2], detected_headers[i][3])
                next_pos = (
                    (detected_headers[i + 1][2], detected_headers[i + 1][3])
                    if i + 1 < len(detected_headers)
                    else (footer_pos or (9999, 9999.0))
                )
                if start_pos <= pos < next_pos:
                    peril_buckets[i].append(c)
                    assigned = True
                    break
            if not assigned:
                footer_cells.append(c)

    peril_objects: list[SegmentedPeril] = []
    for (peril_id, arch, _, _), bcells in zip(detected_headers, peril_buckets):
        peril_objects.append(
            SegmentedPeril(
                peril_id=peril_id,
                raw_cells=bcells,
                archetype=arch,  # type: ignore[arg-type]
            )
        )

    return SegmentedPerils(perils=peril_objects), header_cells, footer_cells


def segment(raw_cells: RawCells) -> SegmentedPerils:
    """
    Main entry point for Stage 3: takes RawCells, returns SegmentedPerils.
    """
    segmented, _, _ = segment_with_accounting(raw_cells)
    return segmented


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist(
    segmented_perils: SegmentedPerils,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """
    Write SegmentedPerils to JSON for Stage 4 consumption.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        segmented_perils.model_dump_json(indent=2), encoding="utf-8"
    )
    return output_path


# ---------------------------------------------------------------------------
# Convenience Run Function
# ---------------------------------------------------------------------------


def run(
    raw_cells_source: str | Path | RawCells,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    quiet: bool = False,
) -> SegmentedPerils:
    """
    Load raw cells, segment into perils, persist output, and return SegmentedPerils.
    """
    if isinstance(raw_cells_source, (str, Path)):
        source_path = Path(raw_cells_source)
        if not source_path.exists():
            raise FileNotFoundError(f"Raw cells file not found: {source_path}")
        raw_dict = json.loads(source_path.read_text(encoding="utf-8"))
        raw_cells = RawCells.model_validate(raw_dict)
    else:
        raw_cells = raw_cells_source

    segmented, header_cells, footer_cells = segment_with_accounting(raw_cells)
    out = persist(segmented, output_path)

    if not quiet:
        total_in = len(raw_cells.cells)
        peril_cell_sum = sum(len(p.raw_cells) for p in segmented.perils)
        print(f"Segmented {len(segmented.perils)} perils from {total_in} cells:")
        for p in segmented.perils:
            print(f"  - {p.peril_id:20s} ({p.archetype:25s}): {len(p.raw_cells):>3} cells")
        print(f"  - Document Header   : {len(header_cells):>3} cells")
        print(f"  - Premium Footer    : {len(footer_cells):>3} cells")
        print(f"  - Accounting Check  : {peril_cell_sum + len(header_cells) + len(footer_cells)} / {total_in} cells accounted for.")
        print(f"Persisted -> {out}")

    return segmented


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "data/intermediates/raw_cells.json"
    dest = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_OUTPUT_PATH)
    run(src, dest)
