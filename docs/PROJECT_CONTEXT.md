# WBCIS Termsheet Engine — Project Context

## Goal
Convert WBCIS Annexure 3 PDF termsheets into validated, machine-readable
parametric insurance products for Riskwolf.

## Pipeline (6 stages)
1. Ingest & Route      — native vs scanned page detection
2. Extract to Cells    — pdfplumber/Camelot → cells + x/y geometry
3. Segment & Classify  — split into perils, tag with archetype
4. Reconstruct & Map   — deterministic table reconstruction + agent schema-mapping
5. Validate            — independent deterministic rule engine
6. Emit                — human-readable termsheet + Riskwolf JSON

## Architecture principle
**Deterministic spine + agent judgment in the middle.**

Deterministic (plain Python):
- PDF routing
- native extraction
- geometry reconstruction
- validation
- emission

Agent (Strands + Bedrock):
- segmentation/classification where genuinely ambiguous
- schema mapping
- date normalization
- interpreting messy headers/structures

The agent never touches the raw PDF directly and never invents values.

## Technologies
Python · Pydantic · pdfplumber / Camelot · Strands · AWS Bedrock · JSON · pytest

## Initial target
Orange / Jhalawar / Rajasthan / WBCIS 2019-20

## First archetype
rainfall_multistrike (hardest — solve this first, others get easier after)

## Source of truth
The original PDF. JSON is an extracted representation, not the source of truth.
Full schema contract: see docs/source/wbcis_extraction_schema.md

## Hard rules
- Never invent missing values.
- Blank ≠ zero — blank source field becomes `null`, not `0`.
- Preserve raw values alongside normalized ones.
- Preserve provenance + confidence on every extracted field.
- Every stage has a typed Pydantic input/output contract.
- Every stage is independently testable and persists its output.
- Don't use an LLM where deterministic code is sufficient.
- Don't build production infra yet (no distributed systems, no live APIs).

This file is the agent's constitution. Point every coding-agent session
here first.
