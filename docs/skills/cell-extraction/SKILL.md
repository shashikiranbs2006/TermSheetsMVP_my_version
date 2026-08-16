---
name: cell-extraction
description: Use when extracting table cells with geometry (x/y/width/height) from native PDF pages, or wiring up the OCR path for scanned pages. Trigger on Stage 2 / raw cell extraction tasks.
---

# Cell Extraction (Stage 2)

## Native path
pdfplumber / Camelot (lattice mode) → cells with coordinates.

## Scanned path
OCR/vision → text → same cell output shape as native path.
**Both paths must produce identical output format** — downstream code
never knows or cares whether a cell came from OCR or native extraction.

## Cell shape
```json
{"text": "29.0", "x": 250, "y": 180, "width": 50, "height": 20}
```

## Why geometry matters
The hard part isn't reading "29.0" — it's knowing which column/phase it
belongs to. x/y coordinates are what let Stage 4 reconstruct hierarchy
(e.g. Phase I containing two sub-period columns). This is the core of
extraction — don't skip preserving geometry to save effort.

## Boundary
Do NOT interpret values or map to schema fields here. This stage answers
"can Python accurately see the table," nothing more. No LLM involved.
