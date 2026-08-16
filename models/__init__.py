"""
models/__init__.py — Public API for the models package.

Imports every stage-boundary model so callers can write:
    from models import PageManifest, StructuredTermsheet, ...
"""

from models.common import CoverPeriod, DatePeriod, ExtractedValue
from models.outputs import Outputs
from models.page_manifest import PageManifest
from models.raw_cells import RawCell, RawCells
from models.segmented_peril import SegmentedPeril, SegmentedPerils
from models.structured_termsheet import (
    DocumentFields,
    ExtractionConfidence,
    PerilEnvelope,
    PerilStructure,
    Premium,
    RainfallMultistrikePhase,
    RainfallMultistrikeStructure,
    RainfallSinglePayoutStructure,
    SourceMeta,
    TemperaturePhase,
    TemperaturePhasedStructure,
    WindPhase,
    WindPhasedStructure,
    WindTriggerBlock,
)
from models.validated_termsheet import ValidationFlag, ValidatedTermsheet

__all__ = [
    # common
    "ExtractedValue",
    "CoverPeriod",
    "DatePeriod",
    # Stage 1
    "PageManifest",
    # Stage 2
    "RawCell",
    "RawCells",
    # Stage 3
    "SegmentedPeril",
    "SegmentedPerils",
    # Stage 4 — top-level
    "StructuredTermsheet",
    "DocumentFields",
    "SourceMeta",
    "Premium",
    "PerilEnvelope",
    "PerilStructure",
    "ExtractionConfidence",
    # Stage 4 — archetype structures
    "TemperaturePhasedStructure",
    "TemperaturePhase",
    "RainfallMultistrikeStructure",
    "RainfallMultistrikePhase",
    "RainfallSinglePayoutStructure",
    "WindPhasedStructure",
    "WindTriggerBlock",
    "WindPhase",
    # Stage 5
    "ValidatedTermsheet",
    "ValidationFlag",
    # Stage 6
    "Outputs",
]

from models.structured_termsheet import StructuredTermsheet  # noqa: E402 — after all sub-imports
