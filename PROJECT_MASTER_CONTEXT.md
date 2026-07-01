فكرة ممتازة. وصلنا إلى مرحلة أصبح فيها المشروع كبيرًا، ومن الأفضل أن يكون لديك **ملف مرجعي (Master Context)** تستطيع لصقه في أي محادثة جديدة مع ChatGPT أو Codex ليعرف المشروع بالكامل ويكمل منه مباشرة.

---

# 5ibr AdGuard Filter Toolkit

## Master Project Context (June 2026)

---

# 1. المشروع

اسم المشروع:

**5ibr AdGuard Filter Toolkit**

الهدف:

إنشاء مشروع احترافي مفتوح المصدر لإنتاج فلاتر AdGuard عالية الجودة تعتمد على قاعدة بيانات منظمة بدلاً من ملفات نصية فقط.

الفكرة الأساسية:

```
CSV Database
        ↓
Build System
        ↓
Filters
        ↓
Configs
        ↓
Releases
```

---

# 2. أهداف المشروع

المشروع ليس مجرد فلتر.

الهدف النهائي هو إنشاء:

* قاعدة بيانات Domains
* Build System
* Validation
* Reports
* CLI Toolkit
* GitHub Actions
* Releases
* Documentation
* Open Source Project

---

# 3. هيكل المشروع

```
fivebr.py

scripts/

builders/

database/

filters/

config/

releases/

tests/

docs/

.github/
```

---

# 4. قاعدة البيانات

الملف الرئيسي:

```
database/domains.csv
```

الأعمدة:

```
Domain
Vendor
Category
Filter
Confidence
Status
Source
Notes
```

مهم جداً:

قد يتم إضافة أعمدة مستقبلية.

لذلك لا يسمح لأي كود بحذف أعمدة غير معروفة.

Database API يحافظ على جميع Metadata.

---

# 5. Build System

الأمر:

```
python fivebr.py build
```

يبني:

```
filters/

config/

releases/
```

---

# 6. Validation

```
python fivebr.py validate
```

يفحص:

* duplicate rules
* syntax
* release consistency

---

# 7. Search

```
python fivebr.py search DOMAIN
```

يعرض:

Vendor

Category

Filter

Confidence

---

# 8. Statistics

```
python fivebr.py stats
```

يعرض:

عدد الدومينات

أفضل Vendors

أفضل Categories

---

# 9. Report

```
python fivebr.py report
```

ينشئ تقارير المشروع.

---

# 10. CRUD

تم الانتهاء بالكامل.

### Add

```
python fivebr.py add
```

Interactive

CLI

اختبارات كاملة

---

### Search

```
python fivebr.py search
```

---

### Update

```
python fivebr.py update
```

يدعم:

Interactive

CLI

Partial Update

يحافظ على Metadata

---

### Remove

```
python fivebr.py remove
```

يعرض البيانات

يطلب تأكيد

يحذف

---

# 11. CLI Architecture

تم إعادة هيكلته بالكامل.

fivebr.py أصبح:

Command Router فقط.

لا يحتوي على if/elif طويلة.

يعتمد على:

```
COMMANDS Registry
```

كل أمر عبارة عن Module مستقل.

جميع الأوامر تستخدم:

```
main(argv)
```

بدلاً من:

```
sys.argv
```

---

# 12. Command Modules

حالياً:

```
build.py

validate.py

stats.py

report.py

search.py

add.py

update.py

remove.py
```

---

# 13. Database Layer

```
scripts/database.py
```

يوفر:

```
load_database()

save_database()

search_domain()

add_domain()

update_domain()

remove_domain()

database_stats()
```

يحافظ على جميع أعمدة CSV.

---

# 14. Testing

يستخدم:

pytest

الحالة الحالية:

```
26 passed
```

تشمل:

CLI

Database

CRUD

Integration

Regression

Interactive

Build

Validation

---

# 15. GitHub Actions

يوجد Workflow كامل.

يقوم بـ:

```
Build

Validate

Pytest

Reports
```

---

# 16. Git Workflow

طريقة العمل المعتمدة:

```
Issue

↓

Feature Branch

↓

Development

↓

Tests

↓

Pull Request

↓

Merge

↓

Delete Branch

↓

git pull main
```

---

# 17. الفروع التي تم دمجها

تم دمج:

CLI Refactor

Remove Command

Update Command

في main.

---

# 18. أسلوب التطوير

أي ميزة جديدة يجب أن تمر بالمراحل:

1

Issue

2

Feature Branch

3

Implementation

4

Tests

5

Manual Testing

6

Pull Request

7

Review

8

Merge

---

# 19. ما تم تعلمه

تعلمنا عدم الاعتماد على الاختبارات فقط.

أي ميزة يجب اختبارها يدوياً.

كل مرة اكتشفنا Bugs لم تظهر في pytest.

---

# 20. فلسفة المشروع

لا نكتب كود سريع.

نكتب مشروع Open Source احترافي.

كل ميزة يجب أن تكون:

* قابلة للاختبار
* موثقة
* لها PR
* لها Issue
* لها Tests
* لا تكسر الإصدارات السابقة

---

# 21. ما تم إنجازه

✅ Build System

✅ Validation

✅ Reports

✅ Search

✅ Stats

✅ CLI Refactor

✅ Add

✅ Remove

✅ Update

✅ GitHub Actions

✅ Database API

✅ CRUD كامل

---

# 22. المرحلة القادمة

الأولوية المقترحة:

### المرحلة 1

```
list
```

```
python fivebr.py list
```

يدعم:

```
--vendor

--category

--filter

--status

--approved
```

---

### المرحلة 2

```
doctor
```

يفحص:

المشروع بالكامل

Missing Files

Database

Filters

Releases

---

### المرحلة 3

```
import

export
```

---

### المرحلة 4

```
Plugin Architecture
```

---

### المرحلة 5

```
Package on PyPI
```

حتى يصبح:

```
pip install fivebr
```

ثم:

```
fivebr build

fivebr validate
```

بدلاً من:

```
python fivebr.py build
```

---

### المرحلة 6

واجهة ويب (Web UI)

---

### المرحلة 7

إصدار

```
v1.0.0
```

---

# 23. قواعد يجب عدم كسرها

أي تعديل مستقبلي يجب أن يحافظ على:

* عدم حذف Metadata من CSV.
* عدم إعادة استخدام `sys.argv`.
* استخدام `main(argv)` في كل أمر جديد.
* إضافة اختبارات لكل ميزة جديدة.
* اختبار يدوي قبل الدمج.
* عدم تعديل `database/domains.csv` في الـ PR إلا إذا كان الهدف هو تحديث البيانات نفسها.

---

# 24. أوامر التحقق القياسية

قبل أي Commit أو Pull Request، شغّل دائمًا:

```powershell
python fivebr.py build
python fivebr.py validate
pytest -q
```

ثم اختبر يدويًا أي ميزة جديدة إذا كانت تفاعلية.

---

## اقتراح إضافي

أنصح أن تحفظ هذا الملخص داخل المشروع باسم:

```text
PROJECT_MASTER_CONTEXT.md
```

وفي كل محادثة جديدة مع ChatGPT أو Codex، ارفع هذا الملف مع المشروع. سيختصر عليك وقتًا كبيرًا ويجعل أي جلسة جديدة تبدأ من نفس المستوى دون الحاجة لإعادة شرح تاريخ المشروع.
