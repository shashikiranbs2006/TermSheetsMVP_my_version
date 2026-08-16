<div align="center">

# KlarDataLabs India Pvt Ltd
### Clarity for smarter decisions
www.klardatalabs.com · contact@mail.klardatalabs.com

</div>

---

# Project Overview — Agentic Parametric Crop Termsheet Engine

**Prepared by:** KlarDataLabs India Pvt Ltd
**Client / Partner:** Riskwolf
**Status:** MVP in build · Discovery complete
**Classification:** Confidential & Proprietary

---

## What we are building

An agentic engine that reads India's weather-based crop insurance termsheets and turns them into standardized, machine-readable parametric product definitions. It ingests historical WBCIS termsheets, extracts and harmonizes their trigger structures, index definitions, crop calendars and payout logic, adapts a product to a new state or district, and outputs a validated draft termsheet plus a JSON payload ready for the Riskwolf platform.

In one line: **messy government termsheets in → standardized, validated, API-ready parametric products out.**

## Why it matters

Today, structuring a crop insurance product for a new region is manual, slow, and inconsistent — the same crop-and-risk combination gets structured differently across states and years. This creates underwriting effort, errors, and no reusable standard. The engine turns a repeated manual exercise into a governed, repeatable capability: define once, adapt everywhere.

## Who it is for

Built for Riskwolf as the parametric structuring capability inside their underwriting and product-generation workflow. KlarDataLabs owns the reusable engine and governed libraries; Riskwolf's platform consumes the standardized output.

## The core insight

The unit of standardization is **not** the crop or the region — it is the **peril archetype**. A handful of repeating structures (temperature-phased, rainfall multi-strike, rainfall single-payout, wind-phased) cover essentially the entire WBCIS format. Model those archetypes once, and one crop-region becomes every crop-region. This is where the reusable IP lives.

## How it works — the pipeline

1. **Ingest** the native-PDF WBCIS termsheet and extract raw table cells.
2. **Segment** the document into its perils and classify each into an archetype.
3. **Reconstruct** merged cells and two-level headers into correct per-period values.
4. **Map** the structured cells into the archetype schema (LLM step, on AWS Bedrock).
5. **Validate** the result and produce underwriter review notes and flags.
6. **Output** a human-readable termsheet and a Riskwolf-ready JSON payload.

A governed library layer (Standard Index Library, Crop Ontology, Template Library) sits under the pipeline and holds the reusable, standardized archetype definitions.

## MVP scope

**In scope**
- WBCIS "Annexure 3" government termsheet format
- One vertical slice end-to-end: extract → adapt → validate → JSON
- The four core peril archetypes and their variants
- Ajmer → Alwar adaptation as the built-in golden-answer test

**Out of scope (for the MVP)**
- Nationwide or all-crop coverage
- Private-insurer termsheet formats
- Headline coverage KPIs (>95% acreage, >90% standardization) — these are the vision, not the MVP deliverable
- Live Riskwolf/Geostore API calls at generation time (later phase)

## Success criteria for the MVP

Generate a validated draft termsheet and a JSON payload that loads cleanly into the Riskwolf sandbox — for one archetype, from a real WBCIS document — measured field-for-field against a hand-verified fixture.

## Current status

- Discovery complete: five real Rajasthan WBCIS samples reviewed (Guava, Kinnow, Onion ×2, Orange)
- Source documents confirmed as native PDFs — OCR is off the critical path
- Format confirmed as single government WBCIS standard — scope bounded and winnable
- Extraction schema and archetype model defined
- Reference JSON fixture and per-archetype mapping prompt drafted
- Build team: two engineers (AWS Bedrock, Strands, full-stack)
