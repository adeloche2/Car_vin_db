# GVIDB roadmap

## Foundation — implemented
- [x] Flask/SQLite application for Termux.
- [x] Arabic RTL UI and progressive VIN input.
- [x] VehiclesDB catalogue importer.
- [x] VIN normalization, shape validation, US check-digit helper and position parser.
- [x] NHTSA vPIC online VIN/WMI adapter.
- [x] Source-aware messages and VIN-only colour policy.
- [x] Research schema, NHTSA manufacturer/WMI/Part 565/566 collector.
- [x] Document download, SHA-256 and optional PDF text extraction.
- [x] JSON importer for reviewed rules.

## Research coverage
- [ ] Run full NHTSA collection and archive collection statistics.
- [ ] Audit pagination and document metadata.
- [ ] Add public regional WMI sources outside the US.
- [ ] Add OCR workflow for scanned manufacturer documents.

## Manufacturer rule corpus
- [ ] Extract Part 565 tables by manufacturer/model year.
- [ ] Build a review UI for position/code tables.
- [ ] Store model, engine, body, plant and year rules with evidence.
- [ ] Add conflict detection and rule versioning.
- [ ] Create test VIN fixtures for every verified rule.

## Offline decoding and release quality
- [ ] Implement local matching over verified rules only.
- [ ] Return candidate/verified/no-rule/conflict states.
- [ ] Add evidence trace and confidence.
- [ ] Add import/export manifests and checksums.
- [ ] Expand tests across regions and vehicle categories.
