---
name: archetype-classification
description: Use when splitting a termsheet page into peril sections and tagging each with its archetype. Trigger on Stage 3 / segmentation / classification tasks.
---

# Segment & Classify (Stage 3)

## The 4 archetypes
| Archetype | Used for |
|---|---|
| temperature_phased | High temperature |
| rainfall_multistrike | Deficit rainfall (hardest — multi-strike, phased) |
| rainfall_single_payout | Unseasonal / excess rainfall |
| wind_phased | High wind speed |

## Why archetypes matter
This is the product thesis: standardize on peril *structure*, not
crop/region. One parser per archetype, reused across every
crop/district/state/year — only calibrated values change.

## Boundary
This stage answers "what section is this and what type is it" — NOT
"what are the actual trigger numbers." Value extraction happens later
(Stage 4). Don't let this stage pull real numbers.
