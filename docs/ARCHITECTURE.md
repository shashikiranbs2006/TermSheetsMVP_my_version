# Architecture — Pointer

Full spec: docs/source/Pipeline_Architecture_Spec.md (do not duplicate here)

Quick-reference (for fast lookups only — source file is authoritative):

PDF → [1 Route] → [2 Extract Cells] → [3 Segment/Classify] →
[4a Reconstruct (deterministic) → 4b Map (Strands+Bedrock)] →
[5 Validate] → [6 Emit] → Riskwolf JSON

Cross-cutting: Eval Harness (expected vs actual, field-by-field) +
Provenance/Confidence (travels with every field through the pipeline).

If this quick-reference ever conflicts with the source spec, the source
spec wins — update this file, don't patch around it.
