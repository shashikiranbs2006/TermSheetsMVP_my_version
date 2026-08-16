# Schema — Pointer

Full contract: docs/source/wbcis_extraction_schema.md (do not duplicate here)

Quick-reference:
- Top level: `document` (state/district/crop/scheme/year/unit) + `perils[]`
- Each peril: peril_id, peril_label_raw, archetype, cover_objective,
  event_definition, cover_period, structure (shape depends on archetype)
- 4 archetypes: temperature_phased, rainfall_multistrike,
  rainfall_single_payout, wind_phased
- Every value field should carry: value, source (native_exact/ocr/agent_inferred), confidence

Before writing any Stage 4+ code, read the actual source file — this is
just a memory-jog, not the contract.
