# Project Progress

## Completed
- [x] Project context
- [x] Pydantic contracts
- [x] Eval harness
- [x] Page router
- [x] Raw cell extraction
- [x] Segmentation
- [x] Archetype classification
- [x] Reconstruction
- [x] Bedrock mapping
- [x] Validation
- [x] Full pipeline
- [ ] Provenance
- [ ] Remaining archetypes
- [ ] Ajmer → Alwar
- [ ] Riskwolf output

## Current Stage
Phase 10 -- Field-Level Provenance & Traceability

## Current Goal
Enhance extraction provenance across all stages, ensuring every extracted field
links back to exact cell/geometry coordinates in raw_cells.json.

## Last Test Result
Phase 9 -- 259/259 tests passed (4 new Phase 9 pipeline integration tests + 255 earlier stages).
Full pipeline orchestrator built: stages/pipeline.py and main.py

Pipeline Integration Findings:
  - End-to-end PDF to ValidatedTermsheet: Ran in ~10.27s on real Orange_TermSheet.pdf.
  - Sequential execution verified:
    1. Stage 1 Ingest & Route -> data/intermediates/page_manifest.json (1 native page)
    2. Stage 2 Cell Extractor -> data/intermediates/raw_cells.json (330 cells)
    3. Stage 3 Segmenter      -> data/intermediates/segmented_perils.json (4 perils, 100% cells accounted)
    4. Stage 4A Reconstructor -> data/intermediates/reconstructed_perils.json (4 peril tables reconstructed)
    5. Stage 4B Mapper        -> data/intermediates/mapped_termsheet.json + mapping_agent_logs.json (Bedrock agent)
    6. Stage 5 Validator      -> data/intermediates/validated_termsheet.json (0 errors, 0 warnings, review_required=False)
  - All intermediate artifacts verified persisted, readable, and strictly adhering to Pydantic models.
  - Idempotency verified: running pipeline repeatedly yields consistent, clean ValidatedTermsheet.

Eval Harness Report (against docs/source/sample_orange_jhalawar.json):
  - Field comparison summary: PASS: 177, FAIL: 6, WARN: 164, TOTAL: 347
  - All 4 perils (high_temperature, deficit_rainfall, unseasonal_rainfall, high_wind_speed) and document header/premium business values achieve 100% PASS rate.
  - Remaining 6 FAILs against read-only ground truth fixture:
    * 3 in document.source_meta (page_range scalar "1" vs [1], is_scan/ocr_used boolean False vs null in fixture, documented in ADR-012 as intentional operational deviations).
    * 2 in extraction_confidence: overall computed as dynamic mean across all fields (0.94 vs mock 0.86) and perils[3].cover_period.end (1.0 vs mock 0.72, pending user verification).
    * 1 in root-level flags (early sample fixture mock vs Stage 5 ValidatedTermsheet.flags, documented in ADR-011).


Validation Engine Findings:
  - Real Orange Data (Orange_TermSheet.pdf): Cleanly passed all 6 rule categories.
    * 0 errors, 0 warnings, review_required = False.
    * Sum insured: 125,000 > 0.
    * Deficit rainfall payout arithmetic: 5 x 7500 = 37,500 == total_payout.
    * Temperature rate-span: 2083.33 * 18 = 37,499.94 ~= 37,500.
    * Strike/exit relationships: deficit exit < strike_1 (0 < 20 < 60, 10 < 30 < 80); upward strike < exit (4 < 22, 10 < 70).
  - All 6 Rule Categories verified via independent synthetic failure tests:
    1. completeness_check: detected missing document.crop and empty perils.
    2. strike_exit_sanity: detected deficit exit > strike and upward strike > exit.
    3. payout_arithmetic: detected sub-period max_payout sum mismatch.
    4. premium_contradiction: detected gross_premium=0 with farmers_premium > 0 (Guava trap).
    5. sum_insured_check: detected total_sum_insured <= 0 or missing.
    6. confidence_threshold: verified field confidence < 0.75 raises warning and sets review_required = True.
  - Immutability verified: validator is 100% read-only and does not mutate any termsheet values.

Artifact Persisted:
  - data/intermediates/validated_termsheet.json (ValidatedTermsheet)

Strands + Bedrock Mapping Findings:
  - Model used: amazon.nova-lite-v1:0 via AWS Bedrock (us-east-1, temperature=0.0).
  - All 4 perils mapped into typed Pydantic models with ExtractedValue wrappers:
    * high_temperature     -> TemperaturePhasedStructure (6 phases, triggers 29.0..39.0)
    * deficit_rainfall     -> RainfallMultistrikeStructure (5 sub-periods, rates 56.25/45.00, 262.50, max 7500, total 37500)
    * unseasonal_rainfall  -> RainfallSinglePayoutStructure (strike_1 25, strike_2 40, exit 60, rate_1 500, rate_2 875, max 25000)
    * high_wind_speed      -> WindPhasedStructure (2 trigger blocks, triggers 50/55, strike 10, exit 70, payout 208.33, max 12500)
  - Date normalization verified: all dates converted to ISO YYYY-MM-DD format based on scheme year 2019-20.
  - Blank-is-null verified: gross_premium and premium_pct remain null (None), never coerced to 0.
  - Idempotency & Consistency: verified with repeated runs yielding identical values.
  - Token Usage & Cost (Orange_TermSheet.pdf run):
    * Calls: 4 LLM invocations (1 per peril)
    * Estimated Input Tokens: ~2,213 (~8,855 chars)
    * Estimated Output Tokens: ~1,185 (~4,741 chars)
    * Total Cost per Document: ~$0.000417 USD (< 0.05¢)

Artifacts Persisted:
  - data/intermediates/mapped_termsheet.json (StructuredTermsheet output)
  - data/intermediates/mapping_agent_logs.json (raw prompts, responses, and execution traces)

Deterministic Table Reconstruction Findings:
  1. deficit_rainfall (rainfall_multistrike):
     - Phase I (3 sub-periods: 01-Jul..15-Jul, 16-Jul..31-Jul, 1-Aug..15-Aug)
     - Phase II (2 sub-periods: 16-Aug..31-Aug, 01-Sep..15-Sep)
     - Merged values ('60 80', '20 30', '0 10') cleanly partitioned to sub-periods 0 & 1
     - Rates 56.25/45.00, 262.50, Max payout 7500, Total payout 37500 attached exactly.
  2. high_temperature (temperature_phased):
     - 6 sequential phases (I..VI) with triggers [29.0, 31.0, 33.5, 35.5, 36.5, 39.0]
     - Common Strike (4), Exit (22), Payout Rate (2083.33), Max Payout (37500).
  3. high_wind_speed (wind_phased):
     - 2 trigger blocks (Oct-Nov: [50, 55, 55], Feb-Mar: [50, 55, 50])
     - Strike (10), Exit (70), Payout Rate (208.33), Max Payout (12500).
  4. unseasonal_rainfall (rainfall_single_payout):
     - Flat parameters: Strike 1=25, Strike 2=40, Exit=60, Rate 1=500, Rate 2=875, Max=25000.
  5. Geometric Tolerance:
     - Verified with jitter tests (+/- 2.5 points) matching rows and columns stably.
  6. Ambiguity / Clustering Report:
     - 0 cells failed clustering or required force-fitting. All table cells cleanly mapped.

Output persisted to: data/intermediates/reconstructed_perils.json

Segmented Perils Output:
  1. high_temperature     -> archetype: temperature_phased      (90 cells)
  2. deficit_rainfall     -> archetype: rainfall_multistrike    (89 cells)
  3. unseasonal_rainfall  -> archetype: rainfall_single_payout  (38 cells)
  4. high_wind_speed      -> archetype: wind_phased             (91 cells)

Cell Accounting Breakdown (100% accounted for, 0 dropped):
  - 4 Perils Total       : 308 cells
  - Document Header      :  14 cells (Scheme, Annexure, State, District, Crop, Unit, RWS)
  - Premium Footer       :   8 cells (Premium Description, Total Sum Insured, % etc.)
  - Total Accounted      : 330 / 330 cells

Output persisted to: data/intermediates/segmented_perils.json

Extraction Library Decision & Analysis:
  - Library used: pdfplumber (Camelot is not installed in the environment).
  - Method: Hybrid table + cell-bounded word extraction.
    * extract_tables() provides clean, merged-cell-aware text.
    * find_tables().rows provide precise per-cell bounding boxes (x, y, width, height).
    * Non-table text (headers, objectives, definitions, un-tabled district text) extracted
      via word-level bounding boxes filtered against actual cell boundaries.
  - Output: 330 RawCells (269 non-blank with geometry + 61 merged/blank placeholders)
    persisted to data/intermediates/raw_cells.json.
  - Validation: 100% of required text (headers, state, district, crop, all 6 temp triggers,
    all rainfall rates/payouts, all wind triggers/rates, premium values) verified present with
    valid positive geometry coordinates. Blank cells preserved as text=None.
Stage 1 router built: stages/ingest_router.py

Actual page counts (probed, not assumed):
  Orange_TermSheet.pdf   : 1 page  -- native=1   scanned=0  (2176 chars)
  Sample Termsheets.pdf  : 10 pages -- native=10  scanned=0  (1089-1211 chars each)
  Both available PDFs are 100% native -- no scanned pages exist in the fixture set.

Scanned-branch tests use mock pdfplumber pages (documented in test file).
Output persisted: data/intermediates/page_manifest.json
Threshold: >50 chars stripped (not >0 -- guards against watermark/page-num artefacts).
Eval harness built:
  eval/evaluator.py  — recursive JSON walker, compare(expected, actual)
  eval/report.py     — PASS/FAIL/WARN terminal formatter with ANSI colour
  eval/cli.py        — python -m eval.cli expected.json actual.json
  eval/fixtures/orange_jhalawar_gt.json — first ground-truth fixture

## Known Problems
—

## Next Step
Phase 9 -- Full Pipeline Integration & End-to-End Orchestrator (Stage 6).
Build stages/pipeline.py and top-level CLI connecting all stages from PDF to ValidatedTermsheet.

*Update this file after every stage. This is what gives your coding
agent persistent state across sessions instead of relying on chat history.*