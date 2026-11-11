import json
from gvidb.db import connect
from gvidb.vin import normalize, validate, positions, check_digit, year_candidates
from gvidb.sources import decode_vin, decode_wmi

COLOR_KEYS = ("PaintColor","ExteriorColor","InteriorColor","Color","PaintCode",
              "ExteriorColorCode","InteriorColorCode")

def catalog_models(query, limit=25):
    pattern = f"%{query.strip()}%"
    with connect() as db:
        rows = db.execute("""SELECT kind,make_name,model_name,make_slug,model_slug,
          body_types,countries,registration_years,source_version
          FROM vehicle_models WHERE make_name LIKE ? OR model_name LIKE ?
          ORDER BY make_name,model_name LIMIT ?""",(pattern,pattern,limit)).fetchall()
    return [dict(row) for row in rows]

def decode(vin, model_year_hint=None):
    value = normalize(vin)
    validation = validate(value)
    if not validation["valid_shape"]:
        return {"status":"incomplete_or_invalid","validation":validation,
                "user_message":"لا يمكن فك الرقم قبل إدخال VIN كامل وصحيح البنية.",
                "next_step":"أكمل 17 خانة وتأكد من عدم وجود الأحرف I أو O أو Q."}
    pos = positions(value)
    with connect() as db:
        local_wmi = [dict(row) for row in db.execute(
          """SELECT wmi,manufacturer,country,vehicle_type,source,source_url,verified
             FROM wmi_codes WHERE wmi=?""",(pos["wmi"],)).fetchall()]
    try:
        external = decode_vin(value,model_year_hint)
        external_source, external_error = "NHTSA vPIC", None
    except Exception as exc:
        external, external_source, external_error = {}, None, str(exc)
    colors = {key:external.get(key) for key in COLOR_KEYS
              if external.get(key) not in (None,"","Not Applicable","Not Available","0")}
    year_value = external.get("ModelYear") or None
    make = external.get("Make") or None
    model = external.get("Model") or None
    plant = external.get("PlantCountry") or None
    status = "decoded" if (make or model or year_value) else ("source_unavailable" if external_error else "no_match")
    if status == "decoded":
        message, confidence = "أعاد مصدر فك VIN بيانات للمركبة. راجع مصدر كل حقل وحدود تغطيته.", "source_returned"
    elif external_error:
        message, confidence = "تعذر الوصول إلى خدمة فك VIN. تم إجراء الفحص المحلي فقط؛ لم يتم استنتاج الموديل.", "not_determined"
    else:
        message, confidence = "لم يُرجع المصدر بيانات تعريف كافية لهذا الرقم. هذا لا يعني بالضرورة أن VIN غير صحيح.", "not_determined"
    year_note = ("سنة الطراز كما أعادها مصدر فك VIN." if year_value else
                 "لم تُحدد سنة الطراز من المصدر. رمز الخانة العاشرة له دورات متكررة ولا يكفي وحده لإثبات سنة واحدة.")
    color_note = ("عُثر على حقول لون صريحة في استجابة المصدر." if colors else
                  "لم يُرجع مصدر VIN حقلاً صريحاً للون؛ لم يتم تخمين اللون من الموديل أو السنة.")
    result = {
      "status":status,"vin":value,"validation":validation,"check_digit":check_digit(value),
      "positions":pos,"wmi_local_matches":local_wmi,
      "vehicle":{"manufacturer":make,"model":model,"model_year":year_value,
        "vehicle_type":external.get("VehicleType") or None,"trim":external.get("Trim") or None,
        "series":external.get("Series") or None,"plant_country":plant,
        "plant_city":external.get("PlantCity") or None,
        "engine":external.get("EngineModel") or external.get("EngineConfiguration") or None,
        "fuel":external.get("FuelTypePrimary") or None,
        "transmission":external.get("TransmissionStyle") or None},
      "colors":{"available":bool(colors),"values":colors,"message":color_note},
      "year":{"value":year_value,"vin_code":pos["year_code"],
        "candidate_years":year_candidates(pos["year_code"]) if not year_value else [],
        "message":year_note},
      "source":{"name":external_source or "local validation only",
        "url":"https://vpic.nhtsa.dot.gov/api/","external_error":external_error},
      "confidence":confidence,"user_message":message,
      "limitations":["كتالوج VehiclesDB يسجل أسماء موديلات وأسواقًا، وليس أداة فك VIN.",
        "NHTSA vPIC تركز على بيانات الشركات والمركبات المرتبطة بالسوق الأمريكية.",
        "لا يُعرض لون إلا إذا أعاده مصدر VIN صراحةً."]
    }
    with connect() as db:
        db.execute("INSERT INTO vin_decodes(vin,source,result_json) VALUES(?,?,?)",
          (value,external_source or "local",json.dumps(result,ensure_ascii=False)))
    return result

def progressive_search(value):
    vin = normalize(value)
    if not vin: return {"stage":"empty","message":"أدخل رقم VIN للبدء."}
    if len(vin) > 17: return {"stage":"invalid","message":"عدد الخانات تجاوز 17."}
    if any(char in vin for char in "IOQ"):
        return {"stage":"invalid","message":"الأحرف I وO وQ غير مستخدمة في VIN القياسي."}
    pos = positions(vin)
    result = {"vin":vin,"length":len(vin),"positions":pos,"stage":"partial"}
    if len(vin) < 3:
        result["message"] = f"أدخل {3-len(vin)} خانات إضافية حتى نتمكن من البحث عن WMI."
        return result
    with connect() as db:
        local = [dict(row) for row in db.execute(
          "SELECT wmi,manufacturer,country,vehicle_type,source,verified FROM wmi_codes WHERE wmi=?",
          (vin[:3],)).fetchall()]
    external, error = [], None
    if len(vin) == 3:
        try: external = decode_wmi(vin[:3])
        except Exception as exc: error = str(exc)
    result["wmi"] = {"code":vin[:3],"local_matches":local,"external_matches":external,
                    "source":"NHTSA vPIC" if len(vin)==3 and external else "GVIDB local","error":error}
    if len(vin) < 8:
        result["message"] = "تم التعرف على WMI أو محاولة البحث عنه. أدخل حتى الخانة الثامنة لاستكمال VDS؛ لا يمكن تأكيد الموديل من WMI وحده."
    elif len(vin) < 17:
        result["message"] = "اكتملت خانات WMI وVDS جزئيًا. لا يمكن إثبات الموديل أو سنة الطراز دون قاعدة أنماط خاصة بالمصنّع أو VIN كامل."
    else:
        result["message"] = "اكتمل VIN. اضغط «فك VIN» لطلب بيانات المصدر."
    return result
