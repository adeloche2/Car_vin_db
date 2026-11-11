from flask import Flask, jsonify, request, send_from_directory
from gvidb.db import init_db, connect
from gvidb.engine import progressive_search, decode, catalog_models
from gvidb.catalog import import_catalog

app = Flask(__name__, static_folder="static")
init_db()

@app.get("/")
def index():
    return send_from_directory("static", "index.html")

@app.get("/api/health")
def health():
    with connect() as db:
        count = db.execute("SELECT COUNT(*) FROM vehicle_models").fetchone()[0]
        version = db.execute("SELECT value FROM app_meta WHERE key='catalog_version'").fetchone()
    return jsonify({"status":"ok","app":"GVIDB","version":"2.0","catalog_models":count,
                    "catalog_version":version["value"] if version else None,"catalog_ready":count > 0})

@app.post("/api/catalog/import")
def catalog_import():
    try:
        return jsonify(import_catalog())
    except Exception as exc:
        return jsonify({"error":str(exc),"message":"فشل تنزيل أو استيراد الكتالوج. تحقق من الإنترنت ثم أعد المحاولة."}), 502

@app.get("/api/search")
def search():
    try:
        return jsonify(progressive_search(request.args.get("q","")))
    except Exception as exc:
        return jsonify({"error":str(exc)}), 500

@app.get("/api/decode/<path:vin>")
def vin_decode_path(vin):
    return jsonify(decode(vin, request.args.get("modelyear")))

@app.get("/api/catalog/models")
def models():
    query = request.args.get("q","").strip()
    if len(query) < 2:
        return jsonify({"message":"أدخل حرفين على الأقل للبحث في كتالوج الموديلات.","results":[]})
    return jsonify({"results":catalog_models(query,100)})

@app.get("/api/catalog/stats")
def stats():
    with connect() as db:
        count = db.execute("SELECT COUNT(*) FROM vehicle_models").fetchone()[0]
        makes = db.execute("SELECT COUNT(*) FROM makes").fetchone()[0]
        kinds = [dict(row) for row in db.execute(
            "SELECT kind,COUNT(*) AS count FROM vehicle_models GROUP BY kind ORDER BY kind")]
        version = db.execute("SELECT value FROM app_meta WHERE key='catalog_version'").fetchone()
    return jsonify({"models":count,"makes":makes,"by_kind":kinds,
                    "version":version["value"] if version else None})

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8000,debug=False)
