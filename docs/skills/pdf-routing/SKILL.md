---
name: pdf-routing
description: Use when classifying WBCIS termsheet PDF pages as native (text-based) or scanned (image-based), before choosing an extraction method. Trigger on any Stage 1 / ingest / page-routing task.
---

# PDF Routing (Stage 1)

## Rule
```python
text = page.extract_text()
route = "native" if len(text.strip()) > 50 else "scanned"
```
Threshold is >50 chars, not >0 — a lone page number or watermark
shouldn't register as native.

## Output — PageManifest
```json
{"pages": [{"page_no": 1, "route": "native"}, {"page_no": 2, "route": "scanned"}]}
```

## Boundary
Routing only decides native vs scanned. Do NOT do OCR here — that's a
separate concern handled downstream in Stage 2 for scanned pages only.

## Expected on sample set
~157 native pages, ~24 scanned pages. If your counts are wildly off,
check the threshold isn't misclassifying edge pages.
