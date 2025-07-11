# دليل النشر على PythonAnywhere
# PythonAnywhere Deployment Guide

## ⚠️ إصلاحات مهمة للتوافق مع PythonAnywhere

### 🔧 التحديثات الجديدة:
- **إزالة استدعاءات `subprocess.run()`** - معطلة لأسباب أمنية
- **إزالة استدعاءات `webbrowser.open()`** - معطلة لأسباب أمنية  
- **تحديث `app.run()`** - استبدال بـ WSGI application
- **إضافة ملف `pythonanywhere_config.py`** - إعدادات خاصة
- **تحديث ملف `wsgi.py`** - تحسينات للأداء

## متطلبات النشر | Deployment Requirements

### حساب PythonAnywhere
- أنشئ حساب على [PythonAnywhere](https://www.pythonanywhere.com/)
- اختر الخطة المناسبة (يمكن البدء بالخطة المجانية للاختبار)

## خطوات النشر | Deployment Steps

### 1. رفع الكود | Upload Code

#### الطريقة الأولى: استخدام Git (مُوصى بها)
```bash
# في وحدة التحكم (Console) على PythonAnywhere
cd ~
git clone https://github.com/mgkw/SP-EYE1.git
cd SP-EYE1

# التأكد من أحدث إصدار
git pull origin main
```

#### الطريقة الثانية: رفع الملفات يدوياً
- استخدم تبويب "Files" في PythonAnywhere
- ارفع جميع ملفات المشروع

### 2. تثبيت المتطلبات | Install Dependencies

```bash
# في وحدة التحكم
cd ~/SP-EYE1
pip3.10 install --user -r requirements.txt

# التحقق من التثبيت
pip3.10 list --user | grep -E "Flask|requests|beautifulsoup4"
```

### 3. إعداد ملف التكوين | Configuration Setup

```bash
# تحديث ملف التكوين
nano ~/SP-EYE1/pythonanywhere_config.py

# استبدل المسارات التالية:
# DATABASE_PATH = '/home/yourusername/SP-EYE1/customer_orders.db'
# بـ:
# DATABASE_PATH = '/home/اسم_المستخدم_الخاص_بك/SP-EYE1/customer_orders.db'
```

### 4. إنشاء قاعدة البيانات | Create Database

```bash
python3.10 create_database.py

# التحقق من إنشاء قاعدة البيانات
ls -la customer_orders.db
```

### 5. إعداد التطبيق الويب | Web App Setup

#### انتقل إلى تبويب "Web" في PythonAnywhere:

1. **إنشاء تطبيق ويب جديد**:
   - اضغط على "Add a new web app"
   - اختر "Manual configuration"
   - اختر "Python 3.10"

2. **إعداد WSGI**:
   - في قسم "Code", اضغط على "WSGI configuration file"
   - احذف المحتوى الموجود واستبدله بالكود التالي:

```python
#!/usr/bin/env python3
import sys
import os

# استبدل 'yourusername' باسم المستخدم الخاص بك
project_home = '/home/yourusername/SP-EYE1'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# إعداد متغيرات البيئة
os.environ['FLASK_ENV'] = 'production'
os.environ['PYTHONANYWHERE_MODE'] = 'true'

try:
    from pythonanywhere_config import setup_pythonanywhere_environment
    setup_pythonanywhere_environment()
    from app import app as application
    print("✅ تم تحميل التطبيق بنجاح")
except ImportError:
    from app import app as application
except Exception as e:
    print(f"❌ خطأ في تحميل التطبيق: {e}")
    raise
```

3. **إعداد مجلد الملفات الثابتة**:
   - في قسم "Static files"
   - أضف:
     - URL: `/static/`
     - Directory: `/home/yourusername/SP-EYE1/static/`

4. **إعداد Source Code**:
   - في قسم "Code" > "Source code":
   ```
   /home/yourusername/SP-EYE1
   ```

### 6. إعادة تشغيل التطبيق | Restart Application

- اضغط على الزر الأخضر "Reload yourusername.pythonanywhere.com"
- انتظر حتى يكتمل إعادة التشغيل
- تحقق من سجل الأخطاء إذا لم يعمل

## الميزات المعطلة على PythonAnywhere | Disabled Features

### 🚫 الميزات المعطلة لأسباب أمنية:
1. **تشغيل السكريبت الخارجي** (`/run_script`) - معطل
2. **فتح الروابط تلقائياً** في وظيفة الحذف - معطل
3. **استدعاء أوامر النظام** - معطل

### ✅ البدائل المتاحة:
1. **روابط الحذف**: تظهر في السجلات للفتح اليدوي
2. **المراقبة**: تعمل بشكل طبيعي
3. **جميع الصفحات**: تعمل بشكل كامل

## استكشاف الأخطاء | Troubleshooting

### مشاكل شائعة:

#### 1. خطأ "ImportError: No module named 'app'"
```bash
# التحقق من مسار المشروع في WSGI
# تأكد من أن المسار صحيح: /home/yourusername/SP-EYE1
```

#### 2. خطأ "Permission denied"
```bash
# تحديث صلاحيات الملفات
chmod +x ~/SP-EYE1/*.py
chmod 644 ~/SP-EYE1/customer_orders.db
```

#### 3. خطأ "Internal Server Error"
```bash
# فحص سجل الأخطاء في تبويب Web
# تحقق من تثبيت جميع المتطلبات
pip3.10 install --user -r requirements.txt
```

#### 4. خطأ في قاعدة البيانات
```bash
# إعادة إنشاء قاعدة البيانات
rm customer_orders.db
python3.10 create_database.py
```

### فحص السجلات | Log Checking

#### سجل الأخطاء:
- انتقل إلى تبويب "Web"
- اضغط على "Error log" لمشاهدة الأخطاء
- ابحث عن رسائل الخطأ الأخيرة

#### سجل الخادم:
- انتقل إلى تبويب "Web"  
- اضغط على "Server log" لمشاهدة سجل الخادم

### اختبار التطبيق | Testing

#### اختبار سريع:
```bash
# في وحدة التحكم
cd ~/SP-EYE1
python3.10 -c "from app import app; print('✅ التطبيق يعمل بشكل صحيح')"
```

## الصيانة | Maintenance

### تحديث التطبيق | Update Application

```bash
# سحب آخر التحديثات
cd ~/SP-EYE1
git pull origin main

# تثبيت متطلبات جديدة (إن وجدت)
pip3.10 install --user -r requirements.txt

# إعادة تشغيل التطبيق
# اضغط على "Reload" في تبويب Web
```

### النسخ الاحتياطي | Backup

```bash
# نسخ احتياطي لقاعدة البيانات
cp ~/SP-EYE1/customer_orders.db ~/SP-EYE1/backup_$(date +%Y%m%d).db

# نسخ احتياطي للملفات
tar -czf ~/SP-EYE1_backup_$(date +%Y%m%d).tar.gz ~/SP-EYE1/
```

## الأمان | Security

### إعدادات الأمان المحسنة:
1. **تم تعطيل subprocess** لمنع تنفيذ أوامر النظام
2. **تم تعطيل webbrowser** لمنع فتح الروابط التلقائي
3. **استخدام WSGI** بدلاً من Flask development server
4. **إعدادات إنتاج** مع تعطيل وضع التطوير

### متغيرات البيئة الآمنة:
```python
# في pythonanywhere_config.py
SECRET_KEY = 'your-unique-secret-key-here'  # غير هذا!
DEBUG_MODE = False
FLASK_ENV = 'production'
```

## الدعم | Support

### موارد مفيدة:
- [وثائق PythonAnywhere](https://help.pythonanywhere.com/)
- [دليل Flask على PythonAnywhere](https://help.pythonanywhere.com/pages/Flask/)
- [منتدى PythonAnywhere](https://www.pythonanywhere.com/forums/)

### للمساعدة:
- استخدم نظام التذاكر في PythonAnywhere
- راجع سجلات الأخطاء أولاً
- تأكد من اتباع جميع الخطوات بالترتيب

### قائمة التحقق | Checklist

- [ ] استنساخ المشروع من GitHub
- [ ] تثبيت المتطلبات بـ pip3.10
- [ ] تحديث مسارات المستخدم في الملفات
- [ ] إنشاء قاعدة البيانات
- [ ] إعداد WSGI configuration
- [ ] إعداد Static files
- [ ] إعداد Source code path
- [ ] إعادة تشغيل التطبيق
- [ ] فحص سجلات الأخطاء
- [ ] اختبار الصفحات الرئيسية

---

**ملاحظة مهمة:** استبدل `yourusername` باسم المستخدم الفعلي الخاص بك على PythonAnywhere في جميع الأوامر والمسارات.

**التحديث الأخير:** تم إصلاح جميع مشاكل التوافق مع PythonAnywhere وإزالة الاستدعاءات المحظورة. 