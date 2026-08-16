# Design notes

## Folder structure (conceptual — not prescribed by source docs)

```
TermSheetsMVP/
├── models/        # Pydantic contracts per stage
├── stages/        # ingest_router, extractor, segmenter, reconstructor,
│                  #   mapper, validator, emitter
├── agents/        # segmentation_agent.py, mapping_agent.py
├── tools/         # pdf_extractor.py, geometry.py
├── schemas/       # wbcis_schema.py
├── eval/          # fixtures/, evaluator.py
├── tests/
├── data/          # input/, intermediates/
└── main.py
```

## Stage contracts (chain)
PageManifest → RawCells → SegmentedPerils → StructuredTermsheet →
ValidatedTermsheet → Outputs

## Cell shape (Stage 2 output)
```json
{"text": "29.0", "x": 250, "y": 180, "width": 50, "height": 20}
```

## Router rule (Stage 1)
```python
text = page.extract_text()
route = "native" if len(text.strip()) > 50 else "scanned"
```
Threshold is >50, not >0, so a page number/watermark alone doesn't
register as native.
