# SP-EYE1 - نظام مراقبة الطلبات المتقدم

## وصف المشروع | Project Description

**العربية:**
SP-EYE1 هو نظام مراقبة طلبات متقدم مصمم لمراقبة وإدارة الطلبات من النظام الخارجي alkarar-exp.com. يوفر النظام مراقبة فورية للطلبات الجديدة والتغييرات في الأسعار، مع واجهة ويب حديثة وقاعدة بيانات متكاملة.

**English:**
SP-EYE1 is an advanced order monitoring system designed to monitor and manage orders from the external system alkarar-exp.com. The system provides real-time monitoring of new orders and price changes, with a modern web interface and integrated database.

## المميزات الرئيسية | Key Features

### 🔍 المراقبة الفورية | Real-time Monitoring
- مراقبة الطلبات الجديدة والتغييرات في الأسعار
- نظام إشعارات فوري للتغييرات
- مراقبة متعددة العملاء بشكل متوازي

### 📊 لوحة التحكم | Dashboard
- إحصائيات شاملة للطلبات والعملاء
- رسوم بيانية تفاعلية باستخدام Chart.js
- تصميم متجاوب مع جميع الأجهزة

### 🎨 واجهة المستخدم | User Interface
- تصميم Glass Morphism حديث
- نظام ألوان مخصص للحالات المختلفة
- دعم كامل للغة العربية
- جداول بيانات تفاعلية مع DataTables

### 🗃️ إدارة قاعدة البيانات | Database Management
- قاعدة بيانات SQLite متكاملة
- أرشيف للطلبات المحذوفة
- نظام استرداد الطلبات
- تتبع تاريخ التغييرات

### 📈 التقارير والإحصائيات | Reports & Statistics
- تقارير عمولات الوكلاء
- إحصائيات العملاء والطلبات
- تتبع الأداء والمراقبة
- تقارير الطلبات المعلقة والمعزولة

## متطلبات النظام | System Requirements

```
Python 3.7+
Flask 2.0+
SQLite3
Requests
BeautifulSoup4
Threading support
```

## التثبيت | Installation

### 1. استنساخ المشروع | Clone the Repository
```bash
git clone https://github.com/mgkw/SP-EYE1.git
cd SP-EYE1
```

### 2. تثبيت المتطلبات | Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. إنشاء قاعدة البيانات | Create Database
```bash
python create_database.py
```

### 4. تشغيل التطبيق | Run the Application
```bash
python app.py
```

أو استخدم الملف التنفيذي:
```bash
# Windows
run.bat

# Linux/Mac
./run.sh
```

## الاستخدام | Usage

### تشغيل الخادم | Starting the Server
1. قم بتشغيل `app.py`
2. افتح المتصفح على `http://127.0.0.1:5000`
3. ستظهر لوحة التحكم الرئيسية

### إضافة عملاء جدد | Adding New Customers
1. انتقل إلى صفحة "العملاء"
2. أدخل اسم العميل الجديد
3. سيتم البحث التلقائي عن طلبات العميل

### بدء المراقبة | Starting Monitoring
1. اضغط على "بدء المراقبة" في الصفحة الرئيسية
2. سيتم مراقبة جميع العملاء تلقائياً
3. ستظهر الإشعارات عند اكتشاف تغييرات

## هيكل المشروع | Project Structure

```
SP-EYE1/
├── app.py                 # التطبيق الرئيسي
├── create_database.py     # إنشاء قاعدة البيانات
├── monitor_orders.py      # نظام المراقبة
├── test.py               # اختبارات النظام
├── requirements.txt      # متطلبات Python
├── templates/           # قوالب HTML
│   ├── base.html
│   ├── index.html
│   ├── customers.html
│   └── ...
├── static/             # الملفات الثابتة
│   └── favicon.png
└── README.md           # هذا الملف
```

## المساهمة | Contributing

نرحب بالمساهمات! يرجى:
1. عمل Fork للمشروع
2. إنشاء فرع جديد للميزة
3. إضافة التغييرات والاختبارات
4. إرسال Pull Request

## الترخيص | License

هذا المشروع مرخص تحت رخصة MIT - راجع ملف LICENSE للتفاصيل.

## الدعم | Support

للحصول على الدعم أو الإبلاغ عن المشاكل:
- افتح Issue على GitHub
- راسل المطور مباشرة

## الإصدارات | Versions

- **v1.0.0** - الإصدار الأولي مع المراقبة الأساسية
- **v1.1.0** - إضافة لوحة التحكم المتقدمة
- **v1.2.0** - نظام الألوان المخصص والتصميم المحسن

---

**تم تطوير هذا المشروع بواسطة:** mgkw
**تاريخ الإنشاء:** 2025
**آخر تحديث:** يوليو 2025 