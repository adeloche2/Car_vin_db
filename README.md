# GVIDB — Global Vehicle Identification Database

GVIDB is an offline-first vehicle catalogue and VIN/WMI research project. The target coverage is global and includes cars, motorcycles, mopeds, trucks, vans, buses and other vehicle classes.

**Status:** working Flask/SQLite application, VehiclesDB catalogue importer, NHTSA vPIC VIN/WMI lookup, and a source-preserving VIN/WMI research collector. A complete global corpus of manufacturer-specific VDS decoding rules is not yet available. See [Project status](docs/PROJECT_STATUS_AR.md).

## Product decisions

- Global collection scope; official and specialist technical sources.
- Maximum practical make/model catalogue coverage, retaining incomplete records and source provenance.
- VIN-only colours: never infer paint/interior colour from make, model or year.
- WMI identifies a manufacturer context; it does not identify a model by itself.
- Manufacturer-specific position/code rules require source documents, year scope and evidence. Imported rules default to `needs_review`.
- Local SQLite is the intended offline data store; online APIs are used for collection and optional lookup.

## Features

- Arabic RTL web interface (Flask) for progressive VIN entry, WMI lookup, VIN decode and model catalogue search.
- SQLite schema for makes, models, WMI, decode history, source registry and VIN research evidence.
- VehiclesDB 2026.11.3 CSV importer.
- NHTSA vPIC adapter for DecodeVinValuesExtended and DecodeWMI.
- VIN shape validation, US check-digit calculation, position parsing and year-code candidates.
- NHTSA manufacturer/WMI/Part 565/566 document metadata collector.
- Document download with SHA-256 and optional PDF text extraction.
- JSON importer for manually reviewed manufacturer-specific rules.

## Quick start (Termux)

```bash
pkg update
pkg install python git
git clone https://github.com/adeloche2/Car_vin_db.git
cd Car_vin_db
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8000. Detailed Arabic steps: [Termux guide](docs/INSTALLATION_TERMUX_AR.md).

## Import the vehicle catalogue

```bash
python -c "from gvidb.catalog import import_catalog; print(import_catalog())"
```

Or use the catalogue tab in the UI. The importer downloads the pinned VehiclesDB 2026.11.3 release. The user's Termux import was verified at **16,032 models**, **1,261 makes rows**, **970 distinct make names/slugs**, and **zero duplicate (kind, make_slug, model_slug) groups**. Per-kind counts: 5,997 cars; 6,196 motorcycles; 1,459 mopeds; 1,159 trucks; 795 vans; 426 buses.

The local SQLite database and downloaded catalogue files are intentionally excluded from Git. Each installation creates its own database and imports the dataset. VehiclesDB requires CC BY 4.0 attribution: **Vehicle data by VehiclesDB** — https://vehiclesdb.com.

## Collect VIN/WMI research data

```bash
python -m gvidb.vin_research collect --with-wmi
python -m gvidb.vin_research download-docs --limit 100
python -m gvidb.vin_research stats
```

Optional PDF extraction support:

```bash
pip install -r requirements-research.txt
python -m gvidb.vin_research download-docs --limit 100
```

See [VIN research pipeline](docs/VIN_RESEARCH_PIPELINE.md), [data model](docs/DATA_MODEL.md), [sources and coverage](docs/DATA_SOURCES.md), and [architecture](docs/ARCHITECTURE.md).

## Important limitations

NHTSA vPIC is a high-value official source, but its coverage primarily reflects manufacturers and vehicles submitted for the US regulatory market. It is not a complete global WMI or VIN-pattern register. Downloading a Part 565 document does not mean its tables have been extracted or verified. GVIDB does not yet decode every manufacturer's VDS/model codes locally. Unknown results must not be treated as proof that a VIN is invalid.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py gvidb tests
```

## Repository map

- `gvidb/`: SQLite, catalogue, VIN primitives, source adapter, decode engine and research collector.
- `static/`: Arabic RTL interface.
- `docs/`: architecture, schema, source provenance, installation, research workflow, status and roadmap.
- `tests/`: unit tests.
- `data/`: generated local data; ignored by Git.

See [Roadmap](docs/ROADMAP.md) and [Changelog](docs/CHANGELOG.md).
