# WBCIS Termsheet Engine — Pipeline Architecture Spec (MVP)

**Status:** Internal build doc for the engineering team
**Principle:** Deterministic spine + agent judgment in the middle. Every stage independently testable, with typed contracts and field-level provenance.
**Golden rule:** Production-ready *architecture*, MVP-level *operations*. Build the structure right (typed stages, provenance, per-stage eval). Do NOT build the heavy operational machinery (distributed orchestration, retry queues, dashboards, autoscaling) until Riskwolf is committed and real volume/SLAs are known.

---

## 1. Pipeline shape

| # | Stage | Type | Owner |
|---|---|---|---|
| 1 | Ingest & Route | Deterministic | Code |
| 2 | Extract to Cells | Deterministic + OCR | Code (native) / Vision model (scanned) |
| 3 | Segment & Classify | Agent | Strands + Bedrock |
| 4 | Reconstruct & Map | Agent + Deterministic | Code (reconstruct) + Agent (map) |
| 5 | Validate | Deterministic | Code (independent of agent) |
| 6 | Emit | Deterministic | Code |

**Flow:** 1 → 2 → 3 → 4 → 5 → 6, sequential. Each stage persists its typed output, so any stage can be re-run from the previous stage's saved output.

**Two cross-cutting layers sit across all stages:**
- The **eval harness** runs against *every* stage output, not just the final JSON — so a regression is traced to the stage that caused it.
- The **human-in-the-loop gate** sits before Stage 6, pausing low-confidence or flagged fields for underwriter review.

The agent (Strands + Bedrock) owns only the fuzzy stages — Stage 3, and the mapping half of Stage 4. Exact work — reading native cells, validation math, emitting payloads — stays deterministic. The agent *calls* deterministic tools; it does not replace them.

---

## 2. Stages, with typed contracts

Each stage takes a defined input model and returns a defined output model (Pydantic). Contracts are the highest-value practice here — they let a stage be tested, replaced, or re-run alone, and make a bad hand-off fail at the boundary instead of corrupting output downstream.

### Stage 1 — Ingest & Route  *(deterministic)*
- **Does:** Classifies every page `native | scanned` (text-layer test, threshold > 50 chars + char-count check). Splits the document into termsheet units.
- **In:** `RawDocument { file_path }`
- **Out:** `PageManifest { pages: [ { page_no, route: native|scanned, crop?, district? } ] }`
- **Notes:** Runs once, cheaply. Everything downstream trusts this routing. ~13% of pages route to OCR.

### Stage 2 — Extract to Cells  *(deterministic + OCR path)*
- **Does:** Native pages → pdfplumber / Camelot. Scanned pages → OCR / vision model. **Both converge on one common cell format.** Downstream never needs to know which path a page took.
- **In:** `PageManifest`
- **Out:** `RawCells { blocks: [ { cells[][], geometry, source: native|ocr, confidence } ] }`
- **Notes:** Native confidence = 1.0 (lossless). OCR confidence = model score. Confidence is set HERE and travels with every field forever.

### Stage 3 — Segment & Classify  *(agent)*
- **Does:** Splits raw cells into perils by section markers; classifies each into an archetype (`temperature_phased | rainfall_multistrike | rainfall_single_payout | wind_phased`).
- **In:** `RawCells`
- **Out:** `SegmentedPerils { document_meta, perils: [ { archetype, raw_cells, cover_period } ] }`
- **Notes:** Largely rule-assistable (headers are consistent) but agent handles variation. Cheap model tier is fine.

### Stage 4 — Reconstruct & Map  *(deterministic reconstruct + agent map)*
- **Does:** (a) Deterministic: reconstruct merged cells / two-level headers from geometry → per-period values. (b) Agent: map reconstructed cells to archetype schema, normalize dates to ISO (year inferred from cover period), nest sub-periods.
- **In:** `SegmentedPerils`
- **Out:** `StructuredTermsheet { document, perils[schema JSON], per_field_provenance }`
- **Notes:** The reconstruct half is exact logic, not judgment — keep it deterministic. The map half is the agent's core job. Force structured output; validate JSON before it leaves the stage.

### Stage 5 — Validate  *(deterministic, INDEPENDENT of the agent)*
- **Does:** Rule-based checks — completeness, strike/exit sanity vs direction, payout arithmetic reconciliation, premium contradictions, SI present. Routes low-confidence / flagged fields to review.
- **In:** `StructuredTermsheet`
- **Out:** `ValidatedTermsheet { termsheet, validation_report, flags[], review_required: bool }`
- **Notes:** MUST be independent code, not the same agent that produced the JSON — otherwise it validates its own hallucination. The flags ARE the product.

### Stage 6 — Emit  *(deterministic)*
- **Does:** Renders human-readable termsheet + Riskwolf-ready JSON payload.
- **In:** `ValidatedTermsheet` (post human review if `review_required`)
- **Out:** `Outputs { termsheet_doc, riskwolf_payload_json }`
- **Notes:** Payload shape is defined by Riskwolf's JSON contract (outstanding input — request from them).

---

## 3. Cross-cutting practices (the "production-ready" part)

**Typed contracts between every stage.** Pydantic models for each In/Out above. A malformed hand-off fails at the boundary. This is the single highest-leverage practice — adopt it first.

**Provenance + confidence on every field.** Each value records origin (`native_exact | ocr | agent_inferred`) and a confidence score, set at extraction and carried through. This is what powers the human-review routing in Stage 5 and what makes an underwriter trust the system. In insurance this is the trust layer, not a nice-to-have.

**Idempotent, re-runnable stages.** Each stage persists its output (S3 / DB). Fix a Stage 4 bug → re-run from Stage 3's saved output; don't re-OCR 181 pages. Also makes the pipeline debuggable — you can see exactly which stage produced a bad value.

**Per-stage eval, not just end-to-end.** The harness scores accuracy at each stage boundary against the corpus (Cauliflower-14, Tomato-29, Onion-10 crop-sets from the real document). When accuracy drops you know which stage regressed. Wire this from day one.

**Human-in-the-loop as an explicit stage.** Flagged / low-confidence outputs pause before Stage 6. How strict this is depends on whether Riskwolf consumes output straight-through or with underwriter review (open question — confirm with them).

**Orchestration: start boring.** MVP = a sequential orchestrator (a Python script calling each stage with typed hand-offs). Strands orchestrates the *agent* stages internally. Add real workflow orchestration (Step Functions / queues / retries) only when volume demands it — that is a post-MVP scaling concern.

---

## 4. MVP line — build now vs later

| Build NOW (cheap, saves pain later) | Build LATER (after Riskwolf commits) |
|---|---|
| Typed stage contracts (Pydantic) | Distributed orchestration (Step Functions/Airflow) |
| Field provenance + confidence | Retry queues, dead-letter handling |
| Persisted stage intermediates | Monitoring dashboards, alerting |
| Per-stage eval harness | Autoscaling / parallel document throughput |
| Sequential orchestrator | Multi-tenant, SLAs, audit exports |
| One archetype end-to-end (rainfall_multistrike) | All archetypes × all crops at volume |

**Discipline:** typed stages and provenance now; operational scale later. Don't spend intern time hardening infrastructure for a product that isn't sold yet. The MVP's job is a convincing demo that triggers the commercial conversation.

---

## 5. Build order for the skeleton

1. Define all six typed contracts (Pydantic models) — the pipeline skeleton, stages stubbed.
2. Stage 1 (router) + Stage 2 native path — get real cells out of one native page.
3. Stage 5 validation rules + eval harness — so "correct" is measurable before building the agent.
4. Stages 3–4 on ONE archetype (`rainfall_multistrike`) — agent segment + map, measured against the fixture.
5. Stage 6 emit → JSON that loads into the Riskwolf sandbox.
6. Widen: add OCR path (Stage 2 scanned), then remaining archetypes one at a time.

---

## 6. Open inputs (gate specific stages)
- **Riskwolf JSON payload contract** — defines Stage 6 output shape.
- **Straight-through vs underwriter-reviewed** — sets strictness of Stages 5–6 and the human-in-the-loop gate.
- **OCR tool choice** for the scanned path (Stage 2) — vision model vs dedicated OCR/table engine.
