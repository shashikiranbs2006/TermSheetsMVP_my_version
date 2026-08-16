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

## Open items
- [ ] Riskwolf JSON contract — owner: ______  follow-up date: ______
- [ ] OCR/vision tool choice for scanned pages — still open
- [ ] Stage ownership split between Shashikiran and Aniket — not yet decided
