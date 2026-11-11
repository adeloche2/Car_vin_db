"""Import source-backed VIN rules from JSON. Positions are 1-based."""
import json
from pathlib import Path
from gvidb.db import connect
from gvidb.vin_research import init_research_db, now

ALLOWED_STATUS = {"needs_review","verified","rejected"}

def import_rules(path):
    init_research_db()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    count = 0
    with connect() as c:
        for rule in data.get("rules", []):
            start = int(rule["vin_position_start"])
            end = int(rule["vin_position_end"])
            if not (1 <= start <= end <= 17):
                raise ValueError(f"Invalid VIN positions: {start}-{end}")
            status = rule.get("verification_status","needs_review")
            if status not in ALLOWED_STATUS:
                raise ValueError(f"Invalid verification_status: {status}")
            c.execute("""INSERT INTO vin_pattern_rules
              (manufacturer_name,wmi,vehicle_category,model_name,model_year_from,model_year_to,
               vin_position_start,vin_position_end,field_name,code_value,decoded_value,match_pattern,
               rule_type,confidence,verification_status,evidence_excerpt,source_name,source_url,notes,created_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (rule["manufacturer_name"],rule.get("wmi"),rule.get("vehicle_category"),rule.get("model_name"),
               rule.get("model_year_from"),rule.get("model_year_to"),start,end,rule["field_name"],
               rule.get("code_value"),rule.get("decoded_value"),rule.get("match_pattern"),
               rule.get("rule_type","position_code"),rule.get("confidence","unverified"),status,
               rule.get("evidence_excerpt"),rule.get("source_name","User-reviewed source"),
               rule["source_url"],rule.get("notes"),now()))
            count += 1
    return count
