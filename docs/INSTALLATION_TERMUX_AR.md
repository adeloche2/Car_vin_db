# تثبيت GVIDB على Termux

## المتطلبات
```bash
pkg update && pkg upgrade
pkg install python git
```

## تنزيل المشروع
```bash
git clone https://github.com/adeloche2/Car_vin_db.git
cd Car_vin_db
```

## إنشاء البيئة وتثبيت Flask
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## تشغيل التطبيق
```bash
python app.py
```
افتح http://127.0.0.1:8000 في متصفح الهاتف. ينشئ التطبيق قاعدة SQLite تلقائيًا في data/GVIDB.sqlite.

## استيراد كتالوج المركبات
من واجهة «كتالوج الموديلات» اضغط «تنزيل واستيراد كتالوج VehiclesDB»، أو نفّذ:
```bash
python -c "from gvidb.catalog import import_catalog; print(import_catalog())"
```
يتطلب ذلك اتصالًا بالإنترنت.

## جمع بيانات VIN/WMI
```bash
python -m gvidb.vin_research collect --with-wmi
python -m gvidb.vin_research download-docs --limit 100
python -m gvidb.vin_research stats
```

## ملاحظات
- احتفظ بنسخة احتياطية من data/GVIDB.sqlite.
- لا ترفع قاعدة البيانات المحلية إلى GitHub؛ المستودع يتجاهلها.
- نجاح جمع WMI لا يعني معرفة الطراز.
- لا تعتبر وثيقة VIN قاعدة فك مؤكدة قبل استخراج جداولها ومراجعتها.
- عند فشل NHTSA أعد المحاولة لاحقًا واحتفظ برسالة الخطأ.
