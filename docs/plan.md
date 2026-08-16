# Roadmap

PHASE 0  → Project foundation + context           (this docs/ setup)
PHASE 1  → Pydantic contracts
PHASE 2  → Eval harness
PHASE 3  → PDF page router
PHASE 4  → Raw cell extraction
PHASE 5  → Segment + classify
PHASE 6  → Reconstruct tables
PHASE 7  → Bedrock + Strands mapping
PHASE 8  → Deterministic validation
PHASE 9  → Full pipeline integration (Orange vertical slice)
PHASE 10 → Human review + provenance
PHASE 11 → Remaining archetypes
PHASE 12 → Ajmer → Alwar adaptation test
PHASE 13 → Riskwolf output

Rule: one stage → one objective → one contract → tests → pass → next stage.
Don't ask a coding agent to "build the pipeline." Ask it to build one
stage, give it the contract + tests + definition of done, and tell it
not to touch other stages.

## Prompt template for every stage

```
You are working on the WBCIS Termsheet Engine.
Read docs/PROJECT_CONTEXT.md first.

CURRENT STAGE: [stage name]
GOAL: [one specific goal]
INPUT CONTRACT: [model]
OUTPUT CONTRACT: [model]
SOURCE: [PDF / fixture / schema file]

CONSTRAINTS:
- Do not modify unrelated stages.
- Do not invent missing values.
- Preserve provenance/confidence.
- Use deterministic code where possible.
- Do not introduce an LLM unless this stage explicitly requires it.

TESTS REQUIRED: [list]
DEFINITION OF DONE: [exact conditions]

Before coding: inspect the repo, explain what you'll touch, flag any
architecture conflicts, then wait for approval.
```
