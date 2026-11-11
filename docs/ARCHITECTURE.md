# GVIDB architecture

## Runtime components
- `app.py`: Flask application and JSON endpoints.
- `static/`: Arabic RTL interface.
- `gvidb/db.py`: SQLite schema, database path and connections.
- `gvidb/catalog.py`: pinned VehiclesDB downloader/importer.
- `gvidb/vin.py`: VIN normalization, shape validation, US check digit, positions and year candidates.
- `gvidb/sources.py`: NHTSA vPIC online lookup adapter.
- `gvidb/engine.py`: progressive search, VIN decode orchestration and catalogue search.
- `gvidb/vin_research.py`: manufacturer/WMI/document collector and downloader.
- `gvidb/vin_rules.py`: importer for source-reviewed VIN rules.

## Data flow
1. Partial VIN input triggers progressive lookup. At three characters, the app can query WMI.
2. A complete VIN is shape-checked and passed to NHTSA vPIC when online.
3. Catalogue search is separate; a model's presence in VehiclesDB does not prove that a VIN belongs to it.
4. The research collector preserves manufacturer records, WMI assignments, Part 565/566 metadata and downloaded source documents.
5. Researchers transcribe position/code tables into JSON and import them with source evidence.
6. A future offline matcher must use verified rules and return the matching rule and evidence trail.

## Invariants
- WMI is not a model decoder.
- Position rules can vary by manufacturer, vehicle type, market and model year.
- The check-digit helper implements the US algorithm; it is not a universal rejection rule.
- Year codes repeat; do not assert a unique year without sufficient context.
- Never infer vehicle colour from model metadata.
- Missing source data is not proof of an invalid VIN.

## HTTP endpoints
| Method | Path | Function |
|---|---|---|
| GET | `/` | Arabic web UI |
| GET | `/api/health` | Runtime/catalogue status |
| POST | `/api/catalog/import` | Import VehiclesDB |
| GET | `/api/search?q=...` | Progressive VIN/WMI lookup |
| GET | `/api/decode/<vin>` | Online VIN decode |
| GET | `/api/catalog/models?q=...` | Local model search |
| GET | `/api/catalog/stats` | Catalogue totals |

Local databases, CSVs and source documents are generated data and ignored by Git.
