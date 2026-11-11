# VIN/WMI research pipeline

## Phase A — collect source metadata
```bash
python -m gvidb.vin_research collect --with-wmi
```
Collects NHTSA manufacturer records, per-manufacturer WMI data and Part 565/566 document metadata. Records are upserted and can be collected again. WMI lookups may take time because manufacturers are queried individually.

## Phase B — download VIN documents
Start with a limited batch:
```bash
python -m gvidb.vin_research download-docs --limit 100
```
Then download the remaining Part 565 files:
```bash
python -m gvidb.vin_research download-docs
```
PDF text extraction is optional:
```bash
pip install -r requirements-research.txt
python -m gvidb.vin_research download-docs --limit 100
```
Files are stored under `data/vin_sources/nhtsa/documents/`; SQLite records the relative path, SHA-256 and extraction status. Scanned PDFs may need OCR and manual review.

## Phase C — convert documents into rules
1. Confirm manufacturer and WMI scope.
2. Confirm vehicle category and model-year applicability.
3. Transcribe VIN positions using 1-based numbering.
4. Record each code and its documented meaning.
5. Preserve a short evidence excerpt/table reference and source URL.
6. Use `vin_rules_template.json` as the JSON structure.
7. Import with:
```bash
python -c "from gvidb.vin_rules import import_rules; print(import_rules('vin_rules.json'))"
```
Rules should remain `needs_review` until checked against the original source and test VINs.

## Phase D — future offline matcher
The future matcher must match only rules scoped to the relevant WMI, vehicle class and model year; detect conflicts; distinguish candidate from verified results; and return rule IDs, evidence, source and confidence. It must never infer model from WMI alone.

## Global expansion
NHTSA is the first high-value source, not the global finish line. Extend collection to regional regulators and manufacturer technical documents where lawfully accessible. ISO/SAE standards define frameworks and assignment processes; they do not contain every manufacturer's proprietary decoding table.

## Statistics
```bash
python -m gvidb.vin_research stats
```
