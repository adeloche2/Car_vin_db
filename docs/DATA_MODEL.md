# SQLite data model

## Core tables
- `makes`: make slug/name per vehicle kind. A make can have multiple rows for different kinds.
- `vehicle_models`: make/model catalogue records, unique by (kind, make_slug, model_slug), retaining raw JSON and source version.
- `wmi_codes`: optional local WMI registry records and their source/verification flag.
- `data_sources`: source name, version, URL, licence, import time and record count.
- `vin_decodes`: stored decode responses.
- `app_meta`: catalogue/application metadata.

## Research tables
- `vin_manufacturers`: manufacturer identity and raw source records.
- `vin_wmi_registry`: WMI assignments, vehicle class/country and provenance.
- `vin_pattern_documents`: Part 565/566 document metadata, URL, local path, SHA-256, extracted text and extraction status.
- `vin_pattern_rules`: source-backed position/code rules with manufacturer, WMI, vehicle category, model/year scope, evidence and review status.
- `vin_research_sources`: source registry with publisher, geographic scope, data scope and access/licensing notes.
- `vin_collection_runs`: collector run status, counts and errors.

## VIN rule semantics
- Position numbers are 1-based and inclusive (1–17).
- WMI, vehicle category, model and model-year range restrict applicability.
- `field_name` describes the decoded field; `code_value` and `decoded_value` describe the documented code.
- `match_pattern` stores a documented pattern when a fixed code is insufficient.
- `evidence_excerpt`, `document_id`, `source_name` and `source_url` preserve provenance.
- Status values: `needs_review`, `verified`, `rejected`.

WMI assignments and VDS/model decoding rules are different evidence types. Do not promote WMI into a model rule.
