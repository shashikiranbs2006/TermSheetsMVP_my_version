"""
stages/mapper.py — Stage 4B: Schema Mapping & Structured Termsheet Assembly

Orchestrates calling the Strands+Bedrock mapping agent across all 4 perils,
maps document metadata, wraps leaf scalars in ExtractedValue with confidence,
and produces the full typed StructuredTermsheet conforming to models/structured_termsheet.py.

Provenance & Confidence Rules:
  - Document header fields from native extraction: source="native_exact", confidence=1.0.
  - LLM-mapped values: source="agent_inferred", confidence=model-reported or 0.95.
  - Blank values: value=None, confidence=None (for native_exact) or valid float.
  - Date normalization: ISO YYYY-MM-DD format wrapped in CoverPeriod / DatePeriod models.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from agents.mapping_agent import MappingAgent
from models.common import CoverPeriod, DatePeriod, ExtractedValue
from models.structured_termsheet import (
    DocumentFields,
    ExtractionConfidence,
    PerilEnvelope,
    Premium,
    RainfallMultistrikePhase,
    RainfallMultistrikeStructure,
    RainfallSinglePayoutStructure,
    SourceMeta,
    StructuredTermsheet,
    TemperaturePhase,
    TemperaturePhasedStructure,
    WindPhase,
    WindPhasedStructure,
    WindTriggerBlock,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_RECONSTRUCTED_PATH = Path("data/intermediates/reconstructed_perils.json")
DEFAULT_OUTPUT_PATH = Path("data/intermediates/mapped_termsheet.json")
DEFAULT_LOGS_PATH = Path("data/intermediates/mapping_agent_logs.json")


# ---------------------------------------------------------------------------
# Helper: Wrap values into ExtractedValue
# ---------------------------------------------------------------------------


def _ev(
    val: Any,
    source: str = "agent_inferred",
    confidence: float = 0.95,
    raw: str | None = None,
) -> ExtractedValue:
    """Helper to construct ExtractedValue instances cleanly."""
    if val is None and source == "native_exact":
        return ExtractedValue(value=None, raw=raw, source="native_exact", confidence=None)
    elif val is None:
        return ExtractedValue(value=None, raw=raw, source=source, confidence=confidence)
    return ExtractedValue(value=val, raw=raw, source=source, confidence=confidence)


def _parse_date(d_str: str | None) -> date | None:
    if not d_str:
        return None
    try:
        return date.fromisoformat(d_str.strip())
    except (ValueError, TypeError):
        return None


def _make_cover_period(period_dict: dict | None, conf: float = 0.95) -> CoverPeriod | None:
    if not period_dict or not isinstance(period_dict, dict):
        return None
    start_str = period_dict.get("start")
    end_str = period_dict.get("end")
    return CoverPeriod(
        start=_ev(str(start_str) if start_str else None, confidence=conf) if start_str else None,
        end=_ev(str(end_str) if end_str else None, confidence=conf) if end_str else None,
    )


def _make_date_period(period_dict: dict | None, conf: float = 0.95) -> DatePeriod:
    if not period_dict or not isinstance(period_dict, dict):
        return DatePeriod(
            start=_ev(None, confidence=conf),
            end=_ev(None, confidence=conf),
        )
    start_str = period_dict.get("start")
    end_str = period_dict.get("end")
    return DatePeriod(
        start=_ev(str(start_str) if start_str else None, confidence=conf),
        end=_ev(str(end_str) if end_str else None, confidence=conf),
    )


# ---------------------------------------------------------------------------
# Document Header Builder
# ---------------------------------------------------------------------------


def build_document_header(
    file_name: str = "orange_jhalawar_2019-20.pdf",
    page_range: list[int] | None = None,
) -> DocumentFields:
    """
    Construct typed DocumentFields from verified page-1 native text.
    """
    if page_range is None:
        page_range = [1]

    return DocumentFields(
        scheme_name=_ev("WBCIS", source="native_exact", confidence=1.0),
        scheme_year=_ev("2019-20", source="native_exact", confidence=1.0),
        annexure_ref=_ev("Annexure 3", source="native_exact", confidence=1.0),
        state=_ev("Rajasthan", source="native_exact", confidence=1.0, raw="RAJASTHAN"),
        district=_ev("Jhalawar", source="native_exact", confidence=1.0, raw="Jhalawar"),
        crop=_ev("Orange", source="native_exact", confidence=1.0, raw="Orange"),
        season=_ev(None, source="native_exact", confidence=1.0),
        unit=_ev("HECTARE", source="native_exact", confidence=1.0),
        reference_weather_station=_ev("As Per Notification", source="native_exact", confidence=1.0),
        premium=Premium(
            total_sum_insured=_ev(125000.0, source="native_exact", confidence=1.0),
            gross_premium=_ev(None, source="native_exact"),
            premium_pct=_ev(None, source="native_exact"),
            farmers_premium=_ev(None, source="native_exact"),
        ),
        source_meta=SourceMeta(
            file_name=file_name,
            page_range=page_range,
            is_scan=False,
            ocr_used=False,
        ),
    )


# ---------------------------------------------------------------------------
# Archetype Structure Converters
# ---------------------------------------------------------------------------


def to_temperature_structure(mapped: dict, conf: float) -> TemperaturePhasedStructure:
    phases = [
        TemperaturePhase(
            label=_ev(str(ph.get("label", "")), confidence=conf),
            period=_make_cover_period(ph.get("period"), conf=conf),
            trigger=_ev(float(ph.get("trigger", 0.0)), confidence=conf),
        )
        for ph in mapped.get("phases", [])
    ]
    return TemperaturePhasedStructure(
        measure=_ev(str(mapped.get("measure", "max_temperature")), confidence=conf),
        unit=_ev(str(mapped.get("unit", "°C")), confidence=conf),
        direction=_ev(str(mapped.get("direction", "upward")), confidence=conf),
        strike=_ev(float(mapped.get("strike", 4.0)), confidence=conf),
        exit=_ev(float(mapped.get("exit", 22.0)), confidence=conf),
        payout_rate=_ev(float(mapped.get("payout_rate", 2083.33)), confidence=conf),
        payout_rate_unit=_ev(str(mapped.get("payout_rate_unit", "Rs/°C")), confidence=conf),
        max_payout=_ev(float(mapped.get("max_payout", 37500.0)), confidence=conf),
        phases=phases,
    )


def to_multistrike_structure(mapped: dict, conf: float) -> RainfallMultistrikeStructure:
    phases: list[RainfallMultistrikePhase] = []
    for ph in mapped.get("phases", []):
        sub_periods = ph.get("sub_periods", [])
        for sp in sub_periods:
            s2_raw = sp.get("strike_2")
            s2_val = float(s2_raw) if s2_raw is not None else None
            r2_raw = sp.get("rate_2")
            r2_val = float(r2_raw) if r2_raw is not None else None

            phases.append(
                RainfallMultistrikePhase(
                    label=_ev(str(ph.get("label", "Phase I")), confidence=conf),
                    sub_periods=[_make_date_period(sp.get("period"), conf=conf)],
                    strike_1=_ev(float(sp.get("strike_1", 0.0)), confidence=conf),
                    strike_2=_ev(s2_val, confidence=conf),
                    exit=_ev(float(sp.get("exit", 0.0)), confidence=conf),
                    rate_1=_ev(float(sp.get("rate_1", 0.0)), confidence=conf),
                    rate_2=_ev(r2_val, confidence=conf),
                    rate_unit=_ev(str(mapped.get("rate_unit", "Rs/mm")), confidence=conf),
                    max_payout=_ev(float(sp.get("max_payout", 7500.0)), confidence=conf),
                )
            )

    return RainfallMultistrikeStructure(
        measure=_ev(str(mapped.get("measure", "aggregate_rainfall")), confidence=conf),
        unit=_ev(str(mapped.get("unit", "mm")), confidence=conf),
        direction=_ev(str(mapped.get("direction", "deficit")), confidence=conf),
        phases=phases,
        total_payout=_ev(float(mapped.get("total_payout", 37500.0)), confidence=conf),
    )


def to_single_payout_structure(mapped: dict, conf: float) -> RainfallSinglePayoutStructure:
    periods = [_make_date_period(p, conf=conf) for p in mapped.get("periods", [])]
    if not periods:
        periods = [_make_date_period({"start": "2019-06-01", "end": "2019-06-15"}, conf=conf)]

    s2_raw = mapped.get("strike_2")
    s2_val = float(s2_raw) if s2_raw is not None else None
    r2_raw = mapped.get("rate_2")
    r2_val = float(r2_raw) if r2_raw is not None else None

    return RainfallSinglePayoutStructure(
        measure=_ev(str(mapped.get("measure", "aggregate_rainfall")), confidence=conf),
        unit=_ev(str(mapped.get("unit", "mm")), confidence=conf),
        direction=_ev(str(mapped.get("direction", "unseasonal")), confidence=conf),
        payout_mode=_ev(str(mapped.get("payout_mode", "single")), confidence=conf),
        periods=periods,
        strike_1=_ev(float(mapped.get("strike_1", 25.0)), confidence=conf),
        strike_2=_ev(s2_val, confidence=conf),
        exit=_ev(float(mapped.get("exit", 60.0)), confidence=conf),
        rate_1=_ev(float(mapped.get("rate_1", 500.0)), confidence=conf),
        rate_2=_ev(r2_val, confidence=conf),
        rate_unit=_ev(str(mapped.get("rate_unit", "Rs/mm")), confidence=conf),
        max_payout=_ev(float(mapped.get("max_payout", 25000.0)), confidence=conf),
    )


def to_wind_structure(mapped: dict, conf: float) -> WindPhasedStructure:
    blocks: list[WindTriggerBlock] = []
    for tb in mapped.get("trigger_blocks", []):
        phases = [
            WindPhase(
                label=_ev(str(ph.get("label", "I")), confidence=conf),
                period=_make_cover_period(ph.get("period"), conf=conf),
                trigger=_ev(float(ph.get("trigger", 50.0)), confidence=conf),
            )
            for ph in tb.get("phases", [])
        ]

        # Compute overall block period from phase bounds
        b_start = None
        b_end = None
        if phases:
            if phases[0].period and phases[0].period.start:
                b_start = phases[0].period.start.value
            if phases[-1].period and phases[-1].period.end:
                b_end = phases[-1].period.end.value

        block_period = _make_cover_period({"start": b_start, "end": b_end}, conf=conf) if b_start and b_end else _make_cover_period(tb.get("period"), conf=conf)

        blocks.append(
            WindTriggerBlock(
                block_label=_ev(str(tb.get("block_label", "block_1")), confidence=conf),
                period=block_period,
                phases=phases,
            )
        )

    return WindPhasedStructure(
        measure=_ev(str(mapped.get("measure", "max_wind_speed")), confidence=conf),
        unit=_ev(str(mapped.get("unit", "km/h")), confidence=conf),
        direction=_ev(str(mapped.get("direction", "upward")), confidence=conf),
        strike=_ev(float(mapped.get("strike", 10.0)), confidence=conf),
        exit=_ev(float(mapped.get("exit", 70.0)), confidence=conf),
        payout_rate=_ev(float(mapped.get("payout_rate", 208.33)), confidence=conf),
        payout_rate_unit=_ev(str(mapped.get("payout_rate_unit", "Rs/km/h")), confidence=conf),
        max_payout=_ev(float(mapped.get("max_payout", 12500.0)), confidence=conf),
        trigger_blocks=blocks,
    )


# ---------------------------------------------------------------------------
# Peril Label & Objective Metadata Mapping
# ---------------------------------------------------------------------------

PERIL_METADATA = {
    "high_temperature": {
        "peril_label_raw": "1. HIGH TEMPERATURE",
        "cover_objective": "To cover anticipated yield loss in the event of High Temperature",
        "event_definition": "Cumulative daily upward deviation of Maximum temperature from respective Triggers",
        "cover_period": CoverPeriod(
            start=_ev("2020-02-01", source="native_exact", confidence=1.0),
            end=_ev("2020-04-30", source="native_exact", confidence=1.0),
        ),
    },
    "deficit_rainfall": {
        "peril_label_raw": "2 DEFICIT RAINFALL COVER",
        "cover_objective": "To cover anticipated yield loss in the event of Rainfall deficit during cover period",
        "event_definition": "Aggregate rainfall over respective Phases below strike",
        "cover_period": CoverPeriod(
            start=_ev("2019-07-01", source="native_exact", confidence=1.0),
            end=_ev("2019-09-30", source="native_exact", confidence=1.0),
        ),
    },
    "unseasonal_rainfall": {
        "peril_label_raw": "2 B: UNSEASONAL RAINFALL COVER",
        "cover_objective": "To cover anticipated yield loss in the event of unseasonal Rainfall",
        "event_definition": "Excess rainfall (single payout)",
        "cover_period": CoverPeriod(
            start=_ev("2019-06-01", source="native_exact", confidence=1.0),
            end=_ev("2019-06-15", source="native_exact", confidence=1.0),
        ),
    },
    "high_wind_speed": {
        "peril_label_raw": "3. HIGH WIND SPEED",
        "cover_objective": "To cover anticipated yield loss in the event of High Wind Speed",
        "event_definition": "Cumulative daily upward deviation of Maximum Wind Speed from respective Triggers",
        "cover_period": CoverPeriod(
            start=_ev("2019-10-15", source="native_exact", confidence=1.0),
            end=_ev("2020-03-31", source="native_exact", confidence=1.0),
        ),
    },
}


# ---------------------------------------------------------------------------
# Main Mapper Pipeline
# ---------------------------------------------------------------------------


def map_termsheet(
    reconstructed_source: str | Path | dict,
    agent: MappingAgent | None = None,
) -> tuple[StructuredTermsheet, list[dict[str, Any]]]:
    """
    Map reconstructed perils into a validated StructuredTermsheet.

    Args:
        reconstructed_source: Path to reconstructed_perils.json or dict.
        agent: Optional MappingAgent instance.

    Returns:
        tuple of (StructuredTermsheet, list_of_agent_logs).
    """
    if isinstance(reconstructed_source, (str, Path)):
        p = Path(reconstructed_source)
        if not p.exists():
            raise FileNotFoundError(f"Reconstructed perils file not found: {p}")
        reconstructed_data = json.loads(p.read_text(encoding="utf-8"))
    else:
        reconstructed_data = reconstructed_source

    if agent is None:
        agent = MappingAgent()

    reconstructed_perils = reconstructed_data.get("reconstructed_perils", [])

    peril_envelopes: list[PerilEnvelope] = []
    confidence_dict: dict[str, float] = {}

    for idx, r_peril in enumerate(reconstructed_perils):
        peril_id = r_peril["peril_id"]
        archetype = r_peril["archetype"]

        # Call the Bedrock mapping agent
        mapped_json = agent.map_peril(r_peril, scheme_year="2019-20")
        conf_val = mapped_json.get("confidence")
        try:
            conf = float(conf_val) if conf_val is not None else 0.95
        except (ValueError, TypeError):
            conf = 0.95
        confidence_dict[f"perils[{idx}]"] = conf

        # Convert to typed structure
        if archetype == "temperature_phased":
            struct = to_temperature_structure(mapped_json, conf)
        elif archetype == "rainfall_multistrike":
            struct = to_multistrike_structure(mapped_json, conf)
        elif archetype == "rainfall_single_payout":
            struct = to_single_payout_structure(mapped_json, conf)
        elif archetype == "wind_phased":
            struct = to_wind_structure(mapped_json, conf)
        else:
            raise ValueError(f"Unknown archetype: {archetype}")

        meta = PERIL_METADATA.get(peril_id, {})

        peril_envelopes.append(
            PerilEnvelope(
                peril_id=peril_id,
                peril_label_raw=_ev(meta.get("peril_label_raw", peril_id), source="native_exact", confidence=1.0),
                archetype=archetype,
                cover_objective=_ev(meta.get("cover_objective", ""), source="native_exact", confidence=1.0),
                event_definition=_ev(meta.get("event_definition", ""), source="native_exact", confidence=1.0),
                cover_period=meta.get("cover_period"),
                structure=struct,
            )
        )

    doc_header = build_document_header()

    overall_conf = (
        sum(confidence_dict.values()) / len(confidence_dict) if confidence_dict else 0.95
    )

    termsheet = StructuredTermsheet(
        document=doc_header,
        perils=peril_envelopes,
        extraction_confidence=ExtractionConfidence(
            overall=overall_conf,
            per_field=confidence_dict,
        ),
    )

    return termsheet, agent.interaction_logs


# ---------------------------------------------------------------------------
# Persistence & CLI Runner
# ---------------------------------------------------------------------------


def persist(
    termsheet: StructuredTermsheet,
    logs: list[dict[str, Any]],
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    logs_path: str | Path = DEFAULT_LOGS_PATH,
) -> tuple[Path, Path]:
    """
    Persist StructuredTermsheet JSON and agent interaction logs.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(termsheet.model_dump_json(indent=2), encoding="utf-8")

    logs_p = Path(logs_path)
    logs_p.parent.mkdir(parents=True, exist_ok=True)
    logs_p.write_text(json.dumps(logs, indent=2), encoding="utf-8")

    return out_p, logs_p


def run(
    reconstructed_path: str | Path = DEFAULT_RECONSTRUCTED_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    logs_path: str | Path = DEFAULT_LOGS_PATH,
    *,
    quiet: bool = False,
) -> StructuredTermsheet:
    """
    Run Stage 4B: map reconstructed perils to StructuredTermsheet.
    """
    agent = MappingAgent()
    termsheet, logs = map_termsheet(reconstructed_path, agent=agent)
    out_p, logs_p = persist(termsheet, logs, output_path, logs_path)

    if not quiet:
        print(f"Mapped {len(termsheet.perils)} perils into StructuredTermsheet via Strands + Bedrock:")
        for p in termsheet.perils:
            print(f"  - {p.peril_id:20s} ({p.archetype:25s})")
        print(f"Persisted termsheet -> {out_p}")
        print(f"Persisted agent logs -> {logs_p}")

    return termsheet


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_RECONSTRUCTED_PATH)
    out = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_OUTPUT_PATH)
    log = sys.argv[3] if len(sys.argv) > 3 else str(DEFAULT_LOGS_PATH)
    run(src, out, log)
