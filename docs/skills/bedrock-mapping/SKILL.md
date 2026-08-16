---
name: bedrock-mapping
description: Use when building or prompting the Strands + Bedrock agent that maps reconstructed cells into schema-shaped JSON. Trigger on Stage 4B / agent mapping / LLM tasks.
---

# Map (Stage 4B - Strands + Bedrock)

## Input
Reconstructed cells (already geometrically correct) + target schema +
archetype-specific instructions + a few worked examples.
**Never the raw PDF, never unreconstructed cells.**

## Agent may
- Normalize dates ("01 April to 15 April" -> {"start":"2020-04-01","end":"2020-04-15"})
- Map fields to schema keys
- Build nested structures (phases/sub_periods)
- Pick correct schema fields per archetype

## Agent must NOT
- Invent missing values
- Guess premium numbers
- Decide validation rules
- "Fix" numbers that look wrong
- Inspect the raw PDF directly
- Replace deterministic reconstruction

## Critical rule
Blank source -> `null`. Never `0`. This is a hard rule, not a style
preference - silent zero-filling is exactly the failure mode this
architecture exists to prevent.
