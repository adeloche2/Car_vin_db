# دليل جمع قاعدة أنماط VIN في GVIDB

## الهدف
جمع سجلات المصنعين وأكواد WMI ووثائق فك VIN التي تصدرها الشركات، ثم تحويل الجداول المنشورة إلى قواعد موضعية قابلة للبحث. لا يُستنتج الطراز من WMI وحده.

## جمع بيانات NHTSA
```bash
python -m gvidb.vin_research collect --with-wmi
```
تجمع العملية سجلات المصنعين، وأكواد WMI، وفهارس وثائق 49 CFR Part 565 الخاصة بتعريف VIN، ووثائق Part 566 الداعمة لتعريف المصنعين.

## تنزيل الوثائق
ابدأ بعينة:
```bash
python -m gvidb.vin_research download-docs --limit 100
```
ولتنزيل كل وثائق Part 565 المتاحة:
```bash
python -m gvidb.vin_research download-docs
```
استخراج نص PDF اختياري:
```bash
pip install -r requirements-research.txt
python -m gvidb.vin_research download-docs --limit 100
```

## فحص النتائج
```bash
python -m gvidb.vin_research stats
```

## تحويل الوثيقة إلى قاعدة
- راجع وثيقة الشركة الأصلية.
- تحقق من WMI ونوع المركبة ونطاق سنوات الموديل.
- سجّل مواضع VIN بالأرقام من 1 إلى 17.
- أدخل الرمز ومعناه ومقتطف الدليل ورابط المصدر في ملف مبني على vin_rules_template.json.
- استورد القواعد:
```bash
python -c "from gvidb.vin_rules import import_rules; print(import_rules('vin_rules.json'))"
```
تبقى القاعدة needs_review حتى التحقق اليدوي. لا تجعلها verified لمجرد أن النمط يبدو منطقيًا.

## حدود التغطية
NHTSA مصدر رسمي مهم لكنه يعكس أساسًا بيانات المركبات والمصنعين المقدمة للسوق الأمريكية. وجود شركة أجنبية في القاعدة لا يعني تغطية كل أسواقها أو كل طرازاتها عالميًا. الوثائق التي تم تنزيلها ليست تلقائيًا قواعد فك مؤكدة. قد تحتاج ملفات PDF الممسوحة إلى OCR ومراجعة بشرية.
