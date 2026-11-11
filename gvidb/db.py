import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "GVIDB.sqlite"

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS makes (
 id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT NOT NULL,
 kind TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'VehiclesDB',
 UNIQUE(slug,kind)
);
CREATE TABLE IF NOT EXISTS vehicle_models (
 id INTEGER PRIMARY KEY, model_slug TEXT NOT NULL, make_slug TEXT NOT NULL,
 make_name TEXT NOT NULL, model_name TEXT NOT NULL, kind TEXT NOT NULL,
 body_types TEXT, countries TEXT, regions TEXT, aliases TEXT, former_ids TEXT,
 registration_years TEXT, raw_json TEXT NOT NULL,
 source TEXT NOT NULL DEFAULT 'VehiclesDB', source_version TEXT,
 UNIQUE(kind,make_slug,model_slug)
);
CREATE INDEX IF NOT EXISTS idx_models_make ON vehicle_models(make_slug,kind);
CREATE INDEX IF NOT EXISTS idx_models_name ON vehicle_models(model_name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_models_make_name ON vehicle_models(make_name COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS wmi_codes (
 id INTEGER PRIMARY KEY, wmi TEXT NOT NULL, manufacturer TEXT, country TEXT,
 vehicle_type TEXT, source TEXT NOT NULL, source_url TEXT,
 verified INTEGER NOT NULL DEFAULT 0, notes TEXT,
 UNIQUE(wmi,source,manufacturer)
);
CREATE INDEX IF NOT EXISTS idx_wmi ON wmi_codes(wmi);
CREATE TABLE IF NOT EXISTS data_sources (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, version TEXT, url TEXT,
 license TEXT, imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
 record_count INTEGER, notes TEXT
);
CREATE TABLE IF NOT EXISTS vin_decodes (
 id INTEGER PRIMARY KEY, vin TEXT NOT NULL, source TEXT NOT NULL,
 result_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_vin_decodes_vin ON vin_decodes(vin);
CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with connect() as c:
        c.executescript(SCHEMA)
        c.execute("""INSERT OR IGNORE INTO data_sources(name,version,url,license,notes)
          VALUES(?,?,?,?,?)""",
          ("VehiclesDB","not imported","https://github.com/vehiclesdb/vehiclesdb",
           "CC BY 4.0","Requires visible attribution: Vehicle data by VehiclesDB"))
