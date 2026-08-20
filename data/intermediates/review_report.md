# WBCIS Termsheet Human Review & Provenance Report

**Document**: `orange_jhalawar_2019-20.pdf` | **Crop**: `Orange` | **District**: `Jhalawar`, `Rajasthan` | **Year**: `2019-20`

> [!NOTE]
> **EXECUTIVE STATUS: PASS — CLEAN EXTRACTION (NO REVIEW REQUIRED)**
> All extracted parameters meet the confidence threshold (>= 0.75) and passed all deterministic rule checks.

### Executive Summary Metrics

| Metric | Value | Status / Notes |
| :--- | :--- | :--- |
| **Review Required** | `NO` | Ready for downstream automated ingestion |
| **Overall Confidence** | `0.95` | Dynamic mean across all fields |
| **Total Extracted Fields** | `341` | 4 intentional blank fields |
| **Native PDF Exact** | `68` (19.9%) | Direct character extraction (conf: 1.0) |
| **Agent Inferred (Bedrock)** | `273` (80.1%) | Structured schema mapping |
| **OCR Extracted** | `0` (0.0%) | Scanned fallback |
| **Validation Rule Flags** | `0` | 0 errors, 0 warnings, 0 info |

## 1. Underwriter Action Items

> [!TIP]
> **No fields require human review.**
> All 100% of extracted values meet or exceed the 0.75 confidence threshold, and 0 validation errors or warnings were raised by the Stage 5 Rule Engine.

## 2. Non-Native Provenance Log (AI / OCR Mapped Fields)

Total non-native fields: `273` (all schema-mapped parameters from tables).

| Field Path | Value | Source | Confidence | Raw Text / Notes |
| :--- | :--- | :--- | :--- | :--- |
| `perils[0].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.payout_rate` | `1866.67` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.max_payout` | `56000.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.payout_rate` | `2000.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.max_payout` | `60000.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.payout_rate` | `1500.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.max_payout` | `45000.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.payout_rate` | `1700.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.max_payout` | `51000.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.payout_rate` | `1000.0` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.max_payout` | `30000.0` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[4].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.payout_rate` | `2333.33` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.max_payout` | `70000.0` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[5].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.payout_rate` | `2000.0` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.max_payout` | `60000.0` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[6].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.payout_rate` | `1933.33` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.max_payout` | `58000.0` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[7].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.payout_rate` | `1500.0` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.max_payout` | `45000.0` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[0].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[0].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[0].trigger` | `35.0` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[1].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[1].trigger` | `34.0` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[2].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[2].trigger` | `33.0` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[3].period.start` | `2019-09-16` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[3].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[8].structure.phases[3].trigger` | `32.0` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.measure` | `max_wind_speed` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.unit` | `km/h` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.strike` | `5.0` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.payout_rate` | `950.71` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.payout_rate_unit` | `Rs/km/h` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.max_payout` | `33275.0` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].block_label` | `block_1` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].period.start` | `2019-07-01` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[0].period.start` | `2019-07-01` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[0].period.end` | `2019-07-15` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[0].trigger` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[1].period.start` | `2019-07-16` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[1].period.end` | `2019-07-31` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[1].trigger` | `45.0` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[2].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[2].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[2].trigger` | `45.0` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[3].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[3].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[9].structure.trigger_blocks[0].phases[3].trigger` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.measure` | `aggregate_rainfall` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.direction` | `deficit` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.unit` | `mm` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.rate_unit` | `Rs/mm` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].label` | `Phase I` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[0].period.start` | `2019-07-01` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[0].period.end` | `2019-07-31` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[0].strike_1` | `120.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[0].strike_2` | `80.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[0].exit` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[0].rate_1` | `74.87` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[0].rate_2` | `174.7` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[0].max_payout` | `9983.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[1].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[1].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[1].strike_1` | `250.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[1].strike_2` | `150.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[1].exit` | `100.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[1].rate_1` | `39.93` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[1].rate_2` | `186.34` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[1].max_payout` | `13310.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[2].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[2].period.end` | `2019-09-30` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[2].strike_1` | `80.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[2].strike_2` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[2].exit` | `30.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[2].rate_1` | `74.87` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[2].rate_2` | `698.74` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.phases[0].sub_periods[2].max_payout` | `9982.0` | `agent_inferred` | `0.95` | — |
| `perils[10].structure.total_payout` | `33275.0` | `agent_inferred` | `0.95` | — |

## 3. Per-Peril Extraction & Provenance Breakdown

| Peril ID | Archetype | Cover Objective | Total Fields | Native | Agent Mapped | Avg Conf | Flags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `29` | `5` | `24` | `0.96` | `0` |
| `high_wind_speed` | `wind_phased` | To cover anticipated yield loss in the e... | `32` | `5` | `27` | `0.96` | `0` |
| `deficit_rainfall` | `rainfall_multistrike` | To cover anticipated yield loss in the e... | `35` | `5` | `30` | `0.96` | `0` |

## 4. Deterministic Audit Rules Log

Summary of Stage 5 rule engine execution:

| Audit Rule | Status | Description |
| :--- | :--- | :--- |
| `completeness_check` | ✅ PASS (0 flags) | Verifies state, district, crop, unit, and at least one peril are present |
| `strike_exit_sanity` | ✅ PASS (0 flags) | Validates direction constraints (strike > exit for deficit; exit > strike for upward) |
| `payout_arithmetic` | ✅ PASS (0 flags) | Verifies sub-period/phase sums equal total peril payout and rate calculations |
| `premium_contradiction` | ✅ PASS (0 flags) | Audits gross premium vs farmer premium for logical contradictions |
| `sum_insured_check` | ✅ PASS (0 flags) | Verifies total sum insured is a positive non-zero number |
| `confidence_threshold` | ✅ PASS (0 flags) | Audits all non-blank leaf scalars against 0.75 threshold |

---
*Report generated automatically by WBCIS Termsheet Engine (Stage 6: Review & Provenance Surface).*