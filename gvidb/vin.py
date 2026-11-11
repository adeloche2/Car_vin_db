import re

FORBIDDEN = set("IOQ")
TRANSLIT = {**{str(i):i for i in range(10)},
 **dict(zip("ABCDEFGH",range(1,9))),
 **dict(zip("JKLMN",range(1,6))),
 **dict(zip("PR",(7,9))),
 **dict(zip("STUVWXYZ",range(2,10)))}
WEIGHTS = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2]
YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY123456789"

def normalize(v):
    return re.sub(r"[\\s-]","",(v or "").upper())

def validate(v):
    v = normalize(v)
    errors = []
    if not v: errors.append("لم تدخل أي خانة.")
    if len(v) > 17: errors.append("VIN أطول من 17 خانة.")
    if any(ch in FORBIDDEN for ch in v):
        errors.append("VIN القياسي لا يستخدم الأحرف I وO وQ.")
    if not re.fullmatch(r"[A-HJ-NPR-Z0-9]*",v):
        errors.append("توجد رموز أو أحرف غير مسموحة في VIN.")
    if len(v) < 17: errors.append(f"الرقم غير مكتمل: أدخل {17-len(v)} خانة إضافية.")
    return {"vin":v,"length":len(v),"valid_shape":len(v)==17 and not errors,"errors":errors}

def check_digit(v):
    v = normalize(v)
    if len(v) != 17 or not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}",v):
        return {"status":"not_checked","explanation":"لا يمكن فحص خانة التحقق قبل اكتمال VIN."}
    total = sum(TRANSLIT[ch] * w for ch,w in zip(v,WEIGHTS))
    rem = total % 11
    expected = "X" if rem == 10 else str(rem)
    return {"status":"pass" if expected == v[8] else "mismatch",
            "expected":expected,"actual":v[8],
            "explanation":"فحص خانة التحقق وفق الخوارزمية الأمريكية. اختلافها لا يثبت وحده أن VIN مزيف؛ قد تختلف قواعد بعض الأسواق."}

def year_candidates(code):
    if not code or code not in YEAR_CODES:
        return []
    idx = YEAR_CODES.index(code)
    return [start + idx for start in (1980,2000,2020) if 1980 <= start + idx <= 2049]

def positions(v):
    v = normalize(v)
    return {
      "wmi":v[:3] if len(v)>=3 else None,
      "vds":v[3:8] if len(v)>=8 else None,
      "check_digit":v[8] if len(v)>=9 else None,
      "year_code":v[9] if len(v)>=10 else None,
      "plant_code":v[10] if len(v)>=11 else None,
      "serial":v[11:17] if len(v)>=17 else None
    }
