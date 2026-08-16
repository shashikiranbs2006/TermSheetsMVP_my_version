---
name: table-reconstruction
description: Use when reconstructing merged cells, two-level headers, and phase/sub-period hierarchy from raw cell geometry — deterministic, no LLM. Trigger on Stage 4A / reconstruct tasks.
---

# Reconstruct (Stage 4A — deterministic)

## Problem
Raw cells give you flat values (60, 20, 0, 56.25, 262.50) but not the
hierarchy: Phase I contains sub-periods "1-15 July," "16-31 July," etc.
Geometry (x/y) is what lets you rebuild this.

## Target shape
```
Phase I
├── sub_period: 1-15 July  -> strike1=60 strike2=20 exit=0 rate1=56.25 rate2=262.50 max=7500
└── sub_period: 16-31 July -> strike1=80 strike2=30 exit=10 ...
```
Schema models this as `phases[] -> sub_periods[]`.

## Priority
Solve rainfall_multistrike first - it has merged cells + two-level
headers + nested sub-periods + multiple strikes/rates. If this works,
the other three archetypes are easier.

## Boundary
Purely deterministic Python. No LLM here - this is geometry math, not
interpretation.
