import json, urllib.parse, urllib.request

BASE = "https://vpic.nhtsa.dot.gov/api/vehicles"

def get_json(url, params):
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + query, headers={"User-Agent":"GVIDB/2.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))

def decode_vin(vin, year=None):
    params = {"format":"json"}
    if year:
        params["modelyear"] = str(year)
    url = f"{BASE}/DecodeVinValuesExtended/{urllib.parse.quote(vin)}"
    payload = get_json(url, params)
    rows = payload.get("Results") or []
    return rows[0] if rows else {}

def decode_wmi(wmi):
    url = f"{BASE}/DecodeWMI/{urllib.parse.quote(wmi)}"
    payload = get_json(url, {"format":"json"})
    return payload.get("Results") or []
