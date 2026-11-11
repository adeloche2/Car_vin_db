"""Source-preserving NHTSA manufacturer, WMI and VIN-document collector."""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from gvidb.db import connect, ROOT, init_db

API = "https://vpic.nhtsa.dot.gov/api/vehicles"
SOURCE = "NHTSA vPIC / MID"
SOURCE_URL = "https://vpic.nhtsa.dot.gov/api/"
DATA_DIR = ROOT / "data" / "vin_sources" / "nhtsa"
DOC_DIR = DATA_DIR / "documents"
UA = "GVIDB-VIN-Research/1.0"

SCHEMA = """
CREATE TABLE IF NOT EXISTS vin_manufacturers (
 id INTEGER PRIMARY KEY, source_key TEXT NOT NULL UNIQUE,
 source_manufacturer_id INTEGER, manufacturer_name TEXT NOT NULL,
 common_name TEXT, manufacturer_type TEXT, country TEXT,
 source_scope TEXT NOT NULL DEFAULT 'US-regulatory-submissions',
 raw_json TEXT NOT NULL, source_url TEXT NOT NULL,
 first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, wmi_checked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_vin_mfr_name ON vin_manufacturers(manufacturer_name COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS vin_wmi_registry (
 id INTEGER PRIMARY KEY, wmi TEXT NOT NULL, manufacturer_id INTEGER,
 manufacturer_name TEXT, common_name TEXT, vehicle_type TEXT, country TEXT,
 source_scope TEXT NOT NULL DEFAULT 'US-regulatory-submissions',
 source_name TEXT NOT NULL, source_url TEXT NOT NULL, raw_json TEXT NOT NULL,
 collected_at TEXT NOT NULL, UNIQUE(wmi,source_name,manufacturer_id,vehicle_type)
);
CREATE INDEX IF NOT EXISTS idx_vin_wmi_code ON vin_wmi_registry(wmi);
CREATE TABLE IF NOT EXISTS vin_pattern_documents (
 id INTEGER PRIMARY KEY, source_document_key TEXT NOT NULL UNIQUE,
 manufacturer_id INTEGER, manufacturer_name TEXT, document_type TEXT NOT NULL,
 document_title TEXT, letter_date TEXT, model_year_from TEXT, model_year_to TEXT,
 document_url TEXT NOT NULL, local_path TEXT, sha256 TEXT, extracted_text TEXT,
 extraction_status TEXT NOT NULL DEFAULT 'metadata_only',
 source_name TEXT NOT NULL,
 source_scope TEXT NOT NULL DEFAULT 'US-regulatory-submissions',
 raw_json TEXT NOT NULL, collected_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vin_docs_mfr ON vin_pattern_documents(manufacturer_name COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS vin_pattern_rules (
 id INTEGER PRIMARY KEY, manufacturer_name TEXT NOT NULL, wmi TEXT,
 vehicle_category TEXT, model_name TEXT, model_year_from INTEGER, model_year_to INTEGER,
 vin_position_start INTEGER NOT NULL, vin_position_end INTEGER NOT NULL,
 field_name TEXT NOT NULL, code_value TEXT, decoded_value TEXT, match_pattern TEXT,
 rule_type TEXT NOT NULL DEFAULT 'position_code',
 confidence TEXT NOT NULL DEFAULT 'unverified',
 verification_status TEXT NOT NULL DEFAULT 'needs_review',
 evidence_excerpt TEXT, document_id INTEGER, source_name TEXT NOT NULL,
 source_url TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL,
 FOREIGN KEY(document_id) REFERENCES vin_pattern_documents(id)
);
CREATE INDEX IF NOT EXISTS idx_vin_rules_lookup ON vin_pattern_rules(wmi,vin_position_start,vin_position_end);
CREATE TABLE IF NOT EXISTS vin_collection_runs (
 id INTEGER PRIMARY KEY, source_name TEXT NOT NULL, started_at TEXT NOT NULL,
 finished_at TEXT, status TEXT NOT NULL, manufacturers_seen INTEGER DEFAULT 0,
 wmis_seen INTEGER DEFAULT 0, documents_seen INTEGER DEFAULT 0,
 errors INTEGER DEFAULT 0, notes TEXT
);
CREATE TABLE IF NOT EXISTS vin_research_sources (
 id INTEGER PRIMARY KEY, source_name TEXT NOT NULL UNIQUE, publisher TEXT,
 source_url TEXT NOT NULL, geographic_scope TEXT, data_scope TEXT,
 license_or_access TEXT, source_role TEXT, notes TEXT, last_checked_at TEXT
);
"""

SEEDS = [
 ("ISO 3779:2009","ISO","https://www.iso.org/standard/52200.html","Global","VIN content and structure","Standard preview; full text may require purchase","standard","Defines VIN structure and WMI/VDS/VIS concepts; not manufacturer code tables."),
 ("ISO 3780:2009","ISO","https://www.iso.org/standard/45844.html","Global","WMI structure","Standard preview; full text may require purchase","standard","Defines WMI framework; not a live exhaustive allocation register."),
 ("SAE J1044","SAE International","https://saemobilus.sae.org/standards/j1044_202501-world-manufacturer-identifier","Global","WMI assignment procedure","Standard access may require purchase","standard","WMI assignment procedure reference."),
 ("NHTSA vPIC / MID","US NHTSA",SOURCE_URL,"Primarily US regulatory submissions","Manufacturer VIN data, WMI, Part 565/566 documents","Public API and public documents","official_dataset","Primary source for submitted manufacturer patterns; not a global complete register."),
 ("EU Regulation 19/2011","European Union","https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32011R0019","European Union","VIN composition and type approval","Public legal text","regulation","Regional VIN requirements."),
 ("Australian Government VIN guidance","Australian Government","https://www.infrastructure.gov.au/infrastructure-transport-vehicles/vehicles/importing-vehicle/vin","Australia","VIN/WMI guidance","Public government guidance","guidance","Corroborating source, not a VDS database."),
 ("Bureau of Indian Standards WMI","BIS","https://www.bis.gov.in/standards/world-manufacturer-identifier/","India","WMI coordination","Public guidance; assignment service may require application","authority","National WMI coordination reference.")
]

def now():
    return datetime.now(timezone.utc).isoformat()

def init_research_db():
    init_db()
    with connect() as db:
        db.executescript(SCHEMA)
        for name,publisher,url,geo,scope,access,role,notes in SEEDS:
            db.execute("""INSERT INTO vin_research_sources
              (source_name,publisher,source_url,geographic_scope,data_scope,license_or_access,source_role,notes,last_checked_at)
              VALUES(?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(source_name) DO UPDATE SET source_url=excluded.source_url,
              notes=excluded.notes,last_checked_at=excluded.last_checked_at""",
              (name,publisher,url,geo,scope,access,role,notes,now()))
        db.execute("""INSERT OR IGNORE INTO data_sources(name,version,url,license,notes)
          VALUES(?,?,?,?,?)""",(SOURCE,"vPIC API",SOURCE_URL,"Public government data",
          "NHTSA manufacturer-submitted records; primarily US regulatory-market coverage."))

def api_get(endpoint, params=None, retries=5):
    query = urllib.parse.urlencode({**(params or {}),"format":"json"})
    url = f"{API}/{endpoint}?{query}"
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8-sig"))
            return payload, url
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429,500,502,503,504): raise
        except Exception as exc:
            last_error = exc
        time.sleep(min(30,2**attempt + 0.5))
    raise RuntimeError(f"API request failed: {url}: {last_error}")

def rows(payload):
    result = payload.get("Results") or payload.get("results") or []
    return result if isinstance(result,list) else []

def pick(record,*keys):
    lower = {str(k).lower():v for k,v in record.items()}
    for key in keys:
        value = record.get(key,lower.get(key.lower()))
        if value not in (None,""): return value
    return None

def collect_manufacturers(delay):
    page = total = errors = 0
    while True:
        page += 1
        payload,url = api_get("GetAllManufacturers",{"page":page})
        batch = rows(payload)
        if not batch: break
        for item in batch:
            try:
                mid = pick(item,"Mfr_ID","ManufacturerId","ManufacturerID","ID")
                name = str(pick(item,"Mfr_Name","ManufacturerName","Name","Manufacturer") or "Unknown manufacturer")
                source_key = str(mid if mid is not None else name.strip().lower())
                stamp = now()
                with connect() as db:
                    db.execute("""INSERT INTO vin_manufacturers
                      (source_key,source_manufacturer_id,manufacturer_name,common_name,manufacturer_type,country,
                       raw_json,source_url,first_seen_at,last_seen_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?)
                      ON CONFLICT(source_key) DO UPDATE SET manufacturer_name=excluded.manufacturer_name,
                      common_name=excluded.common_name,manufacturer_type=excluded.manufacturer_type,
                      country=excluded.country,raw_json=excluded.raw_json,last_seen_at=excluded.last_seen_at""",
                      (source_key,int(mid) if str(mid).isdigit() else None,name,
                       pick(item,"Mfr_CommonName","CommonName"),pick(item,"Mfr_Type","ManufacturerType"),
                       pick(item,"Country","Mfr_Country"),json.dumps(item,ensure_ascii=False),
                       url,stamp,stamp))
                total += 1
            except Exception as exc:
                errors += 1
                print(f"[manufacturer] {exc}",file=sys.stderr)
        print(f"Manufacturers page {page}: {len(batch)} records; stored {total}")
        if len(batch) < 100: break
        time.sleep(delay)
    return total,errors

def collect_wmis(delay):
    with connect() as db:
        manufacturers = db.execute("""SELECT source_manufacturer_id,manufacturer_name
          FROM vin_manufacturers WHERE source_manufacturer_id IS NOT NULL AND wmi_checked_at IS NULL
          ORDER BY source_manufacturer_id""").fetchall()
    total = errors = 0
    for index,manufacturer in enumerate(manufacturers,1):
        mid,name = manufacturer
        try:
            payload,url = api_get(f"GetWMIsForManufacturer/{mid}")
            for item in rows(payload):
                wmi = pick(item,"WMI","Wmi","WorldManufacturerIdentifier")
                if not wmi: continue
                with connect() as db:
                    db.execute("""INSERT INTO vin_wmi_registry
                      (wmi,manufacturer_id,manufacturer_name,common_name,vehicle_type,country,
                       source_name,source_url,raw_json,collected_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?)
                      ON CONFLICT(wmi,source_name,manufacturer_id,vehicle_type) DO UPDATE SET
                      manufacturer_name=excluded.manufacturer_name,common_name=excluded.common_name,
                      country=excluded.country,raw_json=excluded.raw_json,collected_at=excluded.collected_at""",
                      (str(wmi).upper(),mid,pick(item,"ManufacturerName","Manufacturer","Mfr_Name") or name,
                       pick(item,"CommonName","Mfr_CommonName"),pick(item,"VehicleType","Vehicle_Type"),
                       pick(item,"Country","CountryName"),SOURCE,url,json.dumps(item,ensure_ascii=False),now()))
                total += 1
            with connect() as db:
                db.execute("UPDATE vin_manufacturers SET wmi_checked_at=? WHERE source_manufacturer_id=?",(now(),mid))
        except Exception as exc:
            errors += 1
            print(f"[WMI {index}/{len(manufacturers)}] {name}: {exc}",file=sys.stderr)
        if index % 25 == 0: print(f"WMI progress {index}/{len(manufacturers)}; codes={total}; errors={errors}")
        time.sleep(delay)
    return total,errors

def collect_parts(doc_type,delay):
    page = total = errors = 0
    while True:
        page += 1
        payload,url = api_get("GetParts",{"type":doc_type,"page":page})
        batch = rows(payload)
        if not batch: break
        for item in batch:
            try:
                mid = pick(item,"ManufacturerId","ManufacturerID","Mfr_ID")
                name = str(pick(item,"ManufacturerName","Manufacturer","Name") or "Unknown manufacturer")
                links = []
                doc_url = pick(item,"URL","Url","DocumentURL","DocumentUrl")
                cover = pick(item,"CoverLetterURL","CoverLetterUrl")
                if doc_url: links.append((str(doc_url),pick(item,"Name","Title")))
                if cover and cover != doc_url: links.append((str(cover),"Cover letter"))
                for link,title in links:
                    key = hashlib.sha256((str(doc_type)+"|"+link).encode()).hexdigest()
                    with connect() as db:
                        db.execute("""INSERT INTO vin_pattern_documents
                          (source_document_key,manufacturer_id,manufacturer_name,document_type,document_title,
                           letter_date,model_year_from,model_year_to,document_url,source_name,raw_json,collected_at)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                          ON CONFLICT(source_document_key) DO UPDATE SET manufacturer_name=excluded.manufacturer_name,
                          document_title=excluded.document_title,raw_json=excluded.raw_json,collected_at=excluded.collected_at""",
                          (key,int(mid) if str(mid).isdigit() else None,name,str(doc_type),title,
                           pick(item,"LetterDate"),pick(item,"ModelYearFrom"),pick(item,"ModelYearTo"),
                           link,SOURCE,json.dumps(item,ensure_ascii=False),now()))
                    total += 1
            except Exception as exc:
                errors += 1
                print(f"[Part {doc_type}] {exc}",file=sys.stderr)
        print(f"Part {doc_type} page {page}: {len(batch)} rows; stored {total}")
        if len(batch) < 1000: break
        time.sleep(delay)
    return total,errors

def collect_all(with_wmi=True,delay=0.35):
    init_research_db()
    started = now()
    with connect() as db:
        run_id = db.execute("INSERT INTO vin_collection_runs(source_name,started_at,status) VALUES(?,?,?)",
                            (SOURCE,started,"running")).lastrowid
    errors = 0
    try:
        manufacturers,e = collect_manufacturers(delay); errors += e
        wmis = 0
        if with_wmi:
            wmis,e = collect_wmis(delay); errors += e
        documents = 0
        for doc_type in (565,566):
            count,e = collect_parts(doc_type,delay); documents += count; errors += e
        status = "completed_with_errors" if errors else "completed"
        note = "NHTSA is primarily US regulatory-submission coverage; not a complete global WMI/VIN-pattern register. Documents are not auto-promoted to verified rules."
        with connect() as db:
            db.execute("""UPDATE vin_collection_runs SET finished_at=?,status=?,manufacturers_seen=?,
              wmis_seen=?,documents_seen=?,errors=?,notes=? WHERE id=?""",
              (now(),status,manufacturers,wmis,documents,errors,note,run_id))
        return {"run_id":run_id,"status":status,"manufacturers":manufacturers,
                "wmis":wmis,"documents":documents,"errors":errors}
    except Exception as exc:
        with connect() as db:
            db.execute("UPDATE vin_collection_runs SET finished_at=?,status='failed',errors=errors+1,notes=? WHERE id=?",
                       (now(),str(exc),run_id))
        raise

def download_documents(limit=0,delay=0.4,extract=True):
    init_research_db()
    DOC_DIR.mkdir(parents=True,exist_ok=True)
    sql = """SELECT id,source_document_key,manufacturer_name,document_type,document_title,document_url
      FROM vin_pattern_documents WHERE document_type='565' AND local_path IS NULL
      ORDER BY letter_date DESC,id DESC"""
    if limit > 0: sql += f" LIMIT {int(limit)}"
    with connect() as db: documents = db.execute(sql).fetchall()
    downloaded = failed = extracted = 0
    for index,row in enumerate(documents,1):
        doc_id,key,name,kind,title,url = row
        safe = re.sub(r"[^A-Za-z0-9._-]+","_",name)[:60] or "manufacturer"
        path = DOC_DIR / f"{safe}_{doc_id}_{key[:10]}.pdf"
        try:
            req = urllib.request.Request(url,headers={"User-Agent":UA})
            temp = path.with_suffix(".part")
            with urllib.request.urlopen(req,timeout=90) as response, open(temp,"wb") as output:
                while True:
                    block = response.read(256*1024)
                    if not block: break
                    output.write(block)
            if not temp.read_bytes()[:5] == b"%PDF-":
                path = path.with_suffix(".bin")
            temp.replace(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            text_value = None
            status = "downloaded"
            if extract and path.suffix == ".pdf":
                try:
                    from pypdf import PdfReader
                    text_value = "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
                    status = "text_extracted" if text_value.strip() else "downloaded_no_text"
                    if text_value.strip(): extracted += 1
                except ImportError:
                    status = "downloaded_install_pypdf_for_text"
                except Exception as exc:
                    status = "downloaded_extract_error:" + str(exc)[:150]
            with connect() as db:
                db.execute("""UPDATE vin_pattern_documents SET local_path=?,sha256=?,extracted_text=?,
                  extraction_status=? WHERE id=?""",
                  (str(path.relative_to(ROOT)),digest,text_value,status,doc_id))
            downloaded += 1
        except Exception as exc:
            failed += 1
            with connect() as db:
                db.execute("UPDATE vin_pattern_documents SET extraction_status=? WHERE id=?",
                           ("download_error:"+str(exc)[:150],doc_id))
            print(f"[download {index}/{len(documents)}] {name}: {exc}",file=sys.stderr)
        if index % 20 == 0: print(f"Documents {index}/{len(documents)}; downloaded={downloaded}; extracted={extracted}; failed={failed}")
        time.sleep(delay)
    return {"queued":len(documents),"downloaded":downloaded,"text_extracted":extracted,"failed":failed}

def show_stats():
    init_research_db()
    queries = {
      "manufacturers":"SELECT COUNT(*) FROM vin_manufacturers",
      "WMI records":"SELECT COUNT(*) FROM vin_wmi_registry",
      "distinct WMIs":"SELECT COUNT(DISTINCT wmi) FROM vin_wmi_registry",
      "Part 565 documents":"SELECT COUNT(*) FROM vin_pattern_documents WHERE document_type='565'",
      "Part 566 documents":"SELECT COUNT(*) FROM vin_pattern_documents WHERE document_type='566'",
      "downloaded documents":"SELECT COUNT(*) FROM vin_pattern_documents WHERE local_path IS NOT NULL",
      "extracted text documents":"SELECT COUNT(*) FROM vin_pattern_documents WHERE extracted_text IS NOT NULL AND length(extracted_text)>0",
      "verified rules":"SELECT COUNT(*) FROM vin_pattern_rules WHERE verification_status='verified'"
    }
    with connect() as db: result = {name:db.execute(sql).fetchone()[0] for name,sql in queries.items()}
    for name,count in result.items(): print(f"{name}: {count}")
    return result

def main():
    parser = argparse.ArgumentParser(description="GVIDB global VIN/WMI source collector")
    sub = parser.add_subparsers(dest="command",required=True)
    collect = sub.add_parser("collect")
    collect.add_argument("--with-wmi",action="store_true")
    collect.add_argument("--delay",type=float,default=0.35)
    download = sub.add_parser("download-docs")
    download.add_argument("--limit",type=int,default=0)
    download.add_argument("--delay",type=float,default=0.4)
    download.add_argument("--no-extract",action="store_true")
    sub.add_parser("stats")
    args = parser.parse_args()
    if args.command == "collect":
        print(json.dumps(collect_all(args.with_wmi,args.delay),ensure_ascii=False,indent=2))
    elif args.command == "download-docs":
        print(json.dumps(download_documents(args.limit,args.delay,not args.no_extract),ensure_ascii=False,indent=2))
    else:
        show_stats()

if __name__ == "__main__":
    main()
