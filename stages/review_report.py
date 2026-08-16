"""
stages/review_report.py — Stage 6: Field-Level Provenance & Human Review Surface.

Transforms a ValidatedTermsheet into an executive, underwriter-ready Markdown report.
Enables a reviewer (e.g. Prasad or Riskwolf underwriters) to answer in under 10 seconds:
- Is human review required?
- Which fields are uncertain or have validation flags, and why?
- What is the full provenance breakdown across native PDF text, OCR, and Bedrock inference?
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from models.common import ExtractedValue
from models.structured_termsheet import PerilEnvelope, StructuredTermsheet
from models.validated_termsheet import ValidatedTermsheet, ValidationFlag

DEFAULT_INPUT_PATH = Path("data/intermediates/validated_termsheet.json")
DEFAULT_OUTPUT_PATH = Path("data/intermediates/review_report.md")
DEFAULT_CONFIDENCE_THRESHOLD = 0.75


# ---------------------------------------------------------------------------
# Helper: Extract all ExtractedValues with paths
# ---------------------------------------------------------------------------


def _walk_extracted_nodes(data: Any, path: str = "") -> list[tuple[str, ExtractedValue]]:
    """Recursively collect all leaf ExtractedValue instances with their full paths."""
    nodes: list[tuple[str, ExtractedValue]] = []
    if isinstance(data, ExtractedValue):
        nodes.append((path, data))
    elif isinstance(data, BaseModel):
        for field_name in data.__class__.model_fields:
            field_val = getattr(data, field_name)
            child_path = f"{path}.{field_name}" if path else field_name
            nodes.extend(_walk_extracted_nodes(field_val, child_path))
    elif isinstance(data, dict):
        for k, v in data.items():
            child_path = f"{path}.{k}" if path else k
            nodes.extend(_walk_extracted_nodes(v, child_path))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            child_path = f"{path}[{idx}]"
            nodes.extend(_walk_extracted_nodes(item, child_path))
    return nodes


# ---------------------------------------------------------------------------
# Core Report Generator
# ---------------------------------------------------------------------------


def generate_review_report(
    validated_termsheet: ValidatedTermsheet | dict | str | Path,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> str:
    """
    Generate an underwriter-ready Markdown review and provenance report.

    Args:
        validated_termsheet: ValidatedTermsheet instance, dict, or path to JSON.
        confidence_threshold: Threshold below which fields are flagged for review (0.75).

    Returns:
        Formatted Markdown report string.
    """
    if isinstance(validated_termsheet, (str, Path)):
        p = Path(validated_termsheet)
        if not p.exists():
            raise FileNotFoundError(f"Validated termsheet file not found: {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        validated = ValidatedTermsheet.model_validate(data)
    elif isinstance(validated_termsheet, dict):
        validated = ValidatedTermsheet.model_validate(validated_termsheet)
    elif isinstance(validated_termsheet, ValidatedTermsheet):
        validated = validated_termsheet
    else:
        raise TypeError(f"Unsupported input type: {type(validated_termsheet)}")

    ts = validated.termsheet
    flags = validated.flags
    review_required = validated.review_required

    doc = ts.document
    perils = ts.perils or []

    # 1. Collect all leaf nodes
    extracted_nodes = _walk_extracted_nodes(doc, "document")
    for i, peril in enumerate(perils):
        extracted_nodes.extend(_walk_extracted_nodes(peril, f"perils[{i}]"))

    total_fields = len(extracted_nodes)
    native_nodes = [n for n in extracted_nodes if n[1].source == "native_exact"]
    agent_nodes = [n for n in extracted_nodes if n[1].source == "agent_inferred"]
    ocr_nodes = [n for n in extracted_nodes if n[1].source == "ocr"]
    blank_nodes = [n for n in extracted_nodes if n[1].value is None]

    # 2. Identify low confidence fields (non-null with confidence < threshold)
    low_conf_nodes = [
        (path, ev)
        for path, ev in extracted_nodes
        if ev.value is not None and ev.confidence is not None and ev.confidence < confidence_threshold
    ]

    # 3. Index flags by field_path
    flags_by_path: dict[str, list[ValidationFlag]] = {}
    unmapped_flags: list[ValidationFlag] = []
    for f in flags:
        if f.field_path:
            flags_by_path.setdefault(f.field_path, []).append(f)
        else:
            unmapped_flags.append(f)

    # 4. Combine review items
    review_paths = set(p for p, _ in low_conf_nodes) | set(flags_by_path.keys())
    error_flags_count = sum(1 for f in flags if f.severity == "error")
    warning_flags_count = sum(1 for f in flags if f.severity == "warning")
    info_flags_count = sum(1 for f in flags if f.severity == "info")

    doc_state = doc.state.value if doc.state else "N/A"
    doc_district = doc.district.value if doc.district else "N/A"
    doc_crop = doc.crop.value if doc.crop else "N/A"
    doc_year = doc.scheme_year.value if doc.scheme_year else "N/A"
    doc_file = doc.source_meta.file_name if doc.source_meta else "N/A"

    overall_conf = ts.extraction_confidence.overall if ts.extraction_confidence else 1.0

    lines: list[str] = []

    # -----------------------------------------------------------------------
    # Header & Executive Summary
    # -----------------------------------------------------------------------
    lines.append("# WBCIS Termsheet Human Review & Provenance Report")
    lines.append("")
    lines.append(f"**Document**: `{doc_file}` | **Crop**: `{doc_crop}` | **District**: `{doc_district}`, `{doc_state}` | **Year**: `{doc_year}`")
    lines.append("")

    if not review_required and len(flags) == 0 and len(low_conf_nodes) == 0:
        lines.append("> [!NOTE]")
        lines.append("> **EXECUTIVE STATUS: PASS — CLEAN EXTRACTION (NO REVIEW REQUIRED)**")
        lines.append("> All extracted parameters meet the confidence threshold (>= 0.75) and passed all deterministic rule checks.")
    else:
        lines.append("> [!WARNING]")
        lines.append(f"> **EXECUTIVE STATUS: REVIEW REQUIRED ({len(review_paths)} field(s) flagged)**")
        lines.append(f"> Action required by underwriter: {error_flags_count} error(s), {warning_flags_count} warning(s), {len(low_conf_nodes)} low-confidence field(s).")
    lines.append("")

    # Summary Metrics Table
    native_pct = f"{(len(native_nodes) / total_fields * 100):.1f}%" if total_fields else "0%"
    agent_pct = f"{(len(agent_nodes) / total_fields * 100):.1f}%" if total_fields else "0%"
    ocr_pct = f"{(len(ocr_nodes) / total_fields * 100):.1f}%" if total_fields else "0%"

    lines.append("### Executive Summary Metrics")
    lines.append("")
    lines.append("| Metric | Value | Status / Notes |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| **Review Required** | `{'YES' if review_required else 'NO'}` | {'Underwriter sign-off needed' if review_required else 'Ready for downstream automated ingestion'} |")
    lines.append(f"| **Overall Confidence** | `{overall_conf:.2f}` | Dynamic mean across all fields |")
    lines.append(f"| **Total Extracted Fields** | `{total_fields}` | {len(blank_nodes)} intentional blank fields |")
    lines.append(f"| **Native PDF Exact** | `{len(native_nodes)}` ({native_pct}) | Direct character extraction (conf: 1.0) |")
    lines.append(f"| **Agent Inferred (Bedrock)** | `{len(agent_nodes)}` ({agent_pct}) | Structured schema mapping |")
    lines.append(f"| **OCR Extracted** | `{len(ocr_nodes)}` ({ocr_pct}) | Scanned fallback |")
    lines.append(f"| **Validation Rule Flags** | `{len(flags)}` | {error_flags_count} errors, {warning_flags_count} warnings, {info_flags_count} info |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 1: Underwriter Action & Review Items
    # -----------------------------------------------------------------------
    lines.append("## 1. Underwriter Action Items")
    lines.append("")
    if not review_required and len(review_paths) == 0 and len(unmapped_flags) == 0:
        lines.append("> [!TIP]")
        lines.append("> **No fields require human review.**")
        lines.append("> All 100% of extracted values meet or exceed the 0.75 confidence threshold, and 0 validation errors or warnings were raised by the Stage 5 Rule Engine.")
        lines.append("")
    else:
        lines.append("| Field Path | Extracted Value | Confidence | Source | Validation Findings / Review Reason |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")

        # Map nodes for quick lookup
        node_dict = {p: ev for p, ev in extracted_nodes}

        for path in sorted(review_paths):
            ev = node_dict.get(path)
            val_str = str(ev.value) if ev and ev.value is not None else "*(null / blank)*"
            conf_str = f"{ev.confidence:.2f}" if ev and ev.confidence is not None else "N/A"
            source_str = ev.source if ev else "N/A"

            findings: list[str] = []
            if ev and ev.value is not None and ev.confidence is not None and ev.confidence < confidence_threshold:
                findings.append(f"Low confidence ({conf_str} < {confidence_threshold})")

            if path in flags_by_path:
                for f in flags_by_path[path]:
                    findings.append(f"[{f.severity.upper()}] {f.rule}: {f.message}")

            findings_str = "<br>".join(findings) if findings else "Flagged for review"
            lines.append(f"| `{path}` | `{val_str}` | `{conf_str}` | `{source_str}` | {findings_str} |")
        lines.append("")

        if unmapped_flags:
            lines.append("#### General / Unmapped Document Flags")
            lines.append("")
            for f in unmapped_flags:
                lines.append(f"- **[{f.severity.upper()}] {f.rule}**: {f.message}")
            lines.append("")

    # -----------------------------------------------------------------------
    # Section 2: Non-Native Provenance Log (source != "native_exact")
    # -----------------------------------------------------------------------
    non_native_nodes = [n for n in extracted_nodes if n[1].source != "native_exact"]
    lines.append("## 2. Non-Native Provenance Log (AI / OCR Mapped Fields)")
    lines.append("")
    if not non_native_nodes:
        lines.append("*All fields in this document were extracted directly from native PDF text.*")
        lines.append("")
    else:
        lines.append(f"Total non-native fields: `{len(non_native_nodes)}` (all schema-mapped parameters from tables).")
        lines.append("")
        lines.append("| Field Path | Value | Source | Confidence | Raw Text / Notes |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for path, ev in non_native_nodes:
            val_str = str(ev.value) if ev.value is not None else "*(null)*"
            raw_str = f"`{ev.raw}`" if ev.raw is not None else "—"
            conf_str = f"{ev.confidence:.2f}" if ev.confidence is not None else "1.00"
            lines.append(f"| `{path}` | `{val_str}` | `{ev.source}` | `{conf_str}` | {raw_str} |")
        lines.append("")

    # -----------------------------------------------------------------------
    # Section 3: Per-Peril Extraction & Provenance Breakdown
    # -----------------------------------------------------------------------
    lines.append("## 3. Per-Peril Extraction & Provenance Breakdown")
    lines.append("")
    if not perils:
        lines.append("*No perils extracted in this document.*")
        lines.append("")
    else:
        lines.append("| Peril ID | Archetype | Cover Objective | Total Fields | Native | Agent Mapped | Avg Conf | Flags |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for idx, peril in enumerate(perils):
            p_nodes = _walk_extracted_nodes(peril, f"perils[{idx}]")
            p_native = sum(1 for _, ev in p_nodes if ev.source == "native_exact")
            p_agent = sum(1 for _, ev in p_nodes if ev.source == "agent_inferred")
            p_scores = [ev.confidence for _, ev in p_nodes if ev.confidence is not None and ev.value is not None]
            p_avg_conf = f"{(sum(p_scores) / len(p_scores)):.2f}" if p_scores else "N/A"
            p_flags = sum(1 for f in flags if f.field_path and f.field_path.startswith(f"perils[{idx}]"))
            cov_obj = peril.cover_objective.value if peril.cover_objective else "—"
            cov_obj_short = (cov_obj[:40] + "...") if len(cov_obj) > 40 else cov_obj

            lines.append(
                f"| `{peril.peril_id}` | `{peril.archetype}` | {cov_obj_short} | "
                f"`{len(p_nodes)}` | `{p_native}` | `{p_agent}` | `{p_avg_conf}` | `{p_flags}` |"
            )
        lines.append("")

    # -----------------------------------------------------------------------
    # Section 4: Deterministic Audit Rules Log
    # -----------------------------------------------------------------------
    lines.append("## 4. Deterministic Audit Rules Log")
    lines.append("")
    lines.append("Summary of Stage 5 rule engine execution:")
    lines.append("")
    lines.append("| Audit Rule | Status | Description |")
    lines.append("| :--- | :--- | :--- |")

    rule_descriptions = {
        "completeness_check": "Verifies state, district, crop, unit, and at least one peril are present",
        "strike_exit_sanity": "Validates direction constraints (strike > exit for deficit; exit > strike for upward)",
        "payout_arithmetic": "Verifies sub-period/phase sums equal total peril payout and rate calculations",
        "premium_contradiction": "Audits gross premium vs farmer premium for logical contradictions",
        "sum_insured_check": "Verifies total sum insured is a positive non-zero number",
        "confidence_threshold": f"Audits all non-blank leaf scalars against {confidence_threshold:.2f} threshold",
    }

    for rule_name, desc in rule_descriptions.items():
        rule_flags = [f for f in flags if f.rule == rule_name]
        if not rule_flags:
            status_str = "✅ PASS (0 flags)"
        else:
            status_str = f"⚠️ {len(rule_flags)} flag(s)"
        lines.append(f"| `{rule_name}` | {status_str} | {desc} |")
    lines.append("")

    lines.append("---")
    lines.append("*Report generated automatically by WBCIS Termsheet Engine (Stage 6: Review & Provenance Surface).*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Persistence & CLI Runner
# ---------------------------------------------------------------------------


def persist(
    report_md: str,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Persist Markdown review report to disk."""
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(report_md, encoding="utf-8")
    return out_p


def run(
    validated_termsheet_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> str:
    """
    Run Stage 6: Read validated termsheet JSON, generate report, and persist to file.
    """
    p = Path(validated_termsheet_path)
    if not p.exists():
        raise FileNotFoundError(f"Validated termsheet file not found at: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))
    validated = ValidatedTermsheet.model_validate(data)

    report_md = generate_review_report(validated, confidence_threshold=confidence_threshold)
    persist(report_md, output_path)
    return report_md


if __name__ == "__main__":
    report = run()
    print(f"Generated review report -> {DEFAULT_OUTPUT_PATH}")
    print("\n--- Summary Snippet ---\n")
    print("\n".join(report.splitlines()[:25]))
