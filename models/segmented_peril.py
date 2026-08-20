"""
models/segmented_peril.py — Stage 3 output (Segment & Classify).

The segmenter slices the full RawCells list into peril-shaped groups and
assigns each group an archetype classification.  The archetype tag is a
Literal over the four known archetypes; any other value is rejected.

Design note on peril_id:
  peril_id is a free string (str), not a Literal.  A single document can
  carry two perils with the same semantic label (e.g. "deficit_rainfall" for
  a Phase I/II block and a separate 2B section).  The archetype field is the
  real discriminator that drives downstream parsing.  See decision log in
  docs/PROJECT_CONTEXT.md.
"""

from typing import Literal

from pydantic import BaseModel

from models.raw_cells import RawCell


class SegmentedPeril(BaseModel):
    """
    A contiguous slice of RawCells belonging to one peril section, together
    with its archetype classification.

    Attributes:
        peril_id:  Human-readable label for the peril.  Free string — not
                   unique within a document.  Examples: "deficit_rainfall",
                   "high_temperature", "excess_rainfall_2b".
        raw_cells: The extracted cells that make up this peril's table(s).
        archetype: Structural classification.  Drives Stage 4 reconstruction
                   logic.  Must be one of the four known archetypes.
    """

    peril_id: str
    raw_cells: list[RawCell]
    archetype: Literal[
        "temperature_phased",
        "rainfall_multistrike",
        "rainfall_single_payout",
        "wind_phased",
        "unknown",
    ] | None


class SegmentedPerils(BaseModel):
    """
    Stage 3 top-level output.  All segmented perils from a single document,
    in document order.
    """

    perils: list[SegmentedPeril]
