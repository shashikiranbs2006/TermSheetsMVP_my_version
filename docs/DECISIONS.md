# Architecture Decisions

## ADR-001
Native PDF extraction uses pdfplumber/Camelot.

## ADR-002
LLM does not directly extract from PDF — it receives clean structured cells only.

## ADR-003
Reconstruction (merged cells, headers, sub-periods) is deterministic, not agent-driven.

## ADR-004
Validation is independent of the mapping agent (agent doesn't grade its own output).

## ADR-005
Blank source fields become null, not zero.

## ADR-006
Every stage has typed Pydantic contracts.

## ADR-007
Every stage output is persisted (idempotent, re-runnable stages).

## ADR-008
Initial archetype = rainfall_multistrike.

## ADR-009
MVP uses sequential orchestration — no distributed infra.

## ADR-010
Riskwolf JSON payload contract is an open input — don't invent it. Track it below.

## ADR-011
Validation Flags Separation (Stage 4B vs Stage 5).
The original conceptual extraction schema (wbcis_extraction_schema.md §5 / sample_orange_jhalawar.json) placed root-level `flags` directly on the canonical JSON output. In our architecture, extraction (Stage 4B: StructuredTermsheet) is strictly separated from rule-based validation (Stage 5: ValidatedTermsheet). StructuredTermsheet encapsulates document fields, perils, and extraction_confidence. Stage 5 independently audits the termsheet and produces `ValidatedTermsheet.flags` and `review_required: bool`. This guarantees that the mapping agent does not self-validate or invent validation findings.

## ADR-012
Document Source Metadata (`page_range`, `is_scan`, `ocr_used`) Reporting.
In `docs/source/sample_orange_jhalawar.json`, `page_range` was given as `"1"` (a string scalar), while `is_scan` and `ocr_used` were set to `null` because the original author had not yet executed the ingest router and lacked runtime pipeline execution state. In our engine:
1. `SourceMeta.page_range` is strictly modeled as `list[int]` (`[1]`) to cleanly support multi-page annexures (e.g. `[3, 4]`).
2. `SourceMeta.is_scan` and `SourceMeta.ocr_used` strictly report runtime booleans (`is_scan: False`, `ocr_used: False` for native PDFs like Orange) determined by Stage 1 (`ingest_router`).
These are intentional operational deviations over the static ground truth fixture.

## Open items
- [ ] Riskwolf JSON contract — owner: ______  follow-up date: ______
- [ ] OCR/vision tool choice for scanned pages — still open
- [ ] Stage ownership split between Shashikiran and Aniket — not yet decided
- [ ] **Confidence Scoring for `agent_inferred` fields**: Currently reflects LLM self-reported certainty, not source-text visual quality (e.g. awkwardly wrapped multi-line dates like `perils[3].cover_period.end`). This is a known gap, not a blocker for MVP. Revisit if this pattern recurs on messier documents later.
