# WBCIS Termsheet Human Review & Provenance Report

**Document**: `orange_jhalawar_2019-20.pdf` | **Crop**: `Orange` | **District**: `Jhalawar`, `Rajasthan` | **Year**: `2019-20`

> [!NOTE]
> **EXECUTIVE STATUS: PASS — CLEAN EXTRACTION (NO REVIEW REQUIRED)**
> All extracted parameters meet the confidence threshold (>= 0.75) and passed all deterministic rule checks.

### Executive Summary Metrics

| Metric | Value | Status / Notes |
| :--- | :--- | :--- |
| **Review Required** | `NO` | Ready for downstream automated ingestion |
| **Overall Confidence** | `0.94` | Dynamic mean across all fields |
| **Total Extracted Fields** | `163` | 4 intentional blank fields |
| **Native PDF Exact** | `33` (20.2%) | Direct character extraction (conf: 1.0) |
| **Agent Inferred (Bedrock)** | `130` (79.8%) | Structured schema mapping |
| **OCR Extracted** | `0` (0.0%) | Scanned fallback |
| **Validation Rule Flags** | `0` | 0 errors, 0 warnings, 0 info |

## 1. Underwriter Action Items

> [!TIP]
> **No fields require human review.**
> All 100% of extracted values meet or exceed the 0.75 confidence threshold, and 0 validation errors or warnings were raised by the Stage 5 Rule Engine.

## 2. Non-Native Provenance Log (AI / OCR Mapped Fields)

Total non-native fields: `130` (all schema-mapped parameters from tables).

| Field Path | Value | Source | Confidence | Raw Text / Notes |
| :--- | :--- | :--- | :--- | :--- |
| `perils[0].structure.measure` | `max_temperature` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.unit` | `°C` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.strike` | `4.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.exit` | `22.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.payout_rate` | `2083.33` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.payout_rate_unit` | `Rs/°C` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.max_payout` | `37500.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[0].period.start` | `2020-02-01` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[0].period.end` | `2020-02-14` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[0].trigger` | `29.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[1].period.start` | `2020-02-15` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[1].period.end` | `2020-02-28` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[1].trigger` | `31.0` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[2].period.start` | `2020-03-01` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[2].period.end` | `2020-03-15` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[2].trigger` | `33.5` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[3].label` | `IV` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[3].period.start` | `2020-03-16` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[3].period.end` | `2020-03-31` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[3].trigger` | `35.5` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[4].label` | `V` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[4].period.start` | `2020-04-01` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[4].period.end` | `2020-04-15` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[4].trigger` | `36.5` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[5].label` | `VI` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[5].period.start` | `2020-04-16` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[5].period.end` | `2020-04-30` | `agent_inferred` | `0.95` | — |
| `perils[0].structure.phases[5].trigger` | `39.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.measure` | `aggregate_rainfall` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.direction` | `deficit` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.unit` | `mm` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.rate_unit` | `Rs/mm` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].label` | `Phase I` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[0].period.start` | `2019-07-01` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[0].period.end` | `2019-07-15` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[0].strike_1` | `60.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[0].strike_2` | `20.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[0].exit` | `0.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[0].rate_1` | `56.25` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[0].rate_2` | `262.5` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[0].max_payout` | `7500.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[1].period.start` | `2019-07-16` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[1].period.end` | `2019-07-31` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[1].strike_1` | `80.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[1].strike_2` | `30.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[1].exit` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[1].rate_1` | `45.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[1].rate_2` | `262.5` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[1].max_payout` | `7500.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[2].period.start` | `2019-08-01` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[2].period.end` | `2019-08-15` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[2].strike_1` | `80.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[2].strike_2` | `30.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[2].exit` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[2].rate_1` | `45.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[2].rate_2` | `262.5` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[0].sub_periods[2].max_payout` | `7500.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].label` | `Phase II` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[0].period.start` | `2019-08-16` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[0].period.end` | `2019-08-31` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[0].strike_1` | `80.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[0].strike_2` | `30.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[0].exit` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[0].rate_1` | `45.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[0].rate_2` | `262.5` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[0].max_payout` | `7500.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[1].period.start` | `2019-09-01` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[1].period.end` | `2019-09-15` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[1].strike_1` | `60.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[1].strike_2` | `20.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[1].exit` | `0.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[1].rate_1` | `56.25` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[1].rate_2` | `262.5` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.phases[1].sub_periods[1].max_payout` | `7500.0` | `agent_inferred` | `0.95` | — |
| `perils[1].structure.total_payout` | `37500.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.measure` | `aggregate_rainfall` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.unit` | `mm` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.direction` | `unseasonal` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.payout_mode` | `single` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.periods[0].start` | `2019-06-01` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.periods[0].end` | `2019-06-15` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.strike_1` | `25.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.strike_2` | `40.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.exit` | `60.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.rate_1` | `500.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.rate_2` | `875.0` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.rate_unit` | `Rs/mm` | `agent_inferred` | `0.95` | — |
| `perils[2].structure.max_payout` | `25000.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.measure` | `max_wind_speed` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.unit` | `km/h` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.direction` | `upward` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.strike` | `10.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.exit` | `70.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.payout_rate` | `208.33` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.payout_rate_unit` | `Rs/km/h` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.max_payout` | `12500.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].block_label` | `block_1` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].period.start` | `2019-10-15` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].period.end` | `2019-11-30` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[0].period.start` | `2019-10-15` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[0].period.end` | `2019-10-31` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[0].trigger` | `50.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[1].period.start` | `2019-11-01` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[1].period.end` | `2019-11-15` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[1].trigger` | `55.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[2].period.start` | `2019-11-16` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[2].period.end` | `2019-11-30` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[0].phases[2].trigger` | `55.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].block_label` | `block_2` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].period.start` | `2020-02-15` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].period.end` | `2020-03-31` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[0].label` | `I` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[0].period.start` | `2020-02-15` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[0].period.end` | `2020-02-28` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[0].trigger` | `50.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[1].label` | `II` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[1].period.start` | `2020-03-01` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[1].period.end` | `2020-03-15` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[1].trigger` | `55.0` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[2].label` | `III` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[2].period.start` | `2020-03-16` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[2].period.end` | `2020-03-31` | `agent_inferred` | `0.95` | — |
| `perils[3].structure.trigger_blocks[1].phases[2].trigger` | `50.0` | `agent_inferred` | `0.95` | — |

## 3. Per-Peril Extraction & Provenance Breakdown

| Peril ID | Archetype | Cover Objective | Total Fields | Native | Agent Mapped | Avg Conf | Flags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `high_temperature` | `temperature_phased` | To cover anticipated yield loss in the e... | `37` | `5` | `32` | `0.96` | `0` |
| `deficit_rainfall` | `rainfall_multistrike` | To cover anticipated yield loss in the e... | `52` | `5` | `47` | `0.95` | `0` |
| `unseasonal_rainfall` | `rainfall_single_payout` | To cover anticipated yield loss in the e... | `18` | `5` | `13` | `0.96` | `0` |
| `high_wind_speed` | `wind_phased` | To cover anticipated yield loss in the e... | `43` | `5` | `38` | `0.96` | `0` |

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