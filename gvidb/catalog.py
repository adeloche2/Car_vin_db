import csv, hashlib, json, urllib.request
from datetime import datetime, timezone
from gvidb.db import connect, ROOT

VERSION = "2026.11.3"
CSV_URL = f"https://github.com/vehiclesdb/vehiclesdb/releases/download/v{VERSION}/vehicles.csv"
ATTR_URL = f"https://github.com/vehiclesdb/vehiclesdb/releases/download/v{VERSION}/ATTRIBUTION.md"
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "vehiclesdb.csv"

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent":"GVIDB/2.0"})
    tmp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(req, timeout=90) as response, open(tmp, "wb") as f:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            f.write(block)
    tmp.replace(path)

def count_makes():
    with connect() as c:
        return c.execute("SELECT COUNT(*) FROM makes").fetchone()[0]

def import_catalog():
    DATA_DIR.mkdir(exist_ok=True)
    download(CSV_URL, CSV_PATH)
    try:
        download(ATTR_URL, DATA_DIR / "VEHICLESDB_ATTRIBUTION.md")
    except Exception:
        pass
    required = {"kind","make_slug","make_name","model_slug","model_name"}
    rows = 0
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("CSV schema mismatch; missing: " + ", ".join(sorted(missing)))
        with connect() as c:
            c.execute("DELETE FROM vehicle_models")
            c.execute("DELETE FROM makes")
            for row in reader:
                raw = json.dumps(row, ensure_ascii=False, separators=(",",":"))
                val = lambda key: (row.get(key) or "").strip() or None
                c.execute("""INSERT OR REPLACE INTO vehicle_models
                  (model_slug,make_slug,make_name,model_name,kind,body_types,countries,regions,
                   aliases,former_ids,registration_years,raw_json,source,source_version)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (val("model_slug"),val("make_slug"),val("make_name"),val("model_name"),
                   val("kind"),val("body_types"),val("countries"),val("regions"),
                   val("aliases"),val("former_ids"),val("registration_years"),raw,
                   "VehiclesDB",VERSION))
                c.execute("INSERT OR IGNORE INTO makes(slug,name,kind) VALUES(?,?,?)",
                          (val("make_slug"),val("make_name"),val("kind")))
                rows += 1
            c.execute("""INSERT INTO data_sources(name,version,url,license,record_count,notes)
              VALUES(?,?,?,?,?,?)""",
              ("VehiclesDB",VERSION,CSV_URL,"CC BY 4.0",rows,
               "Vehicle data by VehiclesDB; see data/VEHICLESDB_ATTRIBUTION.md"))
            c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('catalog_version',?)",(VERSION,))
            c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('catalog_count',?)",(str(rows),))
            c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('catalog_imported_at',?)",
                      (datetime.now(timezone.utc).isoformat(),))
    return {"version":VERSION,"models_imported":rows,"makes_imported":count_makes(),
            "csv_sha256":hashlib.sha256(CSV_PATH.read_bytes()).hexdigest()}
