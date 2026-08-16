---
name: validation-rules
description: Use when building the independent deterministic validator that checks agent-produced JSON against rules, flags issues, and sets review_required. Trigger on Stage 5 / validation tasks.
---

# Validate (Stage 5 - deterministic, independent of the mapping agent)

## Why independent
The agent that produced the JSON must not be the one grading it - that's
the model checking its own homework. Validator is separate deterministic
Python + Pydantic.

## Checks
1. Completeness - required fields present
2. Strike/exit sanity - relationship makes sense for the peril direction
3. Payout arithmetic - phase totals reconcile with overall max
4. Premium contradictions - e.g. total_premium=0 but farmer_premium>0 -> flag, don't silently fix
5. Sum insured - exists and > 0
6. Confidence - below threshold -> `review_required = true`

## Provenance
Every value should carry `source` (native_exact / ocr / agent_inferred)
and `confidence`. This is what lets the system say "this field needs a
human," not just pass/fail the whole document.
