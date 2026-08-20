"""
stages/reconstructor.py — Stage 4A: Reconstruct Tables (deterministic only)

Reconstructs the hierarchical structure of tables (phases -> sub-periods -> values)
from SegmentedPeril cells using 2D x/y spatial clustering.

Deterministic spine:
  - No LLM, no Bedrock, no Strands here.
  - Slices rows by y-coordinate clustering and columns by x-coordinate clustering.
  - Multi-level headers (e.g. Phase I -> sub-period columns) are detected by
    comparing header cell width/span against sub-period column boundaries.
  - Merged values spanning multiple sub-period columns (e.g. '60 80' across 2 sub-periods)
    are partitioned into their corresponding child sub-periods based on column geometry.
  - Preserves raw values, periods, and numeric parameters without premature schema normalization.

Supports all 4 archetypes:
  1. rainfall_multistrike  -> Phases with nested sub-periods, strikes, rates, and payouts.
  2. temperature_phased    -> Sequential N phases (I..VI) with triggers and common strike/exit/rate.
  3. wind_phased           -> N trigger blocks, each containing phases + common parameters.
  4. rainfall_single_payout-> Flat cover parameter table (single payout, no phase hierarchy).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Sequence

from models.raw_cells import RawCell
from models.segmented_peril import SegmentedPeril, SegmentedPerils

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_PATH = Path("data/intermediates/reconstructed_perils.json")
DEFAULT_Y_TOLERANCE = 3.0
DEFAULT_X_TOLERANCE = 4.0


# ---------------------------------------------------------------------------
# Geometric Clustering Utilities
# ---------------------------------------------------------------------------


def cluster_rows(
    cells: Sequence[RawCell],
    y_tolerance: float = DEFAULT_Y_TOLERANCE,
) -> list[list[RawCell]]:
    """
    Cluster cells into horizontal rows based on y-coordinate proximity.
    Cells in each row are sorted from left to right (x-coordinate).
    """
    valid_cells = [c for c in cells if c.width > 0 and c.height > 0]
    sorted_cells = sorted(valid_cells, key=lambda c: (c.y, c.x))

    rows: list[list[RawCell]] = []
    curr_row: list[RawCell] = []
    curr_y: float | None = None

    for c in sorted_cells:
        if curr_y is None or abs(c.y - curr_y) > y_tolerance:
            if curr_row:
                rows.append(sorted(curr_row, key=lambda cell: cell.x))
            curr_row = [c]
            curr_y = c.y
        else:
            curr_row.append(c)

    if curr_row:
        rows.append(sorted(curr_row, key=lambda cell: cell.x))

    return rows


def match_cell_to_columns(
    cell: RawCell,
    column_bounds: list[tuple[float, float]],
    x_tolerance: float = DEFAULT_X_TOLERANCE,
) -> list[int]:
    """
    Determine which column index (or indices for merged cells) a cell covers.

    Args:
        cell: The RawCell to test.
        column_bounds: List of (x_start, x_end) for each defined column.
        x_tolerance: Overlap tolerance in points.

    Returns:
        List of 0-based column indices that the cell overlaps significantly.
    """
    cx0 = cell.x
    cx1 = cell.x + cell.width

    matched: list[int] = []
    for idx, (col_x0, col_x1) in enumerate(column_bounds):
        # Calculate overlap
        overlap_x0 = max(cx0, col_x0)
        overlap_x1 = min(cx1, col_x1)
        overlap = overlap_x1 - overlap_x0
        col_width = col_x1 - col_x0

        if overlap > (col_width * 0.40) or overlap > (cell.width * 0.40) or (abs(cx0 - col_x0) <= x_tolerance and abs(cx1 - col_x1) <= x_tolerance):
            matched.append(idx)

    # Fallback: if no direct overlap passed threshold, pick closest column by center point
    if not matched:
        c_center = (cx0 + cx1) / 2.0
        best_idx = 0
        min_dist = float("inf")
        for idx, (col_x0, col_x1) in enumerate(column_bounds):
            col_center = (col_x0 + col_x1) / 2.0
            dist = abs(c_center - col_center)
            if dist < min_dist:
                min_dist = dist
                best_idx = idx
        matched = [best_idx]

    return matched


# ---------------------------------------------------------------------------
# Archetype B: rainfall_multistrike Reconstruction
MONTH_REGEX = r"\b(Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|Sept|September|Oct|October|Nov|November|Dec|December)\b"


# ---------------------------------------------------------------------------
# Archetype B: rainfall_multistrike Reconstruction
# ---------------------------------------------------------------------------


def reconstruct_multistrike(peril: SegmentedPeril) -> dict[str, Any]:
    """
    Reconstruct rainfall_multistrike hierarchy:
      Phases (Phase I, Phase II) -> Sub-periods -> Parameters (Strike 1/2, Exit, Rate 1/2, Max Payout)
      + Total Payout.
    """
    table_cells = [c for c in peril.raw_cells if c.width > 0 and c.width < 500 and c.height > 0]
    rows = cluster_rows(table_cells)

    if not rows:
        return {"peril_id": peril.peril_id, "archetype": peril.archetype, "phases": []}

    # Find the sub-period header row:
    sub_period_row_idx = -1
    for ri, row in enumerate(rows):
        row_cells = [c for c in row if c.text and c.text.strip()]
        if any("COVER" in (c.text or "").upper() for c in row_cells):
            continue
        if any("EVENT" in (c.text or "").upper() and "DEFINITION" in (c.text or "").upper() for c in row_cells):
            continue
        date_cols = [
            c for c in row_cells
            if re.search(MONTH_REGEX, c.text, re.I)
            and c.text.strip().upper() not in ["PERIOD", "RAINFALL", "RAINFALL\nVOLUME", "INDEX"]
        ]
        if len(date_cols) >= 3:
            sub_period_row_idx = ri
            break

    if sub_period_row_idx == -1:
        for ri, row in enumerate(rows):
            row_cells = [c for c in row if c.text and c.text.strip()]
            if any("COVER" in (c.text or "").upper() for c in row_cells):
                continue
            if any("EVENT" in (c.text or "").upper() for c in row_cells):
                continue
            date_cols = [
                c for c in row_cells
                if re.search(MONTH_REGEX, c.text, re.I)
                and c.text.strip().upper() not in ["PERIOD", "RAINFALL", "RAINFALL\nVOLUME", "INDEX"]
            ]
            if len(date_cols) >= 1:
                sub_period_row_idx = ri
                break

    if sub_period_row_idx == -1:
        sub_period_row_idx = min(1, len(rows) - 1)

    # Sub-period columns: cells matching date interval patterns
    row_cells = [c for c in rows[sub_period_row_idx] if c.text and c.text.strip()]
    date_cells = [
        c for c in row_cells
        if re.search(MONTH_REGEX, c.text, re.I)
        and c.text.strip().upper() not in ["PERIOD", "RAINFALL", "RAINFALL\nVOLUME", "INDEX"]
    ]
    sub_period_cells = date_cells if date_cells else row_cells
    column_bounds = [(c.x, c.x + c.width) for c in sub_period_cells]

    # Find Phase headers row (the row directly above sub-periods, e.g. "Phase I", "Phase II")
    phase_headers_row = rows[sub_period_row_idx - 1] if sub_period_row_idx > 0 else []
    phase_header_cells = [c for c in phase_headers_row if c.text and "PHASE" in c.text.upper()]

    phase_groups: list[dict[str, Any]] = []
    if phase_header_cells:
        for ph in phase_header_cells:
            ph_x0 = ph.x
            ph_x1 = ph.x + ph.width
            child_sub_periods: list[dict[str, Any]] = []
            for col_idx, (col_x0, col_x1) in enumerate(column_bounds):
                col_mid = (col_x0 + col_x1) / 2.0
                if ph_x0 - 5.0 <= col_mid <= ph_x1 + 55.0:
                    already_assigned = any(
                        any(sp["col_idx"] == col_idx for sp in pg["sub_periods"])
                        for pg in phase_groups
                    )
                    if not already_assigned:
                        child_sub_periods.append({
                            "col_idx": col_idx,
                            "period_raw": sub_period_cells[col_idx].text.strip(),
                            "x_range": [col_x0, col_x1],
                            "values": {},
                        })

            phase_groups.append({
                "label": ph.text.strip(),
                "x_range": [ph_x0, ph_x1],
                "sub_periods": child_sub_periods,
            })
    else:
        phase_groups.append({
            "label": "Phase I",
            "x_range": [column_bounds[0][0], column_bounds[-1][1]],
            "sub_periods": [
                {
                    "col_idx": i,
                    "period_raw": c.text.strip() if c.text else "",
                    "x_range": list(column_bounds[i]),
                    "values": {},
                }
                for i, c in enumerate(sub_period_cells)
            ],
        })

    all_assigned_cols = {sp["col_idx"] for pg in phase_groups for sp in pg["sub_periods"]}
    for col_idx in range(len(column_bounds)):
        if col_idx not in all_assigned_cols:
            col_x0, col_x1 = column_bounds[col_idx]
            target_phase = phase_groups[-1]
            target_phase["sub_periods"].append({
                "col_idx": col_idx,
                "period_raw": sub_period_cells[col_idx].text.strip() if sub_period_cells[col_idx].text else "",
                "x_range": [col_x0, col_x1],
                "values": {},
            })

    for pg in phase_groups:
        pg["sub_periods"].sort(key=lambda sp: sp["col_idx"])

    total_payout_raw: str | None = None
    for ri in range(sub_period_row_idx + 1, len(rows)):
        row = rows[ri]
        row_text_cells = [c for c in row if c.text and c.text.strip()]
        if not row_text_cells:
            continue

        label_cell = row_text_cells[0]
        label_text = label_cell.text.strip()
        val_cells = row_text_cells[1:]

        if "PAYOUT" in label_text.upper() and ("I & II" in label_text.upper() or "TOTAL" in label_text.upper()):
            if val_cells:
                total_payout_raw = val_cells[0].text.strip()
            break

        for vc in val_cells:
            text_val = vc.text.strip()
            matched_cols = match_cell_to_columns(vc, column_bounds)
            tokens = text_val.split()
            if len(matched_cols) > 1 and len(tokens) == len(matched_cols):
                for col_idx, token in zip(matched_cols, tokens):
                    _set_subperiod_value(phase_groups, col_idx, label_text, token)
            elif len(matched_cols) == 1:
                _set_subperiod_value(phase_groups, matched_cols[0], label_text, text_val)
            else:
                for col_idx in matched_cols:
                    _set_subperiod_value(phase_groups, col_idx, label_text, text_val)

    return {
        "peril_id": peril.peril_id,
        "archetype": peril.archetype,
        "phases": phase_groups,
        "total_payout_raw": total_payout_raw,
    }


def _set_subperiod_value(
    phase_groups: list[dict[str, Any]],
    col_idx: int,
    label: str,
    val: str,
) -> None:
    """Helper to set a named row value on the correct sub-period by column index."""
    for pg in phase_groups:
        for sp in pg["sub_periods"]:
            if sp["col_idx"] == col_idx:
                sp["values"][label] = val
                return


# ---------------------------------------------------------------------------
# Archetype A: temperature_phased Reconstruction
# ---------------------------------------------------------------------------


def reconstruct_temperature(peril: SegmentedPeril) -> dict[str, Any]:
    """
    Reconstruct temperature_phased hierarchy:
      Phases (I..VI or 1..4) with period and trigger + common strike, exit, payout_rate, max_payout.
    """
    table_cells = [c for c in peril.raw_cells if c.width > 0 and c.width < 500 and c.height > 0]
    rows = cluster_rows(table_cells)

    if not rows:
        return {"peril_id": peril.peril_id, "archetype": peril.archetype, "phases": []}

    # Locate the phase row (the row containing "PHASE" as a column header)
    phase_row_idx = -1
    for ri, row in enumerate(rows):
        for c in row:
            if c.text and c.text.strip().upper() == "PHASE":
                phase_row_idx = ri
                break
        if phase_row_idx != -1:
            break

    if phase_row_idx == -1:
        return {"peril_id": peril.peril_id, "archetype": peril.archetype, "phases": []}

    phase_row = rows[phase_row_idx]
    phase_cells = [c for c in phase_row if c.text and c.text.strip().upper() not in ["PHASE"]]

    if not phase_cells:
        return {"peril_id": peril.peril_id, "archetype": peril.archetype, "phases": []}

    column_bounds = [(c.x, c.x + c.width) for c in phase_cells]

    # Find Trigger row (explicitly find row with TRIGGER in label)
    trigger_row_idx = -1
    for ri in range(phase_row_idx + 1, len(rows)):
        for c in rows[ri]:
            if c.text and "TRIGGER" in c.text.upper():
                trigger_row_idx = ri
                break
        if trigger_row_idx != -1:
            break

    if trigger_row_idx == -1:
        trigger_row_idx = phase_row_idx + 2 if phase_row_idx + 2 < len(rows) else phase_row_idx + 1

    trigger_row = rows[trigger_row_idx] if trigger_row_idx < len(rows) else []
    trigger_cells = [c for c in trigger_row if c.text and "TRIGGER" not in c.text.strip().upper()]

    # Period row is between phase_row and trigger_row
    period_texts = ["" for _ in phase_cells]
    for ri in range(phase_row_idx + 1, trigger_row_idx):
        for c in rows[ri]:
            if not c.text or c.text.strip().upper() == "PERIOD":
                continue
            matched_cols = match_cell_to_columns(c, column_bounds)
            for col_idx in matched_cols:
                ct = c.text.strip()
                if not period_texts[col_idx]:
                    period_texts[col_idx] = ct
                elif ct not in period_texts[col_idx] and period_texts[col_idx] not in ct:
                    period_texts[col_idx] += "\n" + ct
                elif len(ct) > len(period_texts[col_idx]):
                    period_texts[col_idx] = ct

    phases: list[dict[str, Any]] = []
    for idx, ph_cell in enumerate(phase_cells):
        period_str = period_texts[idx]
        matched_trigger = ""
        for tc in trigger_cells:
            cols = match_cell_to_columns(tc, column_bounds)
            if idx in cols:
                matched_trigger = tc.text.strip()
                break
        if not matched_trigger and idx < len(trigger_cells):
            matched_trigger = trigger_cells[idx].text.strip()

        phases.append({
            "label": ph_cell.text.strip(),
            "period_raw": period_str,
            "trigger_raw": matched_trigger,
            "x_range": list(column_bounds[idx]),
        })

    # Remaining rows: Strike, Exit, Payout Rate, Max Payout spanning all phases
    common_params: dict[str, str] = {}
    for ri in range(trigger_row_idx + 1, len(rows)):
        row = rows[ri]
        row_texts = [c for c in row if c.text and c.text.strip()]
        if len(row_texts) >= 2:
            label = row_texts[0].text.strip()
            val = row_texts[1].text.strip()
            common_params[label] = val

    return {
        "peril_id": peril.peril_id,
        "archetype": peril.archetype,
        "phases": phases,
        "parameters": common_params,
    }


# ---------------------------------------------------------------------------
# Archetype D: wind_phased Reconstruction
# ---------------------------------------------------------------------------


def reconstruct_wind(peril: SegmentedPeril) -> dict[str, Any]:
    """
    Reconstruct wind_phased hierarchy:
      Dynamically discovers 1..N trigger blocks (e.g. 2 blocks of 3 phases for Orange,
      or 1 block of 4 phases for Guava) with shared/per-block parameters.
    """
    # Filter out full-width container/blob cells and 0-dimension cells
    table_cells = [c for c in peril.raw_cells if c.width > 0 and c.width < 500 and c.height > 0]
    rows = cluster_rows(table_cells)

    if not rows:
        return {"peril_id": peril.peril_id, "archetype": peril.archetype, "trigger_blocks": []}

    # Locate the phase row (the row containing "PHASE" as a column header)
    phase_row_idx = -1
    for ri, row in enumerate(rows):
        for c in row:
            if c.text and c.text.strip().upper() == "PHASE":
                phase_row_idx = ri
                break
        if phase_row_idx != -1:
            break

    if phase_row_idx == -1:
        return {"peril_id": peril.peril_id, "archetype": peril.archetype, "trigger_blocks": []}

    phase_row = rows[phase_row_idx]
    phase_cells = [c for c in phase_row if c.text and c.text.strip().upper() not in ["PHASE"]]

    if not phase_cells:
        return {"peril_id": peril.peril_id, "archetype": peril.archetype, "trigger_blocks": []}

    column_bounds = [(c.x, c.x + c.width) for c in phase_cells]

    # Find Period row (row directly below Phase, or next row containing dates/period)
    period_row = rows[phase_row_idx + 1] if phase_row_idx + 1 < len(rows) else []
    period_cells = [c for c in period_row if c.text and c.text.strip().upper() not in ["PERIOD"]]

    # Find Trigger row (row directly below Period)
    trigger_row = rows[phase_row_idx + 2] if phase_row_idx + 2 < len(rows) else []
    trigger_cells = [c for c in trigger_row if c.text and "TRIGGER" not in c.text.strip().upper()]

    # Determine blocks dynamically based on phase labels sequence
    # E.g. ['I', 'II', 'III', 'I', 'II', 'III'] -> 2 blocks of 3
    # E.g. ['I', 'II', 'III', 'IV'] -> 1 block of 4
    # E.g. ['1.', '2.', '3.'] -> 1 block of 3
    block_indices: list[int] = []
    current_block = 0
    seen_labels_in_block = set()

    for c in phase_cells:
        label = c.text.strip().upper()
        if label in seen_labels_in_block and len(seen_labels_in_block) > 0:
            current_block += 1
            seen_labels_in_block = {label}
        else:
            seen_labels_in_block.add(label)
        block_indices.append(current_block)

    num_blocks = current_block + 1
    blocks: list[dict[str, Any]] = [
        {"block_label": f"block_{b + 1}", "phases": [], "parameters": {}}
        for b in range(num_blocks)
    ]

    for idx, ph_cell in enumerate(phase_cells):
        b_idx = block_indices[idx]
        period_str = period_cells[idx].text.strip() if idx < len(period_cells) and period_cells[idx].text else ""
        trigger_str = trigger_cells[idx].text.strip() if idx < len(trigger_cells) and trigger_cells[idx].text else ""

        blocks[b_idx]["phases"].append({
            "label": ph_cell.text.strip(),
            "period_raw": period_str,
            "trigger_raw": trigger_str,
            "x_range": list(column_bounds[idx]),
        })

    # Parameter rows (Strike, Exit, Payout, Max Payout)
    # If num_blocks == 2 and row has 2 value cells -> 1 per block
    # If row has 1 value cell -> shared across all blocks
    for ri in range(phase_row_idx + 3, len(rows)):
        row = rows[ri]
        row_texts = [c for c in row if c.text and c.text.strip()]
        if not row_texts:
            continue
        label = row_texts[0].text.strip()
        val_cells = row_texts[1:]
        if len(val_cells) >= num_blocks:
            for b in range(num_blocks):
                blocks[b]["parameters"][label] = val_cells[b].text.strip()
        elif len(val_cells) == 1:
            val = val_cells[0].text.strip()
            for b in range(num_blocks):
                blocks[b]["parameters"][label] = val

    return {
        "peril_id": peril.peril_id,
        "archetype": peril.archetype,
        "trigger_blocks": blocks,
    }


# ---------------------------------------------------------------------------
# Archetype C: rainfall_single_payout Reconstruction
# ---------------------------------------------------------------------------


def reconstruct_single_payout(peril: SegmentedPeril) -> dict[str, Any]:
    """
    Reconstruct rainfall_single_payout structure:
      Flat parameter table (Strike 1/2, Exit, Rate 1/2, Max Payout) + Cover Period.
    """
    table_cells = [c for c in peril.raw_cells if c.width > 0 and c.width < 500 and c.height > 0]
    rows = cluster_rows(table_cells)

    parameters: dict[str, str] = {}
    periods: list[str] = []

    # Look for period date strings
    for c in peril.raw_cells:
        if c.text and re.search(MONTH_REGEX, c.text, re.I):
            if re.search(r"\b\d{1,2}\s*[-.]\s*[a-zA-Z]+|\b\d{1,2}\s+[a-zA-Z]+\b", c.text, re.I):
                ct = c.text.strip()
                if ct not in periods and "COVER" not in ct.upper():
                    periods.append(ct)

    for row in rows:
        row_texts = [c for c in row if c.text and c.text.strip()]
        if len(row_texts) >= 2:
            label = row_texts[0].text.strip()
            val = row_texts[1].text.strip()
            parameters[label] = val

    return {
        "peril_id": peril.peril_id,
        "archetype": peril.archetype,
        "parameters": parameters,
        "periods_raw": periods,
    }


# ---------------------------------------------------------------------------
# Main Reconstruct Dispatcher
# ---------------------------------------------------------------------------


def reconstruct_peril(peril: SegmentedPeril) -> dict[str, Any]:
    """
    Dispatch reconstruction based on peril archetype.
    """
    if peril.archetype == "rainfall_multistrike":
        return reconstruct_multistrike(peril)
    elif peril.archetype == "temperature_phased":
        return reconstruct_temperature(peril)
    elif peril.archetype == "wind_phased":
        return reconstruct_wind(peril)
    elif peril.archetype == "rainfall_single_payout":
        return reconstruct_single_payout(peril)
    elif peril.archetype in (None, "unknown"):
        return {
            "peril_id": peril.peril_id,
            "archetype": "unknown",
            "status": "unrecognized_peril",
            "raw_cells_count": len(peril.raw_cells),
        }
    else:
        raise ValueError(f"Unknown archetype: {peril.archetype}")


def reconstruct_all(segmented_perils: SegmentedPerils) -> dict[str, Any]:
    """
    Reconstruct all perils in a SegmentedPerils collection.
    Skips unrecognized perils so downstream mapper receives only valid archetypes.
    """
    return {
        "reconstructed_perils": [
            reconstruct_peril(p)
            for p in segmented_perils.perils
            if p.archetype and p.archetype != "unknown"
        ]
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist(
    reconstructed_data: dict[str, Any],
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """
    Write reconstructed perils hierarchy to JSON.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(reconstructed_data, indent=2), encoding="utf-8"
    )
    return output_path


# ---------------------------------------------------------------------------
# Convenience Run Function
# ---------------------------------------------------------------------------


def run(
    segmented_source: str | Path | SegmentedPerils = "data/intermediates/segmented_perils.json",
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    quiet: bool = False,
) -> dict[str, Any]:
    """
    Load segmented perils, reconstruct table hierarchies, persist output, and return dict.
    """
    if isinstance(segmented_source, (str, Path)):
        source_path = Path(segmented_source)
        if not source_path.exists():
            raise FileNotFoundError(f"Segmented perils file not found: {source_path}")
        data_dict = json.loads(source_path.read_text(encoding="utf-8"))
        segmented_perils = SegmentedPerils.model_validate(data_dict)
    else:
        segmented_perils = segmented_source

    reconstructed = reconstruct_all(segmented_perils)
    out = persist(reconstructed, output_path)

    if not quiet:
        perils_list = reconstructed["reconstructed_perils"]
        print(f"Reconstructed {len(perils_list)} perils deterministically:")
        for p in perils_list:
            pid = p["peril_id"]
            arch = p["archetype"]
            if arch == "rainfall_multistrike":
                sp_count = sum(len(ph["sub_periods"]) for ph in p["phases"])
                print(f"  - {pid:20s} ({arch:25s}): {len(p['phases'])} phases, {sp_count} sub-periods, total={p['total_payout_raw']}")
            elif arch == "temperature_phased":
                print(f"  - {pid:20s} ({arch:25s}): {len(p['phases'])} phases")
            elif arch == "wind_phased":
                tb_count = len(p["trigger_blocks"])
                print(f"  - {pid:20s} ({arch:25s}): {tb_count} trigger blocks")
            elif arch == "rainfall_single_payout":
                print(f"  - {pid:20s} ({arch:25s}): {len(p['parameters'])} parameters")
        print(f"Persisted -> {out}")

    return reconstructed


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "data/intermediates/segmented_perils.json"
    dest = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_OUTPUT_PATH)
    run(src, dest)
